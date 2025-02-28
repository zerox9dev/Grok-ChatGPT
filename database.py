import logging
from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

from config import GROK_MODEL


class UserManager:
    def __init__(self, db: "Database"):
        self.db = db

    async def get_user(
        self, user_id: int, username: str, language_code: str = "en"
    ) -> dict:
        """Получает пользователя из базы данных."""
        user = await self.db.users.find_one({"user_id": user_id})
        if not user:
            await self.db.add_user(
                user_id=user_id, username=username, language_code=language_code
            )
            user = await self.db.users.find_one({"user_id": user_id})
        return user

    async def update_balance_and_history(
        self,
        user_id: int,
        tokens_cost: int,
        model: str,
        message_text: str,
        response: str,
    ) -> None:
        """Обновляет баланс и историю сообщений пользователя."""
        update_data = {
            "$inc": {"balance": -tokens_cost},
            "$push": {
                "messages_history": {
                    "model": model,
                    "message": message_text,
                    "response": response,
                    "timestamp": datetime.utcnow(),
                }
            },
        }
        await self.db.users.update_one({"user_id": user_id}, update_data)

    def invalidate_cache(self, user_id: int) -> None:
        """Метод больше не нужен, но оставим заглушку для совместимости."""
        pass

    async def update_user(self, user_id: int, update_data: dict) -> None:
        """Обновляет данные пользователя."""
        await self.db.users.update_one({"user_id": user_id}, {"$set": update_data})

    async def add_invited_user(self, inviter_id: int, invited_id: int) -> None:
        """Добавляет приглашенного пользователя и обновляет статус инвайтера."""
        await self.db.users.update_one(
            {"user_id": inviter_id},
            {"$push": {"invited_users": invited_id}, "$set": {"access_granted": True}},
        )


class Database:
    def __init__(self, url: str):
        self.client = AsyncIOMotorClient(url)
        self.db = self.client.ai_bot
        self.users = self.db.users
        self.user_manager = UserManager(self)

    async def add_user(
        self, user_id: int, username: Optional[str], language_code: str
    ) -> None:
        """Добавляет нового пользователя в базу данных."""
        if not await self.users.find_one({"user_id": user_id}):
            await self.users.insert_one(
                {
                    "user_id": user_id,
                    "username": username,
                    "balance": 0,
                    "language_code": language_code,
                    "current_model": GROK_MODEL,
                    "created_at": datetime.utcnow(),
                    "messages_history": [],
                    "invited_users": [],
                    "access_granted": False,
                    "tariff": "free",
                    "last_daily_reward": None,
                }
            )
            logging.info(f"Добавлен новый пользователь: {user_id}")

    async def get_user_manager(self) -> UserManager:
        """Возвращает экземпляр UserManager."""
        return self.user_manager

    async def close(self) -> None:
        """Закрывает соединение с базой данных."""
        self.client.close()
        logging.info("Соединение с базой данных закрыто")
