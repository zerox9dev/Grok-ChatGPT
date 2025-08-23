from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Optional

from bot.utils.localization import get_text
from bot.database.models import Agent, User
from config import GPT_MODEL, CLAUDE_MODEL


def get_models_keyboard(language_code: str = "en") -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text=get_text("gpt_button", language_code),
                callback_data=f"model_{GPT_MODEL}",
            ),
            InlineKeyboardButton(
                text=get_text("claude_button", language_code),
                callback_data=f"model_{CLAUDE_MODEL}",
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================================================
# Agent Management Keyboards
# ================================================

def get_agents_main_keyboard(language_code: str = "en") -> InlineKeyboardMarkup:
    """Главное меню управления агентами (когда есть агенты)"""
    keyboard = [
        [
            InlineKeyboardButton(
                text=get_text("agents_list", language_code),
                callback_data="agents_list"
            ),
            InlineKeyboardButton(
                text=get_text("create_agent", language_code),
                callback_data="agent_create"
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_text("default_mode", language_code), 
                callback_data="agent_switch_default"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_no_agents_keyboard(language_code: str = "en") -> InlineKeyboardMarkup:
    """Клавиатура когда у пользователя нет агентов"""
    keyboard = [
        [
            InlineKeyboardButton(
                text=get_text("create_agent", language_code),
                callback_data="agent_create"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_agents_list_keyboard(agents: List[Agent], current_agent_id: Optional[str] = None, language_code: str = "en") -> InlineKeyboardMarkup:
    """Клавиатура со списком агентов пользователя"""
    keyboard = []
    
    # Default mode button
    default_text = get_text("default_mode", language_code) if current_agent_id is None else get_text("default_mode", language_code)
    keyboard.append([
        InlineKeyboardButton(
            text=default_text,
            callback_data="agent_switch_default"
        )
    ])
    
    # Agent buttons (2 per row)
    for i in range(0, len(agents), 2):
        row = []
        for j in range(i, min(i + 2, len(agents))):
            agent = agents[j]
            is_current = agent.agent_id == current_agent_id
            prefix = "🟢" if is_current else "⚪"
            
            row.append(InlineKeyboardButton(
                text=f"{prefix} {get_text('current_agent', language_code) if is_current else get_text('inactive_agent', language_code)} {agent.name}",
                callback_data=f"agent_switch_{agent.agent_id}"
            ))
        keyboard.append(row)
    
    # Management buttons
    if agents:
        keyboard.append([
            InlineKeyboardButton(
                text=get_text("manage_agents", language_code),
                callback_data="agents_manage"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text=get_text("create_agent", language_code),
            callback_data="agent_create"
        ),
        InlineKeyboardButton(
            text=get_text("back", language_code),
            callback_data="agents_menu"
        ),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_agents_manage_keyboard(agents: List[Agent], language_code: str = "en") -> InlineKeyboardMarkup:
    """Клавиатура для управления агентами (редактирование/удаление)"""
    keyboard = []
    
    # Agent management buttons
    for agent in agents:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{get_text('edit_agent', language_code)} {agent.name}",
                callback_data=f"agent_edit_{agent.agent_id}"
            ),
            InlineKeyboardButton(
                text=get_text("delete_agent", language_code),
                callback_data=f"agent_delete_{agent.agent_id}"
            ),
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text=get_text("back", language_code),
            callback_data="agents_list"
        ),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_agent_edit_keyboard(agent_id: str, language_code: str = "en") -> InlineKeyboardMarkup:
    """Клавиатура для редактирования конкретного агента"""
    keyboard = [
        [
            InlineKeyboardButton(
                    text=get_text("edit_name", language_code),
                callback_data=f"agent_edit_name_{agent_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_text("edit_prompt", language_code),
                callback_data=f"agent_edit_prompt_{agent_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_text("delete_agent", language_code),
                callback_data=f"agent_delete_{agent_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_text("back", language_code),
                callback_data="agents_manage"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_delete_confirmation_keyboard(agent_id: str, language_code: str = "en") -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления агента"""
    keyboard = [
        [
            InlineKeyboardButton(
                text=get_text("delete_agent_confirm", language_code),
                callback_data=f"agent_delete_{agent_id}"
            ),
            InlineKeyboardButton(
                text=get_text("cancel", language_code),
                callback_data=f"agent_edit_{agent_id}"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_cancel_keyboard(language_code: str = "en") -> InlineKeyboardMarkup:
    """Простая клавиатура отмены"""
    keyboard = [
        [
            InlineKeyboardButton(
                text=get_text("cancel", language_code),
                callback_data="agents_menu"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)



