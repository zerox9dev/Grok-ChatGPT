import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Update

from database import Database  # Добавляем импорт


class UserMiddleware(BaseMiddleware):
    def __init__(self, db: Database):
        self.db = db

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        try:
            # Получаем user_id из разных типов апдейтов
            if event.message:
                user_id = event.message.from_user.id
            elif event.callback_query:
                user_id = event.callback_query.from_user.id
            else:
                return await handler(event, data)

            # Получаем пользователя из БД
            user = await self.db.users.find_one({"user_id": user_id})
            data["user"] = user

            return await handler(event, data)

        except Exception as e:
            logging.error(f"Ошибка в UserMiddleware: {e}")
            raise


class CallbackMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        try:
            if event.callback_query:
                try:
                    await event.callback_query.answer()
                except Exception as e:
                    if "query is too old" not in str(e):
                        logging.error(f"Ошибка ответа на callback: {e}")

            return await handler(event, data)

        except Exception as e:
            logging.error(f"Ошибка в middleware: {e}, event_type: {type(event)}")
            if "query is too old" not in str(e):
                raise
            return None
