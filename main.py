import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import TelegramObject
from aiohttp import web

from bot.handlers.callbacks import router as callback_router
from bot.handlers.messages import router as messages_router
from bot.handlers.payments import router as payments_router
from bot.handlers.start import router as start_router
from config import BOT_TOKEN, MONGO_URL
from database import Database
from webhook import handle_stripe_webhook


# Добавляем класс middleware
class DatabaseMiddleware:
    def __init__(self, db: Database):
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data["db"] = self.db
        return await handler(event, data)


async def main():
    # Инициализация бота
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    db = Database(MONGO_URL)

    # Регистрируем роутеры
    dp.include_router(start_router)
    dp.include_router(callback_router)
    dp.include_router(messages_router)
    dp.include_router(payments_router)

    # Middleware для базы данных
    dp.update.outer_middleware(DatabaseMiddleware(db))

    # Настройка вебхука
    app = web.Application()
    app.router.add_post("/stripe-webhook", handle_stripe_webhook)

    # Запускаем бота и вебхук сервер
    webhook_runner = web.AppRunner(app)
    await webhook_runner.setup()
    site = web.TCPSite(webhook_runner, "localhost", 8000)

    await site.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
