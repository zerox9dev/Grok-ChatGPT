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
from bot.handlers.handlers import router  # Main router for commands
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
            logger.error("Request without body")
            return web.Response(status=400, text="No body")

        update_data = await request.json()

        if not isinstance(update_data, dict):
            logger.error(f"Incorrect data format: {update_data}")
            return web.Response(status=400, text="Invalid JSON")

        update = Update(**update_data)

        await dp.feed_update(bot, update)

        return web.Response(status=200)
    except ValueError as ve:
        logger.error(f"Error creating Update: {ve}")
        return web.Response(status=400, text=f"Invalid update data: {ve}")
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return web.Response(status=500, text=f"Internal error: {e}")
    finally:
        logger.info(f"Request processing took {time.time() - start_time:.2f} seconds")


async def on_startup(bot: Bot):
    webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    try:
        await bot.set_webhook(webhook_url)
        logger.info(f"Webhook set to {webhook_url}")

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
        logger.error(f"Error setting webhook and registering commands: {e}")


async def on_shutdown(bot: Bot, db: Database):
    try:
        # Remove webhook
        await bot.delete_webhook()
        logger.info("Webhook successfully removed")

        # Close bot session
        if bot.session is not None and not bot.session.closed:
            await bot.session.close()
            logger.info("Bot session closed")

        # Close database connection
        await db.close()
        logger.info("Database connection closed")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    finally:
        logger.info("Services successfully stopped")


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
        logger.error(f"Error during shutdown: {e}")


async def handle_root(request: web.Request):
    return web.Response(text="Server is running")


async def handle_ping(request: web.Request):
    return web.Response(text="pong - Your free instance will spin down with inactivity, which can delay requests by 50 seconds or more.")


async def keep_alive(app):
    """Periodic request to prevent free instance from spinning down"""
    session: ClientSession = ClientSession()
    try:
        # Extract hostname without http:// prefix and port
        host_parts = WEBHOOK_URL.replace("http://", "").replace("https://", "").split(":")
        base_hostname = host_parts[0]
        ping_url = f"https://{base_hostname}/ping"
        
        while True:
            try:
                await asyncio.sleep(540)  # Ping every 9 minutes
                async with session.get(ping_url) as response:
                    if response.status == 200:
                        logger.info("Self-ping successful - instance is active")
                    else:
                        logger.warning(f"Self-ping returned code {response.status}")
            except Exception as e:
                logger.error(f"Error performing self-ping: {e}")
    except asyncio.CancelledError:
        logger.info("Self-ping task stopped")
    finally:
        await session.close()


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

    # Configure web application
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, partial(handle_telegram_webhook, dp=dp, bot=bot))
    app.router.add_get("/", handle_root)  # Router for root path
    app.router.add_get("/ping", handle_ping)  # Router for ping-pong

    # Save bot and database in application context
    app["bot"] = bot
    app["db"] = db

    # Register startup and shutdown handlers
    app.on_startup.append(lambda _: on_startup(bot))
    # Remove on_shutdown from app as we will handle it manually in shutdown

    runner = web.AppRunner(app)
    await runner.setup()
    
    # Use WEB_SERVER_HOST for binding the local server
    site = web.TCPSite(runner, WEB_SERVER_HOST, PORT)
    
    try:
        await site.start()
        logger.info(f"Server started on {WEB_SERVER_HOST}:{PORT}")
        logger.info(f"Webhook URL: {WEBHOOK_URL}{WEBHOOK_PATH}")
        
        # Start task to keep free instance active
        keep_alive_task = asyncio.create_task(keep_alive(app))
        logger.info("Self-ping task started to prevent free instance from spinning down")

        # Handle termination signals
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig, lambda: asyncio.create_task(shutdown(loop, runner, app))
            )

        # Keep the application running
        await asyncio.Event().wait()
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        # Attempt to clean up resources
        await shutdown(asyncio.get_event_loop(), runner, app)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user request")
    except Exception as e:
        logger.error(f"Error in application: {e}")
