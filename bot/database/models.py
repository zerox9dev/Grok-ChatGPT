from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class User:
    user_id: int
    username: Optional[str]
    language_code: str
    access_granted: bool
    tariff: str
    balance: int
    current_model: str
    image_model: str
    invited_users: List[int]
    messages_history: List[Dict]
    created_at: datetime
    last_daily_reward: Optional[datetime]

    @classmethod
    def from_dict(cls, data: Dict) -> "User":
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            language_code=data["language_code"],
            access_granted=data["access_granted"],
            tariff=data["tariff"],
            balance=data["balance"],
            current_model=data["current_model"],
            image_model=data.get("image_model", "gpt"),
            invited_users=data["invited_users"],
            messages_history=data["messages_history"],
            created_at=data["created_at"],
            last_daily_reward=data["last_daily_reward"],
        )
