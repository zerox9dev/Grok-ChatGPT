from datetime import datetime

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from bot.database.database import Database
from bot.database.models import User, Agent
from bot.keyboards.keyboards import (
    get_agents_main_keyboard, get_no_agents_keyboard, get_agents_list_keyboard,
    get_agents_manage_keyboard, get_agent_edit_keyboard, get_delete_confirmation_keyboard
)
from bot.locales.utils import get_text

from .base import (
    get_user_decorator, send_localized_message, USER_STATES, AGENT_CREATION_DATA,
    STATE_CREATING_AGENT_NAME, STATE_CREATING_AGENT_PROMPT,
    STATE_EDITING_AGENT_NAME, STATE_EDITING_AGENT_PROMPT,
    MAX_AGENTS_PER_USER, MAX_AGENT_NAME_LENGTH, MAX_AGENT_PROMPT_LENGTH
)

# ================================================
# Роутер для агентов
# ================================================
router = Router()

# ================================================
# Команды управления агентами
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
            reply_markup=get_no_agents_keyboard(user.language_code)
        )
    else:
        await send_localized_message(
            message, "agents_menu", user,
            reply_markup=get_agents_main_keyboard(user.language_code),
            agents_count=agents_count,
            current_mode=current_mode
        )

@router.message(Command("cancel"))
@get_user_decorator
async def cancel_conversation(message: types.Message, db: Database, user: User):
    """Отменить текущую операцию"""
    if user.user_id in USER_STATES:
        del USER_STATES[user.user_id]
    if user.user_id in AGENT_CREATION_DATA:
        del AGENT_CREATION_DATA[user.user_id]
    
    await send_localized_message(message, "agent_creation_cancelled", user)

# ================================================
# Callback обработчики для агентов
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
        keyboard = get_no_agents_keyboard(user.language_code)
    else:
        text = get_text(
            "agents_menu", user.language_code,
            agents_count=agents_count, current_mode=current_mode
        )
        keyboard = get_agents_main_keyboard(user.language_code)
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        # Игнорируем ошибку "message is not modified"
        pass
    await callback.answer()

@router.callback_query(F.data == "agents_list")
@get_user_decorator
async def agents_list_callback(callback: types.CallbackQuery, db: Database, user: User):
    """Показать список агентов"""
    agents = user.get_agents_list()
    
    if not agents:
        text = get_text("no_agents", user.language_code)
        keyboard = get_no_agents_keyboard(user.language_code)
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
    except TelegramBadRequest:
        # Игнорируем ошибку "message is not modified"
        pass
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
    except TelegramBadRequest:
        # Игнорируем ошибку "message is not modified"
        pass
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
    except TelegramBadRequest:
        # Если редактирование невозможно, отправляем новое сообщение
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
    except TelegramBadRequest:
        # Игнорируем ошибку "message is not modified"
        pass
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
        except TelegramBadRequest:
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
        except TelegramBadRequest:
            # Игнорируем ошибку "message is not modified"
            pass
        
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
    except TelegramBadRequest:
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
    except TelegramBadRequest:
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
    except TelegramBadRequest:
        await callback.message.answer(text)
    
    await callback.answer()

# ================================================
# Обработчик разговорного состояния для создания/редактирования агентов
# ================================================
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
