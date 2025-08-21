import logging
import re
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Union, Callable, Any

from aiogram import F, Router, types
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command, CommandObject



from bot.database.database import Database, UserManager
from bot.database.models import User, Agent
from bot.keyboards.keyboards import (
    get_models_keyboard, get_agents_main_keyboard, get_agents_list_keyboard,
    get_agents_manage_keyboard, get_agent_edit_keyboard, get_delete_confirmation_keyboard
)
from bot.locales.utils import get_text
from bot.services.ai_service import AIService
from config import (
    REFERRAL_TOKENS,
    YOUR_ADMIN_ID,
)

# ================================================
# Инициализация и конфигурация
# ================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_SERVICES = {}  # Кэш сервисов моделей
USER_STATES = {}  # Простая система состояний для разговоров
AGENT_CREATION_DATA = {}  # Временные данные создания агента
router = Router()

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


@router.message(Command("send_all"))
async def admin_send_all(message: types.Message, command: CommandObject, db: Database):
    if message.from_user.id != YOUR_ADMIN_ID:
        await message.answer("У вас нет прав для выполнения этой команды")
        return

    if not command.args:
        await message.answer("Использование: /send_all текст сообщения")
        return

    text = command.args
    users = await db.users.find({}).to_list(None)
    success_count = 0
    failed_count = 0

    for user in users:
        try:
            await message.bot.send_message(user["user_id"], text)
            success_count += 1
        except Exception as e:
            print(f"Ошибка отправки сообщения пользователю {user['user_id']}: {str(e)}")
            failed_count += 1

    await message.answer(
        f"Отправлено сообщений: {success_count}, не удалось отправить: {failed_count}"
    )


@router.message(Command("invite"))
@get_user_decorator
async def invite_command(message: types.Message, db: Database, user: User):
    invite_link = f"https://t.me/DockMixAIbot?start={user.user_id}"
    text = "\n\n".join(
        [
            f"🔗 Ваше реферальное посилання: {invite_link}",
            f"👥 Ви запросили: {len(user.invited_users)} користувачів",
        ]
    )
    await message.answer(text)


@router.message(Command("start"))
async def start_command(message: types.Message, db: Database):
    """Команда запуска бота"""
    manager = await db.get_user_manager()
    user = await manager.get_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code,
    )

    # Обрабатываем реферальную ссылку если есть
    if len(message.text.split()) > 1:
        await process_referral(message, user, db)

    await send_localized_message(message, "start", user)





# ================================================
# Обработчики команд (упрощенные с помощью универсальных функций)
# ================================================
@router.message(Command("profile"))
@get_user_decorator
async def profile_command(message: types.Message, db: Database, user: User):
    """Показать профиль пользователя с информацией о текущем режиме"""
    # Get current agent and mode info
    current_agent = user.get_current_agent()
    current_history = user.get_current_history()
    
    if current_agent:
        current_mode = get_text("profile_mode_agent", user.language_code, agent_name=current_agent.name)
    else:
        current_mode = get_text("profile_mode_default", user.language_code)
    
    history_count = len(current_history)
    
    await send_localized_message(
        message, "profile", user,
        current_mode=current_mode,
        history_count=history_count
    )


@router.message(Command("help"))
async def help_command(message: types.Message, db: Database):
    """Показать справку"""
    await create_simple_command_handler("help")(message, db)


@router.message(Command("reset"))
@get_user_decorator
async def reset_command(message: types.Message, db: Database, user: User):
    """Очистить историю сообщений для текущего контекста"""
    manager = await db.get_user_manager()
    
    # Get current agent to determine which history to clear
    current_agent = user.get_current_agent()
    agent_id = current_agent.agent_id if current_agent else None
    
    # Clear history for current context
    await manager.clear_history(user.user_id, agent_id)
    
    # Send localized confirmation message
    if current_agent:
        await send_localized_message(
            message, "history_reset_agent", user, agent_name=current_agent.name
        )
    else:
        await send_localized_message(message, "history_reset_default", user)


@router.message(Command("models"))
@get_user_decorator
async def models_command(message: types.Message, db: Database, user: User):
    """Показать доступные модели"""
    await send_localized_message(
        message, "select_model", user,
        reply_markup=get_models_keyboard(user.language_code)
    )


@router.callback_query(F.data.startswith("model_"))
@get_user_decorator
async def change_model_handler(callback: types.CallbackQuery, db: Database, user: User):
    """Изменить текущую модель"""
    model = callback.data.split("_")[1]
    manager = await db.get_user_manager()
    await manager.update_user(user.user_id, {"current_model": model})
    await send_localized_message(callback.message, "model_changed", user, model=model)


# ================================================
# Agent Management Commands
# ================================================

@router.message(Command("agents"))
@get_user_decorator
async def agents_command(message: types.Message, db: Database, user: User):
    """Показать меню управления агентами"""
    agents = user.get_agents_list()
    agents_count = len(agents)
    
    # Determine current mode
    current_agent = user.get_current_agent()
    if current_agent:
        current_mode = f"🟢 {current_agent.name}"
    else:
        current_mode = "🔵 Стандартный режим"
    
    if agents_count == 0:
        await send_localized_message(
            message, "no_agents", user,
            reply_markup=get_agents_main_keyboard(user.language_code)
        )
    else:
        await send_localized_message(
            message, "agents_menu", user,
            reply_markup=get_agents_main_keyboard(user.language_code),
            agents_count=agents_count,
            current_mode=current_mode
        )


# ================================================
# Agent Callback Handlers  
# ================================================

@router.callback_query(F.data == "agents_menu")
@get_user_decorator
async def agents_menu_callback(callback: types.CallbackQuery, db: Database, user: User):
    """Показать главное меню агентов"""
    agents = user.get_agents_list()
    agents_count = len(agents)
    
    # Determine current mode
    current_agent = user.get_current_agent()
    if current_agent:
        current_mode = f"🟢 {current_agent.name}"
    else:
        current_mode = "🔵 Стандартный режим"
    
    if agents_count == 0:
        text = get_text("no_agents", user.language_code)
    else:
        text = get_text(
            "agents_menu", user.language_code,
            agents_count=agents_count, current_mode=current_mode
        )
    
    try:
        await callback.message.edit_text(
            text, reply_markup=get_agents_main_keyboard(user.language_code)
        )
    except Exception as e:
        # If edit fails (e.g., content unchanged), just answer the callback
        logger.warning(f"Failed to edit message: {e}")
    
    await callback.answer()


@router.callback_query(F.data == "agents_list")
@get_user_decorator
async def agents_list_callback(callback: types.CallbackQuery, db: Database, user: User):
    """Показать список агентов"""
    agents = user.get_agents_list()
    
    if not agents:
        text = get_text("no_agents", user.language_code)
        keyboard = get_agents_main_keyboard(user.language_code)
    else:
        # Build agents list text
        agents_text = "\n".join([
            get_text("current_agent" if agent.agent_id == user.current_agent_id else "inactive_agent",
                   user.language_code, name=agent.name)
            for agent in agents
        ])
        
        # Add default mode
        default_text = get_text(
            "default_mode" if user.current_agent_id is None else "inactive_agent",
            user.language_code, name="Стандартный режим"
        )
        agents_text = default_text + "\n" + agents_text
        
        text = get_text("agents_list", user.language_code, agents_list=agents_text)
        keyboard = get_agents_list_keyboard(agents, user.current_agent_id, user.language_code)
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        # If edit fails (e.g., content unchanged), just answer the callback
        logger.warning(f"Failed to edit message: {e}")
    
    await callback.answer()


@router.callback_query(F.data == "agents_manage")
@get_user_decorator  
async def agents_manage_callback(callback: types.CallbackQuery, db: Database, user: User):
    """Показать меню управления агентами"""
    agents = user.get_agents_list()
    
    if not agents:
        await callback.answer("У вас нет агентов для управления", show_alert=True)
        return
    
    text = "🛠 Управление агентами\n\nВыберите агента для редактирования или удаления:"
    keyboard = get_agents_manage_keyboard(agents, user.language_code)
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        logger.warning(f"Failed to edit message: {e}")
    
    await callback.answer()


@router.callback_query(F.data.startswith("agent_switch_"))
@get_user_decorator
async def agent_switch_callback(callback: types.CallbackQuery, db: Database, user: User):
    """Переключиться на агента или стандартный режим"""
    action = callback.data.replace("agent_switch_", "")
    manager = await db.get_user_manager()
    
    if action == "default":
        # Switch to default mode
        await manager.set_current_agent(user.user_id, None)
        text = get_text("switched_to_default", user.language_code)
    else:
        # Switch to specific agent
        agent_id = action
        agents = user.get_agents_list()
        agent = next((a for a in agents if a.agent_id == agent_id), None)
        
        if not agent:
            await callback.answer("Агент не найден", show_alert=True)
            return
        
        await manager.set_current_agent(user.user_id, agent_id)
        text = get_text("agent_switched", user.language_code, name=agent.name)
    
    try:
        await callback.message.edit_text(text)
    except Exception as e:
        logger.warning(f"Failed to edit message: {e}")
        # Send as new message if edit fails
        await callback.message.answer(text)
    
    await callback.answer()


@router.callback_query(F.data.startswith("agent_edit_"))
@get_user_decorator
async def agent_edit_callback(callback: types.CallbackQuery, db: Database, user: User):
    """Показать меню редактирования агента"""
    agent_id = callback.data.replace("agent_edit_", "")
    agents = user.get_agents_list()
    agent = next((a for a in agents if a.agent_id == agent_id), None)
    
    if not agent:
        await callback.answer("Агент не найден", show_alert=True)
        return
    
    text = get_text("edit_agent_menu", user.language_code, name=agent.name)
    keyboard = get_agent_edit_keyboard(agent_id, user.language_code)
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        logger.warning(f"Failed to edit message: {e}")
    
    await callback.answer()


@router.callback_query(F.data.startswith("agent_delete_"))
@get_user_decorator
async def agent_delete_callback(callback: types.CallbackQuery, db: Database, user: User):
    """Подтверждение удаления агента"""
    if callback.data.startswith("agent_delete_confirm_"):
        # Confirm deletion
        agent_id = callback.data.replace("agent_delete_confirm_", "")
        agents = user.get_agents_list()
        agent = next((a for a in agents if a.agent_id == agent_id), None)
        
        if not agent:
            await callback.answer("Агент не найден", show_alert=True)
            return
        
        manager = await db.get_user_manager()
        await manager.delete_agent(user.user_id, agent_id)
        
        text = get_text("agent_deleted", user.language_code, name=agent.name)
        try:
            await callback.message.edit_text(text)
        except Exception as e:
            logger.warning(f"Failed to edit message: {e}")
            await callback.message.answer(text)
        
        await callback.answer()
    else:
        # Show confirmation
        agent_id = callback.data.replace("agent_delete_", "")
        agents = user.get_agents_list()
        agent = next((a for a in agents if a.agent_id == agent_id), None)
        
        if not agent:
            await callback.answer("Агент не найден", show_alert=True)
            return
        
        text = get_text("delete_agent_confirm", user.language_code, name=agent.name)
        keyboard = get_delete_confirmation_keyboard(agent_id, user.language_code)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logger.warning(f"Failed to edit message: {e}")
        
        await callback.answer()


@router.callback_query(F.data == "agent_create")
@get_user_decorator
async def agent_create_callback(callback: types.CallbackQuery, db: Database, user: User):
    """Начать создание нового агента"""
    agents = user.get_agents_list()
    
    if len(agents) >= MAX_AGENTS_PER_USER:
        await callback.answer(
            get_text("max_agents_reached", user.language_code, max_agents=MAX_AGENTS_PER_USER),
            show_alert=True
        )
        return
    
    # Set state for creating agent name
    USER_STATES[user.user_id] = STATE_CREATING_AGENT_NAME
    AGENT_CREATION_DATA[user.user_id] = {}
    
    text = get_text("create_agent_start", user.language_code)
    try:
        await callback.message.edit_text(text)
    except Exception as e:
        logger.warning(f"Failed to edit message: {e}")
        await callback.message.answer(text)
    
    await callback.answer()


@router.callback_query(F.data.startswith("agent_edit_name_"))
@get_user_decorator
async def agent_edit_name_callback(callback: types.CallbackQuery, db: Database, user: User):
    """Начать редактирование имени агента"""
    agent_id = callback.data.replace("agent_edit_name_", "")
    agents = user.get_agents_list()
    agent = next((a for a in agents if a.agent_id == agent_id), None)
    
    if not agent:
        await callback.answer("Агент не найден", show_alert=True)
        return
    
    # Set state for editing agent name
    USER_STATES[user.user_id] = STATE_EDITING_AGENT_NAME
    AGENT_CREATION_DATA[user.user_id] = {"agent_id": agent_id}
    
    text = get_text("edit_name_prompt", user.language_code, current_name=agent.name)
    try:
        await callback.message.edit_text(text)
    except Exception as e:
        logger.warning(f"Failed to edit message: {e}")
        await callback.message.answer(text)
    
    await callback.answer()


@router.callback_query(F.data.startswith("agent_edit_prompt_"))
@get_user_decorator
async def agent_edit_prompt_callback(callback: types.CallbackQuery, db: Database, user: User):
    """Начать редактирование промпта агента"""
    agent_id = callback.data.replace("agent_edit_prompt_", "")
    agents = user.get_agents_list()
    agent = next((a for a in agents if a.agent_id == agent_id), None)
    
    if not agent:
        await callback.answer("Агент не найден", show_alert=True)
        return
    
    # Set state for editing agent prompt
    USER_STATES[user.user_id] = STATE_EDITING_AGENT_PROMPT
    AGENT_CREATION_DATA[user.user_id] = {"agent_id": agent_id}
    
    text = get_text("edit_prompt_prompt", user.language_code, current_prompt=agent.system_prompt[:200] + "..." if len(agent.system_prompt) > 200 else agent.system_prompt)
    try:
        await callback.message.edit_text(text)
    except Exception as e:
        logger.warning(f"Failed to edit message: {e}")
        await callback.message.answer(text)
    
    await callback.answer()











async def process_referral(message: types.Message, user: User, db: Database) -> None:
    if len(message.text.split()) <= 1:
        return
    try:
        inviter_id = int(message.text.split()[1])
        if inviter_id == user.user_id:
            await message.answer("❌ Ви не можете запросити самого себе!")
            return

        inviter = await db.users.find_one({"user_id": inviter_id})
        if not inviter or message.from_user.id in inviter.get("invited_users", []):
            return

        manager = await db.get_user_manager()
        await manager.add_invited_user(inviter_id, message.from_user.id)
        await send_inviter_notification(
            inviter_id, len(inviter.get("invited_users", []) + 1), db, message.bot
        )
    except (ValueError, TypeError) as e:
        logger.error(f"Помилка обробки реферала: {str(e)}")


async def send_inviter_notification(
    inviter_id: int, invited_count: int, db: Database, bot
) -> None:
    manager = await db.get_user_manager()
    user = await manager.get_user(
        inviter_id, None, "en"
    )  # Username не нужен для уведомления
    text = await send_localized_message(
        None,
        "new_invited_user_tokens",
        user,
        invited_count=invited_count,
        referral_tokens=REFERRAL_TOKENS,
        return_text=True,
    )
    await bot.send_message(inviter_id, text)


# ================================================
# Вспомогательные функции для обработки сообщений
# ================================================
def get_ai_service(model_name: str) -> AIService:
    """Получить или создать AI сервис для модели"""
    if model_name not in MODEL_SERVICES:
        MODEL_SERVICES[model_name] = AIService(model_name=model_name)
    return MODEL_SERVICES[model_name]


async def process_image_message(message: types.Message, service: AIService) -> str:
    """Обработка сообщения с изображением"""
    import os
    
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_path = f"temp_{message.from_user.id}_{photo.file_id}.jpg"
    
    try:
        await message.bot.download_file(file.file_path, file_path)
        response = await service.read_image(file_path)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
    
    return response


def prepare_context_from_history(history: list) -> list:
    """Подготовка контекста из истории сообщений"""
    return [
        {
            "role": "user" if i % 2 == 0 else "assistant",
            "content": entry.get("message" if i % 2 == 0 else "response", ""),
        }
        for i, entry in enumerate(history[-5:])
    ]


async def send_response_safely(message: types.Message, response: str) -> None:
    """Безопасная отправка ответа с fallback форматированием"""
    try:
        formatted_response = format_to_html(response)
        await message.answer(formatted_response, parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(response)
        logger.error(f"HTML format error: {str(e)}")


# ================================================
# Conversation Handlers for Agent Creation/Editing
# ================================================

@router.message(Command("cancel"))
@get_user_decorator
async def cancel_conversation(message: types.Message, db: Database, user: User):
    """Отменить текущую операцию"""
    if user.user_id in USER_STATES:
        del USER_STATES[user.user_id]
    if user.user_id in AGENT_CREATION_DATA:
        del AGENT_CREATION_DATA[user.user_id]
    
    await send_localized_message(message, "agent_creation_cancelled", user)


async def handle_agent_creation_conversation(message: types.Message, db: Database, user: User) -> bool:
    """Обработать сообщение в контексте создания/редактирования агента"""
    user_state = USER_STATES.get(user.user_id)
    
    if not user_state:
        return False
    
    manager = await db.get_user_manager()
    
    # Handle agent name input (creation)
    if user_state == STATE_CREATING_AGENT_NAME:
        agent_name = message.text.strip()
        
        if len(agent_name) > MAX_AGENT_NAME_LENGTH:
            await send_localized_message(message, "agent_name_too_long", user)
            return True
        
        # Save name and ask for prompt
        AGENT_CREATION_DATA[user.user_id]["name"] = agent_name
        USER_STATES[user.user_id] = STATE_CREATING_AGENT_PROMPT
        
        await send_localized_message(message, "agent_name_received", user, name=agent_name)
        return True
    
    # Handle agent prompt input (creation)
    elif user_state == STATE_CREATING_AGENT_PROMPT:
        system_prompt = message.text.strip()
        
        if len(system_prompt) > MAX_AGENT_PROMPT_LENGTH:
            await send_localized_message(message, "agent_prompt_too_long", user)
            return True
        
        # Create agent
        agent_data = AGENT_CREATION_DATA[user.user_id]
        new_agent = Agent(
            agent_id=Agent.generate_id(),
            name=agent_data["name"],
            system_prompt=system_prompt,
            created_at=datetime.now(),
            is_active=True
        )
        
        await manager.create_agent(user.user_id, new_agent)
        await manager.set_current_agent(user.user_id, new_agent.agent_id)
        
        # Clear state
        del USER_STATES[user.user_id]
        del AGENT_CREATION_DATA[user.user_id]
        
        prompt_preview = system_prompt[:100] if len(system_prompt) > 100 else system_prompt
        await send_localized_message(
            message, "agent_created", user,
            name=new_agent.name, prompt_preview=prompt_preview
        )
        return True
    
    # Handle agent name editing
    elif user_state == STATE_EDITING_AGENT_NAME:
        new_name = message.text.strip()
        
        if len(new_name) > MAX_AGENT_NAME_LENGTH:
            await send_localized_message(message, "agent_name_too_long", user)
            return True
        
        agent_id = AGENT_CREATION_DATA[user.user_id]["agent_id"]
        
        # Update agent name
        agents = user.get_agents_list()
        agent = next((a for a in agents if a.agent_id == agent_id), None)
        
        if agent:
            update_data = agent.to_dict()
            update_data["name"] = new_name
            await manager.update_agent(user.user_id, agent_id, update_data)
            
            # Clear state
            del USER_STATES[user.user_id]
            del AGENT_CREATION_DATA[user.user_id]
            
            await send_localized_message(message, "agent_renamed", user, new_name=new_name)
        return True
    
    # Handle agent prompt editing
    elif user_state == STATE_EDITING_AGENT_PROMPT:
        new_prompt = message.text.strip()
        
        if len(new_prompt) > MAX_AGENT_PROMPT_LENGTH:
            await send_localized_message(message, "agent_prompt_too_long", user)
            return True
        
        agent_id = AGENT_CREATION_DATA[user.user_id]["agent_id"]
        
        # Update agent prompt
        agents = user.get_agents_list()
        agent = next((a for a in agents if a.agent_id == agent_id), None)
        
        if agent:
            update_data = agent.to_dict()
            update_data["system_prompt"] = new_prompt
            await manager.update_agent(user.user_id, agent_id, update_data)
            
            # Clear state
            del USER_STATES[user.user_id]
            del AGENT_CREATION_DATA[user.user_id]
            
            await send_localized_message(message, "agent_prompt_updated", user)
        return True
    
    return False


@router.message()
@get_user_decorator
async def handle_message(message: types.Message, db: Database, user: User):
    """Главный обработчик всех сообщений пользователей"""
    
    # Check if user is in conversation state (agent creation/editing)
    if await handle_agent_creation_conversation(message, db, user):
        return
    
    tokens_cost = 1
    
    # Проверка баланса
    if user.balance < tokens_cost:
        next_day = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        await send_localized_message(message, "no_tokens", user, next_day=next_day)
        return

    wait_message = await message.answer("⏳")

    try:
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        service = get_ai_service(user.current_model)
        
        # Get system prompt from current agent if available
        current_agent = user.get_current_agent()
        system_prompt = current_agent.system_prompt if current_agent else None

        # Обработка сообщения в зависимости от типа
        if message.photo:
            response = await process_image_message(message, service)
            content = ""
        else:
            # Get history for current context (agent or default)
            current_history = user.get_current_history()
            context = prepare_context_from_history(current_history)
            response = await service.get_response(
                message.text, context=context, system_prompt=system_prompt
            )
            content = message.text

        # Обновление баланса и истории (включаем информацию об агенте)
        manager = await db.get_user_manager()
        model_info = user.current_model
        if current_agent:
            model_info += f" (Agent: {current_agent.name})"
        
        await manager.update_balance_and_history(
            user.user_id, tokens_cost, model_info, content, response, 
            agent_id=current_agent.agent_id if current_agent else None
        )

        # Удаляем сообщение ожидания и отправляем ответ
        await message.bot.delete_message(message.chat.id, wait_message.message_id)
        await send_response_safely(message, response)

    except Exception as e:
        await message.bot.delete_message(message.chat.id, wait_message.message_id)
        logger.error(f"Message handling failed: {str(e)}")
        await message.answer(f"Помилка обробки повідомлення: {str(e)}")
