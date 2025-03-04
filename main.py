import asyncio
import logging
import signal
import time
from functools import partial
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import TelegramObject, Update
from aiohttp import ClientSession, web
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.database.database import Database
from bot.handlers.handlers import router  # Основной роутер для команд
from bot.locales.utils import get_text
from bot.utils.daily_tokens import daily_rewards_task
from config import (
    BOT_TOKEN,
    MONGO_URL,
    PORT,
    WEB_SERVER_HOST,
    WEBHOOK_PATH,
    WEBHOOK_URL,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_telegram_webhook(request: web.Request, dp: Dispatcher, bot: Bot):
    start_time = time.time()
    try:
        if not request.can_read_body:
            logger.error("Запрос без тела")
            return web.Response(status=400, text="No body")

        update_data = await request.json()

        if not isinstance(update_data, dict):
            logger.error(f"Некорректный формат данных: {update_data}")
            return web.Response(status=400, text="Invalid JSON")

        update = Update(**update_data)

        await dp.feed_update(bot, update)

        return web.Response(status=200)
    except ValueError as ve:
        logger.error(f"Ошибка создания Update: {ve}")
        return web.Response(status=400, text=f"Invalid update data: {ve}")
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {e}")
        return web.Response(status=500, text=f"Internal error: {e}")
    finally:
        logger.info(f"Обработка запроса заняла {time.time() - start_time:.2f} секунд")


async def on_startup(bot: Bot):
    webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    try:
        await bot.set_webhook(webhook_url)
        logger.info(f"Webhook установлен на {webhook_url}")

        language_code = "uk"  # Это можно взять из конфига или настроек пользователя

        await bot.set_my_commands(
            [
                types.BotCommand(
                    command="/start",
                    description=get_text("start_description", language_code),
                ),
                types.BotCommand(
                    command="/models",
                    description=get_text("models_description", language_code),
                ),
                types.BotCommand(
                    command="/image",
                    description=get_text("image_description", language_code),
                ),
                types.BotCommand(
                    command="/invite",
                    description=get_text("invite_description", language_code),
                ),
                types.BotCommand(
                    command="/profile",
                    description=get_text("profile_description", language_code),
                ),
                types.BotCommand(
                    command="/help",
                    description=get_text("help_description", language_code),
                ),
            ]
        )
        logger.info("Команды бота успешно зарегистрированы")
    except Exception as e:
        logger.error(f"Ошибка при установке вебхука и регистрации команд: {e}")


async def on_shutdown(bot: Bot, db: Database):
    try:
        # Удаляем вебхук
        await bot.delete_webhook()
        logger.info("Вебхук успешно удален")

        # Закрываем сессию бота
        if bot.session is not None and not bot.session.closed:
            await bot.session.close()
            logger.info("Сессия бота закрыта")

        # Закрываем соединение с базой данных
        await db.close()
        logger.info("Соединение с базой данных закрыто")

    except Exception as e:
        logger.error(f"Ошибка в процессе завершения: {e}")
    finally:
        logger.info("Сервисы успешно остановлены")


async def shutdown(loop, runner, app):
    """Gracefully shutdown the application"""
    bot: Bot = app["bot"]
    db: Database = app["db"]

    try:
        # Cancel all running tasks except the current one
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()

        # Close bot session before waiting for tasks
        await on_shutdown(bot, db)

        # Wait for tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Cleanup runner
        await runner.cleanup()

        # Stop the event loop
        loop.stop()
    except Exception as e:
        logger.error(f"Ошибка при завершении работы: {e}")


async def handle_root(request: web.Request):
    return web.Response(text="Сервер работает")


async def handle_ping(request: web.Request):
    return web.Response(text="pong")


async def main():
    # Создаем базу данных
    db = Database(MONGO_URL)

    # Создаем бота и диспетчер
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Инициализируем планировщик
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(daily_rewards_task, "cron", hour=0, minute=0, args=(bot, db))
    scheduler.start()

    # Добавляем базу данных в контекст диспетчера
    dp["db"] = db

    # Регистрируем роутеры
    dp.include_router(router)

    # Настраиваем веб-приложение
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, partial(handle_telegram_webhook, dp=dp, bot=bot))
    app.router.add_get("/", handle_root)  # Роутер для корневого пути
    app.router.add_get("/ping", handle_ping)  # Роутер для пинг-понга

    # Сохраняем бота и базу данных в контексте приложения
    app["bot"] = bot
    app["db"] = db

    # Регистрируем обработчики startup и shutdown
    app.on_startup.append(lambda _: on_startup(bot))
    # Убираем on_shutdown из app, так как мы будем управлять им вручную в shutdown

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_SERVER_HOST, PORT)
    await site.start()
    logger.info(f"Сервер запущен на {WEB_SERVER_HOST}:{PORT}")

    # Обработка сигналов завершения
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig, lambda: asyncio.create_task(shutdown(loop, runner, app))
        )

    # Держим приложение запущенным
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Приложение завершено")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение завершено по запросу пользователя")
    except Exception as e:
        logger.error(f"Ошибка в приложении: {e}")
