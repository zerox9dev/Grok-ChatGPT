import asyncio
import logging
from functools import partial
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import TelegramObject, Update
from aiohttp import web

from bot.handlers.handlers import router  # Основной роутер для команд
from bot.handlers.payments import router as payments_router
from bot.middlewares.middleware import CallbackMiddleware
from config import (
    BOT_TOKEN,
    MONGO_URL,
    WEB_SERVER_HOST,
    WEB_SERVER_PORT,
    WEBHOOK_PATH,
    WEBHOOK_URL,
)
from database import Database
from webhook import handle_stripe_webhook

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseMiddleware:
    def __init__(self, db: Database):
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        logger.info("Middleware вызван")
        data["db"] = self.db
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Ошибка в middleware: {e}")
            raise


async def handle_telegram_webhook(request: web.Request, dp: Dispatcher, bot: Bot):
    try:
        if not request.can_read_body:
            logger.error("Запрос без тела")
            return web.Response(status=400, text="No body")

        update_data = await request.json()
        logger.info(f"Получен запрос от Telegram: {update_data}")

        if not isinstance(update_data, dict):
            logger.error(f"Некорректный формат данных: {update_data}")
            return web.Response(status=400, text="Invalid JSON")

        update = Update(**update_data)
        logger.info(f"Создан объект Update: {update}")

        await dp.feed_update(bot, update)
        logger.info("Обновление передано в Dispatcher")

        return web.Response(status=200)
    except ValueError as ve:
        logger.error(f"Ошибка создания Update: {ve}")
        return web.Response(status=400, text=f"Invalid update data: {ve}")
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {e}")
        return web.Response(status=500, text=f"Internal error: {e}")


async def on_startup(bot: Bot):
    webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    try:
        # Устанавливаем вебхук
        await bot.set_webhook(webhook_url)
        logger.info(f"Webhook установлен на {webhook_url}")

        # Регистрируем команды
        await bot.set_my_commands(
            [
                types.BotCommand(command="/start", description="Начало работы"),
                types.BotCommand(
                    command="/add_balance", description="Пополнить баланс"
                ),
            ]
        )
        logger.info("Команды бота успешно зарегистрированы")
    except Exception as e:
        logger.error(f"Ошибка при установке вебхука и регистрации команд: {e}")


async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.update.middleware.register(CallbackMiddleware())
    db = Database(MONGO_URL)

    # Регистрируем все маршрутизаторы
    dp.include_router(router)  # Основной роутер для команд
    dp.include_router(payments_router)  # Роутер для платежей

    dp.update.outer_middleware(DatabaseMiddleware(db))

    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, partial(handle_telegram_webhook, dp=dp, bot=bot))
    app.router.add_post("/stripe-webhook", handle_stripe_webhook)

    app.on_startup.append(lambda _: on_startup(bot))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_SERVER_HOST, WEB_SERVER_PORT)
    await site.start()

    logger.info(f"Сервер запущен на {WEB_SERVER_HOST}:{WEB_SERVER_PORT}")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
