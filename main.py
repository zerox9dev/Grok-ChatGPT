import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.database.database import Database
from bot.handlers.handlers import router  # Main router for commands
from bot.locales.utils import get_text
from bot.utils.daily_tokens import daily_rewards_task
from config import (
    BOT_TOKEN,
    MONGO_URL,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



async def setup_bot_commands(bot: Bot):
    try:
        language_code = "uk"  # This can be taken from config or user settings

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
                types.BotCommand(
                    command="/reset",
                    description=get_text("reset_description", language_code),
                ),
            ]
        )
        logger.info("Bot commands successfully registered")
    except Exception as e:
        logger.error(f"Error registering commands: {e}")


async def cleanup_resources(bot: Bot, db: Database):
    try:
        # Close bot session
        if bot.session is not None and not bot.session.closed:
            await bot.session.close()
            logger.info("Bot session closed")

        # Close database connection
        await db.close()
        logger.info("Database connection closed")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    finally:
        logger.info("Resources successfully cleaned up")










async def main():
    # Create database
    db = Database(MONGO_URL)

    # Create bot and dispatcher
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Initialize scheduler
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(daily_rewards_task, "cron", hour=0, minute=0, args=(bot, db))
    scheduler.start()

    # Add database to dispatcher context
    dp["db"] = db

    # Register routers
    dp.include_router(router)

    # Setup bot commands
    await setup_bot_commands(bot)
    
    logger.info("Bot started in polling mode")
    
    try:
        # Start polling
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        # Cleanup resources
        await cleanup_resources(bot, db)
        scheduler.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user request")
    except Exception as e:
        logger.error(f"Error in application: {e}")
