from datetime import datetime

from aiogram import F, Router, types
from aiogram.enums import ChatAction
from aiogram.filters import Command

from bot.keyboards.keyboards import (
    get_models_keyboard,
    get_payment_keyboard,
    get_start_keyboard,
)
from bot.services.claude import ClaudeService
from bot.services.gpt import GPTService
from bot.services.together import TogetherService
from config import CLAUDE_MODEL, GPT_MODEL, TOGETHER_MODEL
from database import Database

gpt_service = GPTService()
claude_service = ClaudeService()
together_service = TogetherService()

router = Router()


@router.message(Command("start"))
async def start_command(message: types.Message, db: Database, user: dict = None):
    if not user:
        await db.add_user(
            user_id=message.from_user.id, username=message.from_user.username
        )
        user = await db.users.find_one({"user_id": message.from_user.id})

    await message.answer(
        f"👋 Привет, {user['username']}!\nЯ бот с доступом к различным AI моделям.\n\n"
        f"💰 Ваш текущий баланс: {user['balance']} токенов\n"
        f"🤖 Текущая модель: {user['current_model']}\n\n"
        "Начните писать сообщение или выберете действие:",
        reply_markup=get_start_keyboard(user.get("image_mode", False)),
    )


@router.callback_query(F.data == "help")
async def help_callback(callback: types.CallbackQuery, user: dict = None):
    await callback.message.edit_text(
        "ℹ️ <b>СПРАВКА ПО ИСПОЛЬЗОВАНИЮ БОТА</b>\n"
        "─────────────────────────\n\n"
        "🤖 <b>Доступные модели:</b>\n"
        "• <b>GPT-4</b> - самая мощная модель, отлично подходит для сложных задач\n"
        "• <b>Claude 3</b> - специализируется на длинных диалогах и анализе\n"
        "• <b>Together</b> - быстрая модель для простых запросов\n\n"
        "💰 <b>Стоимость использования:</b>\n"
        "• Текстовый запрос - <b>1 токен</b>\n"
        "• Генерация изображения - <b>5 токенов</b>\n\n"
        "💳 <b>Пополнение баланса:</b>\n"
        "• <b>100</b> токенов - <b>5$</b>\n"
        "• <b>500</b> токенов - <b>20$</b>\n"
        "• <b>1000</b> токенов - <b>35$</b>\n"
        "• <b>5000</b> токенов - <b>150$</b>\n\n"
        "📝 <b>Как пользоваться:</b>\n"
        "1️⃣ Выберите AI модель\n"
        "2️⃣ Пополните баланс\n"
        "3️⃣ Отправляйте текстовые сообщения или включите режим генерации изображений\n\n"
        "⚠️ <b>ВАЖНО:</b>\n"
        "После генерации изображения не забудьте выключить режим изображений, "
        "чтобы случайно не потратить 5 токенов на следующее сообщение!\n\n"
        "─────────────────────────\n"
        "<i>Выберите действие:</i>",
        reply_markup=get_start_keyboard(user.get("image_mode", False)),
    )


@router.callback_query(F.data == "select_model")
async def select_model_callback(callback: types.CallbackQuery, user: dict = None):
    if not user:
        await callback.message.edit_text(
            "❌ Пользователь не найден. Используйте /start"
        )
        return

    await callback.message.edit_text(
        f"🤖 Текущая модель: {user['current_model']}\n\n" "Выберите модель:",
        reply_markup=get_models_keyboard(),
    )


@router.callback_query(F.data.startswith("model_"))
async def change_model_handler(
    callback: types.CallbackQuery, db: Database, user: dict = None
):
    if not user:
        await callback.message.edit_text(
            "❌ Пользователь не найден. Используйте /start"
        )
        return

    model = callback.data.split("_")[1]
    await db.users.update_one(
        {"user_id": callback.from_user.id}, {"$set": {"current_model": model}}
    )

    models = {GPT_MODEL: "GPT-4", CLAUDE_MODEL: "Claude 3", TOGETHER_MODEL: "Together"}
    await callback.message.edit_text(
        f"✅ Модель изменена на {models[model]}\n\n"
        "Можете отправлять сообщения\n\n"
        "Вернуться в меню:",
        reply_markup=get_start_keyboard(user.get("image_mode", False)),
    )


@router.callback_query(F.data == "add_balance")
async def add_balance_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💰 Выберите сумму пополнения:", reply_markup=get_payment_keyboard()
    )


@router.callback_query(F.data == "toggle_image_mode")
async def toggle_image_mode(
    callback: types.CallbackQuery, db: Database, user: dict = None
):
    if not user:
        await callback.message.edit_text(
            "❌ Пользователь не найден. Используйте /start"
        )
        return

    current_mode = not user.get("image_mode", False)
    await db.users.update_one(
        {"user_id": callback.from_user.id}, {"$set": {"image_mode": current_mode}}
    )

    message = (
        "🎨 Режим генерации изображений включен\nОтправьте описание желаемого изображения"
        if current_mode
        else "📝 Режим генерации изображений выключен\nМожете отправлять текстовые сообщения"
    )

    await callback.message.edit_text(
        message, reply_markup=get_start_keyboard(current_mode)
    )


@router.callback_query(F.data == "back_to_start")
async def back_to_start_callback(callback: types.CallbackQuery, user: dict = None):
    if not user:
        await callback.message.edit_text(
            "❌ Пользователь не найден. Используйте /start"
        )
        return

    await callback.message.edit_text(
        f"👋 Главное меню\n"
        f"💰 Ваш текущий баланс: {user['balance']} токенов\n"
        f"🤖 Текущая модель: {user['current_model']}\n\n"
        f"Выберите действие:",
        reply_markup=get_start_keyboard(user.get("image_mode", False)),
    )


@router.message()
async def handle_message(message: types.Message, db: Database, user: dict = None):
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start")
        return

    if user["balance"] <= 0:
        await message.answer("❌ Недостаточно токенов. Пополните баланс!")
        return

    await message.bot.send_chat_action(
        chat_id=message.chat.id, action=ChatAction.TYPING
    )

    try:
        if user.get("image_mode"):
            if user["balance"] < 5:
                await message.answer(
                    "❌ Для генерации изображения нужно минимум 5 токенов!"
                )
                return

            image_url = await gpt_service.generate_image(message.text)
            await message.answer_photo(image_url)
            tokens_cost = 5
        else:
            if user["current_model"] == GPT_MODEL:
                response = await gpt_service.get_response(message.text)
            elif user["current_model"] == CLAUDE_MODEL:
                response = await claude_service.get_response(message.text)
            elif user["current_model"] == TOGETHER_MODEL:
                response = await together_service.get_response(message.text)
            else:
                await message.answer("❌ Неизвестная модель")
                return
            await message.answer(response)
            tokens_cost = 1

        await db.users.update_one(
            {"user_id": message.from_user.id},
            {
                "$inc": {"balance": -tokens_cost},
                "$push": {
                    "messages_history": {
                        "model": (
                            "dalle-3"
                            if user.get("image_mode")
                            else user["current_model"]
                        ),
                        "message": message.text,
                        "response": image_url if user.get("image_mode") else response,
                        "timestamp": datetime.utcnow(),
                    }
                },
            },
        )

    except Exception as e:
        await message.answer(f"❌ Произошла ошибка: {str(e)}")
        print(f"Error for user {message.from_user.id}: {str(e)}")
