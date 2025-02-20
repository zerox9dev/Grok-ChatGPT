from aiogram import Router, types
from aiogram.filters import Command

from bot.keyboards.main import get_start_keyboard
from database import Database

router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message, db: Database):
    await db.add_user(user_id=message.from_user.id, username=message.from_user.username)

    await message.answer(
        "👋 Привет! Я бот с доступом к различным AI моделям.\n"
        "💰 Ваш текущий баланс: 0 токенов\n"
        "🤖 Текущая модель: GPT",
        reply_markup=get_start_keyboard(),
    )
