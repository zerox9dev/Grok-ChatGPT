from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

from config import TOGETHER_MODEL


class Database:
    def __init__(self, url: str):
        self.client = AsyncIOMotorClient(url)
        self.db = self.client.ai_bot
        self.users = self.db.users

    async def add_user(self, user_id: int, username: Optional[str]) -> None:
        if not await self.users.find_one({"user_id": user_id}):
            await self.users.insert_one(
                {
                    "user_id": user_id,
                    "username": username,
                    "balance": 10,
                    "current_model": TOGETHER_MODEL,
                    "created_at": datetime.utcnow(),
                    "messages_history": [],
                }
            )
