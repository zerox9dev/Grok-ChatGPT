import logging
from datetime import datetime
from typing import Dict, Optional

from motor.motor_asyncio import AsyncIOMotorClient

from bot.database.models import User  # Импорт User из models.py
from config import GROK_MODEL

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserManager:
    def __init__(self, db: "Database"):
        self.db = db

    async def get_user(
        self, user_id: int, username: Optional[str], language_code: str = "en"
    ) -> User:
        """Получает пользователя из базы данных или создает нового."""
        try:
            user = await self.db.users.find_one({"user_id": user_id})
            if not user:
                await self.db.add_user(user_id, username, language_code)
                user = await self.db.users.find_one({"user_id": user_id})
            return User.from_dict(user)
        except Exception as e:
            logger.error(f"Ошибка получения пользователя {user_id}: {str(e)}")
            raise

    async def update_balance_and_history(
        self,
        user_id: int,
        tokens_cost: int,
        model: str,
        message_text: str,
        response: str,
    ) -> None:
        """Обновляет баланс и историю сообщений пользователя."""
        try:
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
        except Exception as e:
            logger.error(f"Ошибка обновления баланса/истории для {user_id}: {str(e)}")
            raise

    async def update_user(self, user_id: int, update_data: Dict) -> None:
        """Обновляет данные пользователя."""
        try:
            await self.db.users.update_one({"user_id": user_id}, {"$set": update_data})
        except Exception as e:
            logger.error(f"Ошибка обновления данных пользователя {user_id}: {str(e)}")
            raise

    async def add_invited_user(self, inviter_id: int, invited_id: int) -> None:
        """Добавляет приглашенного пользователя и обновляет статус инвайтера."""
        try:
            await self.db.users.update_one(
                {"user_id": inviter_id},
                {
                    "$push": {"invited_users": invited_id},
                    "$set": {"access_granted": True},
                },
            )
        except Exception as e:
            logger.error(
                f"Ошибка добавления приглашенного пользователя {invited_id}: {str(e)}"
            )
            raise


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
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("Некорректный user_id")
        try:
            if not await self.users.find_one({"user_id": user_id}):
                user_data = {
                    "user_id": user_id,
                    "username": username,
                    "balance": 0,
                    "language_code": language_code,
                    "current_model": GROK_MODEL,
                    "image_model": "gpt",  # Default image model is GPT (DALL-E)
                    "created_at": datetime.utcnow(),
                    "messages_history": [],
                    "invited_users": [],
                    "access_granted": False,
                    "tariff": "free",
                    "last_daily_reward": None,
                }
                await self.users.insert_one(user_data)
                logger.info(f"Добавлен новый пользователь: {user_id}")
        except Exception as e:
            logger.error(f"Ошибка добавления пользователя {user_id}: {str(e)}")
            raise

    async def get_user_manager(self) -> UserManager:
        """Возвращает экземпляр UserManager."""
        return self.user_manager

    async def close(self) -> None:
        """Закрывает соединение с базой данных."""
        try:
            self.client.close()
            logger.info("Соединение с базой данных закрыто")
        except Exception as e:
            logger.error(f"Ошибка закрытия соединения: {str(e)}")
            raise
