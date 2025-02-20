import logging  # Добавляем импорт logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Update


class CallbackMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        try:
            # Пытаемся ответить на callback если он есть
            if event.callback_query:
                try:
                    await event.callback_query.answer()
                except Exception as e:
                    # Игнорируем ошибку таймаута
                    if "query is too old" not in str(e):
                        logging.error(f"Ошибка ответа на callback: {e}")

            # Продолжаем обработку
            return await handler(event, data)

        except Exception as e:
            logging.error(f"Ошибка в middleware: {e}")
            if "query is too old" not in str(e):
                raise
            return None
