from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import CLAUDE_MODEL, GPT_MODEL, TOGETHER_MODEL


def get_start_keyboard(image_mode: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="🤖 Выбрать модель", callback_data="select_model"
            ),
            InlineKeyboardButton(
                text=(
                    "🎨 Выкл. режим изображений"
                    if image_mode
                    else "🎨 Вкл. режим изображений"
                ),
                callback_data="toggle_image_mode",
            ),
        ],
        [
            InlineKeyboardButton(
                text="💰 Пополнить баланс", callback_data="add_balance"
            ),
            InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_payment_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="100 токенов - 5$", callback_data="pay_100"),
            InlineKeyboardButton(text="500 токенов - 20$", callback_data="pay_500"),
        ],
        [
            InlineKeyboardButton(text="1000 токенов - 35$", callback_data="pay_1000"),
            InlineKeyboardButton(text="5000 токенов - 150$", callback_data="pay_5000"),
        ],
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_start")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_models_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="GPT", callback_data=f"model_{GPT_MODEL}"),
            InlineKeyboardButton(text="Claude", callback_data=f"model_{CLAUDE_MODEL}"),
            InlineKeyboardButton(
                text="🎁 FREE LLaMA", callback_data=f"model_{TOGETHER_MODEL}"
            ),
        ],
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_start")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
