from datetime import datetime, timedelta

from aiogram import F, Router, types
from aiogram.enums import ChatAction
from aiogram.filters import Command

from bot.keyboards.keyboards import get_models_keyboard
from bot.locales.utils import get_text
from bot.services.claude import ClaudeService
from bot.services.gpt import GPTService
from bot.services.together import TogetherService
from config import (
    CLAUDE_MODEL,
    DAILY_TOKENS,
    FREE_TOKENS,
    GPT_MODEL,
    PAID_TARIFF_PRICE,
    TOGETHER_MODEL,
)
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

    # Проверяем реферальную ссылку
    if len(message.text.split()) > 1:
        try:
            inviter_id = int(message.text.split()[1])

            # Проверяем, что это не тот же самый пользователь
            if inviter_id == user["user_id"]:
                await message.answer(
                    "❌ Вы не можете использовать свою собственную реферальную ссылку!"
                )
                return

            inviter = await db.users.find_one({"user_id": inviter_id})
            invited_users = inviter.get("invited_users", []) if inviter else []

            # Проверяем, что этот пользователь еще не был приглашен
            if message.from_user.id in invited_users:
                await message.answer("❌ Вы уже были приглашены этим пользователем!")
                return

            if inviter:
                # Добавляем в список приглашенных
                invited_users.append(message.from_user.id)

                # Проверяем, первое ли это приглашение
                is_first_invite = len(invited_users) == 1
                is_third_invite = len(invited_users) >= 3

                update_data = {
                    "invited_users": invited_users,
                }

                # Начисляем токены только за первое приглашение
                if is_first_invite:
                    update_data["balance"] = inviter["balance"] + FREE_TOKENS

                # Даем доступ после третьего приглашения
                if is_third_invite:
                    update_data["access_granted"] = True

                await db.users.update_one(
                    {"user_id": inviter_id}, {"$set": update_data}
                )

                # Отправляем уведомление инвайтеру
                notification = f"🎉 У вас новый приглашенный пользователь! ({len(invited_users)}/3)"
                if is_first_invite:
                    notification += (
                        f"\n💰 Вы получили {FREE_TOKENS} токенов за первое приглашение!"
                    )
                if is_third_invite:
                    notification += (
                        "\n✅ Поздравляем! Вы получили полный доступ к боту!"
                    )

                await message.bot.send_message(inviter_id, notification)

        except (ValueError, TypeError) as e:
            print(f"Error processing referral: {str(e)}")

    # Стандартная инициализация нового пользователя
    if "tariff" not in user:
        await db.users.update_one(
            {"user_id": message.from_user.id},
            {
                "$set": {
                    "tariff": "free",
                    "balance": 0,
                    "last_daily_reward": None,
                    "invited_users": [],
                    "access_granted": False,
                }
            },
        )
        user["balance"] = 0
        user["tariff"] = "free"

    # Проверяем доступ
    if not user.get("access_granted"):
        await send_localized_message(
            message=message,
            key="access_denied",
            user=user,
            reply_markup=None,
        )
        return

    await send_localized_message(
        message=message,
        key="start",
        user=user,
        reply_markup=None,
        username=user["username"],
        balance=user["balance"],
        current_model=user.get("current_model", "gpt"),
    )


@router.message(Command("invite"))
async def invite_command(message: types.Message, db: Database):
    user = await get_user(
        db,
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code or "en",
    )

    # Получаем количество приглашенных пользователей
    invited_count = len(user.get("invited_users", []))

    # Генерируем реферальную ссылку
    invite_link = f"https://t.me/DockMixAIbot?start={user['user_id']}"

    # Отправляем сообщение с информацией о статусе и ссылкой
    await message.answer(
        f"🔗 Ваша реферальная ссылка: {invite_link}\n\n"
        f"👥 Вы пригласили: {invited_count}/3 пользователей\n\n"
        f"ℹ️ Пригласите еще {3 - invited_count} пользователей для получения полного доступа"
    )


@router.message(Command("help"))
async def help_command(message: types.Message, db: Database):
    user = await get_user(
        db,
        message.from_user.id,
        message.from_user.language_code or "en",
    )
    await send_localized_message(
        message=message,
        key="help",
        user=user,
        reply_markup=None,
        username=user["username"],
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

    # Проверяем доступ
    if not user.get("access_granted"):
        await send_localized_message(
            message=message,
            key="access_denied",
            user=user,
            reply_markup=None,
        )
        return

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

    # Проверяем доступ
    if not user.get("access_granted"):
        await send_localized_message(
            callback.message,
            key="access_denied",
            user=user,
            reply_markup=None,
        )
        return

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


@router.message(Command("image"))
async def image_command(message: types.Message, db: Database):
    user = await get_user(
        db,
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code or "en",
    )

    # Проверка доступа
    if not user.get("access_granted"):
        await send_localized_message(
            message=message,
            key="access_denied",
            user=user,
            reply_markup=None,
        )
        return

    # Получаем текст промта из команды
    prompt = message.text.split("/image", 1)[1].strip()

    # Проверяем, есть ли текст промта
    if not prompt:
        await send_localized_message(
            message,
            "image_prompt_required",
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

    # Проверяем, есть ли доступ к боту
    if not user.get("access_granted"):
        await send_localized_message(
            message=message,
            key="access_denied",
            user=user,
            reply_markup=None,
        )
        return

    # Проверяем и начисляем ежедневные токены для платного тарифа
    if user.get("tariff") == "paid":
        last_reward = user.get("last_daily_reward")
        if not last_reward or (datetime.now() - last_reward) > timedelta(days=1):
            await db.users.update_one(
                {"user_id": message.from_user.id},
                {
                    "$inc": {"balance": DAILY_TOKENS},
                    "$set": {"last_daily_reward": datetime.now()},
                },
            )
            await message.answer(f"🎉 Вам начислено {DAILY_TOKENS} токенов за сегодня!")

    await message.bot.send_chat_action(
        chat_id=message.chat.id, action=ChatAction.TYPING
    )

    try:
        if user["current_model"] == GPT_MODEL:
            response = await gpt_service.get_response(message.text)
        elif user["current_model"] == CLAUDE_MODEL:
            response = await claude_service.get_response(message.text)
        elif user["current_model"] == TOGETHER_MODEL:
            response = await together_service.get_response(message.text)
        else:
            await send_message(message, "❌ Неизвестная модель")
            return

        # Списываем 1 токен (кроме модели TOGETHER_MODEL)
        tokens_cost = 0 if user["current_model"] == TOGETHER_MODEL else 1
        model = user["current_model"]

        await update_balance_and_history(
            db, message.from_user.id, tokens_cost, model, message.text, response
        )

        await send_message(message, response)

    except Exception as e:
        await send_message(message, f"Произошла ошибка: {str(e)}")
