import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.database.database import Database
from bot.handlers import router
from bot.locales.utils import get_text
from bot.utils.daily_tokens import daily_rewards_task
from config import BOT_TOKEN, MONGO_URL

# ================================================
# Конфигурация логирования
# ================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================================
# Константы команд бота
# ================================================
BOT_COMMANDS = [
    ("/start", "start_description"),
    ("/models", "models_description"),
    ("/agents", "agents_description"),
    ("/invite", "invite_description"),
    ("/profile", "profile_description"),
    ("/help", "help_description"),
    ("/reset", "reset_description"),
]



# ================================================
# Функции инициализации
# ================================================
async def setup_bot_commands(bot: Bot, language_code: str = "uk"):
    """Универсальная регистрация команд бота"""
    try:
        commands = [
            types.BotCommand(command=cmd, description=get_text(desc_key, language_code))
            for cmd, desc_key in BOT_COMMANDS
        ]
        await bot.set_my_commands(commands)
        logger.info("Bot commands successfully registered")
    except Exception as e:
        logger.error(f"Error registering commands: {e}")


async def initialize_scheduler(bot: Bot, db: Database) -> AsyncIOScheduler:
    """Инициализация планировщика задач"""
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(daily_rewards_task, "cron", hour=0, minute=0, args=(bot, db))
    scheduler.start()
    return scheduler


async def initialize_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    """Инициализация бота и диспетчера"""
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    return bot, dp


async def cleanup_resources(bot: Bot, db: Database):
    """Очистка ресурсов при завершении"""
    resources = [
        ("bot session", lambda: bot.session and bot.session.close()),
        ("database connection", db.close)
    ]
    
    for resource_name, cleanup_func in resources:
        try:
            if callable(cleanup_func):
                if asyncio.iscoroutinefunction(cleanup_func):
                    await cleanup_func()
                else:
                    result = cleanup_func()
                    if result:  # Если это не None, значит нужно выполнить
                        await result
            logger.info(f"{resource_name.title()} closed")
        except Exception as e:
            logger.error(f"Error closing {resource_name}: {e}")
    
    logger.info("Resources successfully cleaned up")


async def main():
    """Главная функция запуска бота"""
    # ================================================
    # Инициализация компонентов
    # ================================================
    db = Database(MONGO_URL)
    bot, dp = await initialize_bot_and_dispatcher()
    scheduler = await initialize_scheduler(bot, db)
    
    # Добавляем базу данных в контекст диспетчера
    dp["db"] = db

    # ================================================
    # Настройка бота
    # ================================================
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook successfully removed")
    except Exception as e:
        logger.warning(f"Error removing webhook: {e}")
    
    await setup_bot_commands(bot)
    logger.info("Bot started in polling mode")
    
    # ================================================
    # Запуск бота
    # ================================================
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        await cleanup_resources(bot, db)
        scheduler.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user request")
    except Exception as e:
        logger.error(f"Error in application: {e}")
