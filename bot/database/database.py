import logging
from datetime import datetime
from typing import Dict, Optional

from motor.motor_asyncio import AsyncIOMotorClient

from bot.database.models import User, Agent
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
        message_text: str, response: str, agent_id: Optional[str] = None
    ) -> None:
        """Обновляет баланс и историю сообщений пользователя."""
        message_entry = {
            "model": model,
            "message": message_text,
            "response": response,
            "timestamp": datetime.utcnow(),
        }
        
        if agent_id:
            # Update agent-specific history
            update_data = {
                "$inc": {"balance": -tokens_cost},
                "$push": {f"agent_histories.{agent_id}": message_entry}
            }
        else:
            # Update default history
            update_data = {
                "$inc": {"balance": -tokens_cost},
                "$push": {"messages_history": message_entry}
            }
        
        await self.db.users.update_one({"user_id": user_id}, update_data)

    @handle_db_errors("обновления данных пользователя")
    async def update_user(self, user_id: int, update_data: Dict) -> None:
        """Обновляет данные пользователя."""
        await self.db.users.update_one({"user_id": user_id}, {"$set": update_data})

    @handle_db_errors("добавления приглашенного пользователя")
    async def add_invited_user(self, inviter_id: int, invited_id: int) -> None:
        """Добавляет приглашенного пользователя."""
        await self.db.users.update_one(
            {"user_id": inviter_id},
            {"$push": {"invited_users": invited_id}},
        )

    # ================================================
    # Agent Management Methods
    # ================================================
    @handle_db_errors("создания агента")
    async def create_agent(self, user_id: int, agent: Agent) -> None:
        """Создает нового агента для пользователя."""
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$push": {"custom_agents": agent.to_dict()}}
        )

    @handle_db_errors("обновления агента")
    async def update_agent(self, user_id: int, agent_id: str, update_data: Dict) -> None:
        """Обновляет данные агента."""
        await self.db.users.update_one(
            {"user_id": user_id, "custom_agents.agent_id": agent_id},
            {"$set": {f"custom_agents.$.": {**update_data, "agent_id": agent_id}}}
        )

    @handle_db_errors("удаления агента")
    async def delete_agent(self, user_id: int, agent_id: str) -> None:
        """Удаляет агента пользователя и его историю."""
        # Remove agent from custom_agents array
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$pull": {"custom_agents": {"agent_id": agent_id}}}
        )
        
        # Remove agent's message history
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$unset": {f"agent_histories.{agent_id}": ""}}
        )
        
        # If this was the current agent, reset current_agent_id
        user_data = await self.db.users.find_one({"user_id": user_id})
        if user_data and user_data.get("current_agent_id") == agent_id:
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$unset": {"current_agent_id": ""}}
            )

    @handle_db_errors("установки текущего агента")
    async def set_current_agent(self, user_id: int, agent_id: Optional[str]) -> None:
        """Устанавливает текущего агента для пользователя."""
        if agent_id is None:
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$unset": {"current_agent_id": ""}}
            )
        else:
            # Initialize agent history if it doesn't exist
            await self.db.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {"current_agent_id": agent_id},
                    "$setOnInsert": {f"agent_histories.{agent_id}": []}
                },
                upsert=False
            )
            
            # Ensure agent_histories field exists
            await self.db.users.update_one(
                {"user_id": user_id, "agent_histories": {"$exists": False}},
                {"$set": {"agent_histories": {}}}
            )
            
            # Initialize specific agent history if not exists
            user_data = await self.db.users.find_one({"user_id": user_id})
            if user_data and "agent_histories" in user_data:
                if agent_id not in user_data["agent_histories"]:
                    await self.db.users.update_one(
                        {"user_id": user_id},
                        {"$set": {f"agent_histories.{agent_id}": []}}
                    )
    
    @handle_db_errors("очистки истории")
    async def clear_history(self, user_id: int, agent_id: Optional[str] = None) -> None:
        """Очищает историю сообщений для агента или дефолтного режима."""
        if agent_id:
            # Clear specific agent history
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {f"agent_histories.{agent_id}": []}}
            )
        else:
            # Clear default history
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"messages_history": []}}
            )


class Database:
    # ================================================
    # Начальные данные для нового пользователя
    # ================================================
    DEFAULT_USER_DATA = {
        "balance": 0,
        "current_model": GPT_MODEL,
        "created_at": None,  # Будет установлено в add_user
        "messages_history": [],  # Default mode history
        "invited_users": [],
        "last_daily_reward": None,
        "current_agent_id": None,
        "custom_agents": [],
        "agent_histories": {},  # Agent-specific histories
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
