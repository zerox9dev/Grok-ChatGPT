import logging
import re
from functools import wraps
from typing import Optional, Union, Callable, Any

from aiogram import Router, types
from aiogram.enums import ParseMode

from bot.database.database import Database
from bot.database.models import User
from bot.utils.localization import get_text

# ================================================
# Инициализация и конфигурация
# ================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================================
# Константы для состояний
# ================================================
STATE_CREATING_AGENT_NAME = "creating_agent_name"
STATE_CREATING_AGENT_PROMPT = "creating_agent_prompt"
STATE_EDITING_AGENT_NAME = "editing_agent_name"
STATE_EDITING_AGENT_PROMPT = "editing_agent_prompt"

MAX_AGENTS_PER_USER = 10
MAX_AGENT_NAME_LENGTH = 50
MAX_AGENT_PROMPT_LENGTH = 2000

# ================================================
# Глобальные переменные состояния
# ================================================
USER_STATES = {}  # Простая система состояний для разговоров
AGENT_CREATION_DATA = {}  # Временные данные создания агента
MODEL_SERVICES = {}  # Кэш сервисов моделей

# ================================================
# Утилитные функции для форматирования
# ================================================
def format_to_html(text: str) -> str:
    """Универсальная функция форматирования markdown в HTML"""
    patterns = [
        (r"### \*\*(.*?)\*\*", r"<b><u>\1</u></b>"),  # Заголовки
        (r"\*\*(.*?)\*\*", r"<b>\1</b>"),              # Жирный текст
        (r"\*(.*?)\*", r"<i>\1</i>"),                  # Курсив
        (r"---", "—————————"),                          # Разделители
    ]
    
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text

# ================================================
# Универсальные декораторы
# ================================================
def get_user_decorator(func: Callable) -> Callable:
    """Универсальный декоратор для получения пользователя"""
    @wraps(func)
    async def wrapper(message: types.Message, db: Database, *args, **kwargs):
        manager = await db.get_user_manager()
        user = await manager.get_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.language_code,
        )
        return await func(message, db, user=user, *args, **kwargs)
    return wrapper

# ================================================
# Универсальные функции-хелперы
# ================================================
async def send_localized_message(
    message: types.Message, key: str, user: User,
    reply_markup: Optional[types.InlineKeyboardMarkup] = None,
    return_text: bool = False, **kwargs
) -> Optional[str]:
    """Универсальная функция для отправки локализованных сообщений"""
    kwargs.update({
        "user_id": user.user_id,
        "username": user.username or "",
        "invite_link": f"https://t.me/DockMixAIbot?start={user.user_id}",
        "balance": getattr(user, 'balance', 0),
        "current_model": getattr(user, 'current_model', 'GPT')
    })
    
    text = get_text(key, user.language_code, **kwargs)
    if return_text:
        return text
    await message.answer(text, reply_markup=reply_markup)
    return None

def create_simple_command_handler(message_key: str) -> Callable:
    """Фабрика для создания простых обработчиков команд"""
    @get_user_decorator
    async def handler(message: types.Message, db: Database, user: User):
        await send_localized_message(message, message_key, user)
    return handler

async def send_response_safely(message: types.Message, response: str) -> None:
    """Безопасная отправка ответа с fallback форматированием"""
    try:
        formatted_response = format_to_html(response)
        await message.answer(formatted_response, parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(response)
        logger.error(f"HTML format error: {str(e)}")
