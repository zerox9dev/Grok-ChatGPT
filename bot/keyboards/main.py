from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_start_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text="💰 Пополнить баланс", callback_data="add_balance"
            ),
            InlineKeyboardButton(
                text="🤖 Выбрать модель", callback_data="select_model"
            ),
        ],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_payment_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="100 токенов - 100₽", callback_data="pay_100"),
            InlineKeyboardButton(text="500 токенов - 400₽", callback_data="pay_500"),
        ],
        [
            InlineKeyboardButton(text="1000 токенов - 700₽", callback_data="pay_1000"),
            InlineKeyboardButton(text="5000 токенов - 3000₽", callback_data="pay_5000"),
        ],
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_models_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="GPT-4o", callback_data="model_gpt-4o"),
            InlineKeyboardButton(text="Claude 3", callback_data="model_claude"),
        ],
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
