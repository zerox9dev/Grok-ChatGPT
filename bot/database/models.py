from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import uuid


@dataclass
class Agent:
    agent_id: str
    name: str
    system_prompt: str
    created_at: datetime
    is_active: bool = True

    @classmethod
    def from_dict(cls, data: Dict) -> "Agent":
        return cls(
            agent_id=data["agent_id"],
            name=data["name"],
            system_prompt=data["system_prompt"],
            created_at=data["created_at"],
            is_active=data.get("is_active", True),
        )

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "system_prompt": self.system_prompt,
            "created_at": self.created_at,
            "is_active": self.is_active,
        }

    @staticmethod
    def generate_id() -> str:
        """Generate unique agent ID"""
        return str(uuid.uuid4())


@dataclass
class User:
    user_id: int
    username: Optional[str]
    language_code: str
    balance: int
    current_model: str
    invited_users: List[int]
    messages_history: List[Dict]  # Default mode history
    created_at: datetime
    last_daily_reward: Optional[datetime]
    # New agent-related fields
    current_agent_id: Optional[str] = None
    custom_agents: List[Dict] = None
    # Agent-specific message histories
    agent_histories: Dict[str, List[Dict]] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "User":
        custom_agents = data.get("custom_agents", [])
        if custom_agents is None:
            custom_agents = []
        
        agent_histories = data.get("agent_histories", {})
        if agent_histories is None:
            agent_histories = {}
        
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            language_code=data["language_code"],
            balance=data["balance"],
            current_model=data["current_model"],
            invited_users=data["invited_users"],
            messages_history=data["messages_history"],
            created_at=data["created_at"],
            last_daily_reward=data["last_daily_reward"],
            current_agent_id=data.get("current_agent_id"),
            custom_agents=custom_agents,
            agent_histories=agent_histories,
        )

    def get_current_agent(self) -> Optional[Agent]:
        """Get currently active agent"""
        if not self.current_agent_id or not self.custom_agents:
            return None
        
        for agent_data in self.custom_agents:
            if agent_data.get("agent_id") == self.current_agent_id:
                return Agent.from_dict(agent_data)
        return None

    def get_agents_list(self) -> List[Agent]:
        """Get all user agents"""
        if not self.custom_agents:
            return []
        return [Agent.from_dict(agent_data) for agent_data in self.custom_agents]
    
    def get_current_history(self) -> List[Dict]:
        """Get message history for current context (agent or default)"""
        if self.current_agent_id and self.agent_histories:
            return self.agent_histories.get(self.current_agent_id, [])
        return self.messages_history
    
    def get_agent_history(self, agent_id: str) -> List[Dict]:
        """Get message history for specific agent"""
        if not self.agent_histories:
            return []
        return self.agent_histories.get(agent_id, [])
