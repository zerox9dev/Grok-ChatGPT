from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.locales.utils import get_text
from config import CLAUDE_MODEL, GPT_MODEL, TOGETHER_MODEL


def get_models_keyboard(language_code: str = "en") -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text=get_text("gpt_button", language_code),
                callback_data=f"model_{GPT_MODEL}",
            ),
            # InlineKeyboardButton(
            #     text=get_text("claude_button", language_code),
            #     callback_data=f"model_{CLAUDE_MODEL}",
            # ),
            InlineKeyboardButton(
                text=get_text("free_llama_button", language_code),
                callback_data=f"model_{TOGETHER_MODEL}",
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
