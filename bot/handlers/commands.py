from aiogram import Router, types
from aiogram.filters import Command

from bot.keyboards.main import get_models_keyboard
from database import Database

router = Router()


@router.message(Command("balance"))
async def balance_handler(message: types.Message, db: Database):
    user = await db.users.find_one({"user_id": message.from_user.id})
    if user:
        await message.answer(f"💰 Ваш текущий баланс: {user['balance']} токенов")
    else:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start")


@router.message(Command("models"))
async def models_handler(message: types.Message, db: Database):
    user = await db.users.find_one({"user_id": message.from_user.id})
    if user:
        await message.answer(
            f"🤖 Текущая модель: {user['current_model']}\n\n" "Выберите модель:",
            reply_markup=get_models_keyboard(),
        )
    else:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start")
