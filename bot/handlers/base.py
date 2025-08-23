import re
from functools import wraps
from typing import Optional, Union, Callable, Any

from aiogram import Router, types
from aiogram.enums import ParseMode

from bot.database.database import Database
from bot.database.models import User
from bot.utils.localization import get_text
from bot.utils.logger import setup_logger

# ================================================
# Логгер для обработчиков
# ================================================
logger = setup_logger(__name__)

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
    # Универсальная функция форматирования markdown в HTML
    
    # Экранируем HTML теги, кроме разрешенных Telegram
    import html
    
    # Сначала проверяем есть ли блоки кода (они должны остаться как есть)
    code_blocks = []
    def preserve_code_blocks(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks)-1}__"
    
    # Сохраняем блоки кода (включая SVG, XML, JSON и т.д.)
    text = re.sub(r'```[\s\S]*?```', preserve_code_blocks, text)
    text = re.sub(r'`[^`]+`', preserve_code_blocks, text)
    text = re.sub(r'<svg[\s\S]*?</svg>', preserve_code_blocks, text, flags=re.IGNORECASE)
    
    # Экранируем остальные HTML теги
    text = html.escape(text)
    
    # Применяем форматирование
    patterns = [
        (r"### \*\*(.*?)\*\*", r"<b><u>\1</u></b>"),  # Заголовки
        (r"\*\*(.*?)\*\*", r"<b>\1</b>"),              # Жирный текст  
        (r"\*(.*?)\*", r"<i>\1</i>"),                  # Курсив
        (r"---", "—————————"),                          # Разделители
    ]
    
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    
    # Возвращаем блоки кода
    for i, code_block in enumerate(code_blocks):
        text = text.replace(f"__CODE_BLOCK_{i}__", f"<pre>{html.escape(code_block)}</pre>")
    
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
    # Получаем username бота динамически если нужно для invite_link
    if "invite_link" not in kwargs:
        bot_info = await message.bot.get_me()
        invite_link = f"https://t.me/{bot_info.username}?start={user.user_id}"
    else:
        invite_link = kwargs["invite_link"]
    
    kwargs.update({
        "user_id": user.user_id,
        "username": user.username or "",
        "invite_link": invite_link,
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
    # Безопасная отправка ответа с fallback форматированием
    
    # Проверяем что ответ не пустой
    if not response or not response.strip():
        await message.answer("❌ Получен пустой ответ от нейросети. Попробуйте еще раз.")
        return
    
    try:
        formatted_response = format_to_html(response.strip())
        await message.answer(formatted_response, parse_mode=ParseMode.HTML)
    except Exception as e:
        # Если ошибка форматирования, отправляем как есть
        try:
            await message.answer(response.strip())
        except Exception as e2:
            # Если и это не получается, отправляем базовое сообщение об ошибке
            await message.answer("❌ Ошибка при отправке ответа.")
            logger.error(f"Response sending failed completely: {str(e2)}")
        logger.error(f"HTML format error: {str(e)}")
