from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from config import CLAUDE_MODEL, GPT_MODEL, TOGETHER_MODEL


def get_start_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="💰 Пополнить баланс"),
            KeyboardButton(text="🤖 Выбрать модель"),
        ],
        [KeyboardButton(text="ℹ️ Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_payment_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="100 токенов - 5$"),
            KeyboardButton(text="200 токенов - 10$"),
        ],
        [
            KeyboardButton(text="350 токенов - 15$"),
            KeyboardButton(text="650 токенов - 20$"),
        ],
        [KeyboardButton(text="« Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_models_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="GPT"),
            KeyboardButton(text="Claude"),
            KeyboardButton(text="Together"),
        ],
        [KeyboardButton(text="« Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
