import logging
from datetime import datetime
from typing import Dict, Optional

from motor.motor_asyncio import AsyncIOMotorClient

from bot.database.models import User
from config import GPT_MODEL

# ================================================
# Конфигурация логирования
# ================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ================================================
# Декоратор для обработки ошибок базы данных
# ================================================
def handle_db_errors(operation_name: str):
    """Декоратор для унифицированной обработки ошибок БД"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Ошибка {operation_name}: {str(e)}")
                raise
        return wrapper
    return decorator


class UserManager:
    def __init__(self, db: "Database"):
        self.db = db

    @handle_db_errors("получения пользователя")
    async def get_user(
        self, user_id: int, username: Optional[str], language_code: str = "en"
    ) -> User:
        """Получает пользователя из базы данных или создает нового."""
        user = await self.db.users.find_one({"user_id": user_id})
        if not user:
            await self.db.add_user(user_id, username, language_code)
            user = await self.db.users.find_one({"user_id": user_id})
        return User.from_dict(user)

    @handle_db_errors("обновления баланса и истории")
    async def update_balance_and_history(
        self, user_id: int, tokens_cost: int, model: str,
        message_text: str, response: str
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

    @handle_db_errors("обновления данных пользователя")
    async def update_user(self, user_id: int, update_data: Dict) -> None:
        """Обновляет данные пользователя."""
        await self.db.users.update_one({"user_id": user_id}, {"$set": update_data})

    @handle_db_errors("добавления приглашенного пользователя")
    async def add_invited_user(self, inviter_id: int, invited_id: int) -> None:
        """Добавляет приглашенного пользователя и обновляет статус инвайтера."""
        await self.db.users.update_one(
            {"user_id": inviter_id},
            {
                "$push": {"invited_users": invited_id},
                "$set": {"access_granted": True},
            },
        )


class Database:
    # ================================================
    # Начальные данные для нового пользователя
    # ================================================
    DEFAULT_USER_DATA = {
        "balance": 0,
        "current_model": GPT_MODEL,
        "created_at": None,  # Будет установлено в add_user
        "messages_history": [],
        "invited_users": [],
        "access_granted": False,
        "tariff": "free",
        "last_daily_reward": None,
    }

    def __init__(self, url: str):
        self.client = AsyncIOMotorClient(url)
        self.db = self.client.ai_bot
        self.users = self.db.users
        self.user_manager = UserManager(self)

    @handle_db_errors("добавления пользователя")
    async def add_user(
        self, user_id: int, username: Optional[str], language_code: str
    ) -> None:
        """Добавляет нового пользователя в базу данных."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("Некорректный user_id")
        
        if await self.users.find_one({"user_id": user_id}):
            return  # Пользователь уже существует
        
        user_data = {
            **self.DEFAULT_USER_DATA,
            "user_id": user_id,
            "username": username,
            "language_code": language_code,
            "created_at": datetime.utcnow(),
        }
        await self.users.insert_one(user_data)
        logger.info(f"Добавлен новый пользователь: {user_id}")

    async def get_user_manager(self) -> UserManager:
        """Возвращает экземпляр UserManager."""
        return self.user_manager

    @handle_db_errors("закрытия соединения с БД")
    async def close(self) -> None:
        """Закрывает соединение с базой данных."""
        self.client.close()
        logger.info("Соединение с базой данных закрыто")
