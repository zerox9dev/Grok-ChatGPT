from aiogram import F, Router, types

from bot.keyboards.main import get_models_keyboard, get_payment_keyboard
from database import Database

router = Router()


@router.callback_query(F.data == "add_balance")
async def add_balance_handler(callback: types.CallbackQuery, db: Database):
    await callback.message.answer(
        "💰 Выберите сумму пополнения:", reply_markup=get_payment_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "select_model")
async def select_model_handler(callback: types.CallbackQuery, db: Database):
    await callback.message.answer(
        "🤖 Доступные модели:\n\n" "- GPT-4\n" "- Claude 3",
        reply_markup=get_models_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def help_handler(callback: types.CallbackQuery):
    await callback.message.answer(
        "ℹ️ Справка по использованию бота:\n\n"
        "1. Выберите AI модель\n"
        "2. Пополните баланс\n"
        "3. Отправляйте сообщения для общения с AI"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("model_"))
async def change_model_handler(callback: types.CallbackQuery, db: Database):
    model = callback.data.split("_")[1]  # получаем gpt4 или claude

    await db.users.update_one(
        {"user_id": callback.from_user.id}, {"$set": {"current_model": model}}
    )

    models = {"gpt-4o": "GPT-4o", "claude": "Claude 3"}

    await callback.message.edit_text(
        f"✅ Модель изменена на {models[model]}\n\n" "Можете отправлять сообщения",
        reply_markup=None,
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👋 Главное меню", reply_markup=get_start_keyboard()
    )
    await callback.answer()
