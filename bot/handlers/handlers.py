from datetime import datetime

from aiogram import F, Router, types
from aiogram.enums import ChatAction
from aiogram.filters import Command

from bot.keyboards.keyboards import get_models_keyboard, get_payment_keyboard
from bot.locales.utils import get_text
from bot.services.claude import ClaudeService
from bot.services.gpt import GPTService
from bot.services.together import TogetherService
from config import CLAUDE_MODEL, GPT_MODEL, TOGETHER_MODEL
from database import Database

gpt_service = GPTService()
claude_service = ClaudeService()
together_service = TogetherService()

router = Router()


async def get_user(
    db: Database, user_id: int, username: str, language_code: str = "en"
):
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        await db.add_user(
            user_id=user_id, username=username, language_code=language_code
        )
        user = await db.users.find_one({"user_id": user_id})
    return user


async def send_localized_message(message, key, user, reply_markup=None, **kwargs):
    language_code = user.get("language_code", "en")
    await message.answer(
        get_text(key, language_code, **kwargs), reply_markup=reply_markup
    )


async def send_message(message, text, reply_markup=None):
    await message.answer(text, reply_markup=reply_markup)


async def update_balance_and_history(
    db, user_id, tokens_cost, model, message_text, response
):
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$inc": {"balance": -tokens_cost},
            "$push": {
                "messages_history": {
                    "model": model,
                    "message": message_text,
                    "response": response,
                    "timestamp": datetime.utcnow(),
                }
            },
        },
    )


@router.message(Command("start"))
async def start_command(message: types.Message, db: Database):
    user = await get_user(
        db,
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code or "en",
    )
    await send_localized_message(
        message=message,  # указываем message явно
        key="start",  # ключ сообщения
        user=user,  # передаем пользователя
        reply_markup=None,  # явно указываем reply_markup
        username=user["username"],  # дополнительные данные
        balance=user["balance"],
        current_model=user["current_model"],
    )


@router.message(Command("help"))
async def help_command(message: types.Message, db: Database):
    user = await get_user(
        db,
        message.from_user.id,
        message.from_user.language_code or "en",
    )
    await send_localized_message(
        message=message,  # указываем message явно
        key="help",  # ключ сообщения
        user=user,  # передаем пользователя
        reply_markup=None,  # явно указываем reply_markup
        username=user["username"],  # дополнительные данные
        balance=user["balance"],
        current_model=user["current_model"],
    )


@router.message(Command("profile"))
async def profile_command(message: types.Message, db: Database):
    user = await get_user(
        db,
        message.from_user.id,
        message.from_user.language_code or "en",
    )
    await send_localized_message(
        message,
        "profile",
        user,
        user_id=user["user_id"],
        balance=user["balance"],
        current_model=user["current_model"],
        reply_markup=None,
    )


@router.message(Command("models"))
async def models_command(message: types.Message, db: Database):
    user = await get_user(
        db,
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code or "en",
    )
    await send_localized_message(
        message,
        "select_model",
        user,
        current_model=user["current_model"],
        reply_markup=get_models_keyboard(user.get("language_code", "en")),
    )


@router.callback_query(F.data.startswith("model_"))
async def change_model_handler(callback: types.CallbackQuery, db: Database):
    user = await get_user(
        db,
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.language_code or "en",
    )
    model = callback.data.split("_")[1]
    await db.users.update_one(
        {"user_id": callback.from_user.id}, {"$set": {"current_model": model}}
    )
    models = {GPT_MODEL: "GPT-4", CLAUDE_MODEL: "Claude 3", TOGETHER_MODEL: "Together"}
    await send_localized_message(
        callback.message,
        "model_changed",
        user,
        model=models[model],
    )


@router.message(Command("add_balance"))
async def add_balance_command(message: types.Message, db: Database):
    user = await get_user(
        db,
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code or "en",
    )
    await send_localized_message(
        message,
        "add_balance",
        user,
        reply_markup=get_payment_keyboard(user.get("language_code", "en")),
    )


@router.message(Command("image"))
async def image_command(message: types.Message, db: Database):
    user = await get_user(
        db,
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code or "en",
    )

    # Получаем текст промта из команды
    prompt = message.text.split("/image", 1)[1].strip()

    # Проверяем, есть ли текст промта
    if not prompt:
        await send_localized_message(
            message,
            "image_prompt_required",  # Ключ сообщения
            user,
            reply_markup=None,
        )
        return

    # Проверяем баланс пользователя
    if user["balance"] < 5:
        await send_message(
            message, "У вас недостаточно токенов для генерации изображения."
        )
        return

    # Генерируем изображение
    try:
        await message.bot.send_chat_action(
            chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO
        )
        image_url = await gpt_service.generate_image(prompt)
        await message.answer_photo(image_url)

        # Списываем токены и обновляем историю
        tokens_cost = 5
        model = "dalle-3"
        await update_balance_and_history(
            db, message.from_user.id, tokens_cost, model, prompt, image_url
        )

    except Exception as e:
        print(f"Error for user {message.from_user.id}: {str(e)}")
        await send_message(message, f"Произошла ошибка: {str(e)}")


@router.message()
async def handle_message(message: types.Message, db: Database):
    user = await get_user(
        db,
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code or "en",
    )

    print(f"Handling message from user {message.from_user.id}: {message.text}")
    print(f"User balance: {user['balance']}, current model: {user['current_model']}")

    # Проверяем баланс пользователя
    if user["balance"] <= 0 and user["current_model"] != TOGETHER_MODEL:
        print("User has no tokens.")
        await send_message(message, "У вас недостаточно токенов.")
        return

    # Указываем, что бот печатает (для UX)
    await message.bot.send_chat_action(
        chat_id=message.chat.id, action=ChatAction.TYPING
    )

    try:
        print(f"Generating response using model: {user['current_model']}")

        # Выбираем модель для генерации ответа
        if user["current_model"] == GPT_MODEL:
            response = await gpt_service.get_response(message.text)
        elif user["current_model"] == CLAUDE_MODEL:
            response = await claude_service.get_response(message.text)
        elif user["current_model"] == TOGETHER_MODEL:
            response = await together_service.get_response(message.text)
            print(f"Generated response: {response}")
        else:
            await send_message(message, "❌ Неизвестная модель")
            return

        # Определяем стоимость токенов
        tokens_cost = 0 if user["current_model"] == TOGETHER_MODEL else 1
        model = user["current_model"]

        # Обновляем баланс и историю пользователя
        print(f"Updating balance and history for user {message.from_user.id}")
        await update_balance_and_history(
            db, message.from_user.id, tokens_cost, model, message.text, response
        )

        # Отправляем ответ пользователю
        await send_message(message, response)

    except Exception as e:
        print(f"Error for user {message.from_user.id}: {str(e)}")
        await send_message(message, f"Произошла ошибка: {str(e)}")
