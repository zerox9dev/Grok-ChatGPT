from datetime import datetime, timedelta
from typing import Dict, Optional, Union

from aiogram import F, Router, types
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import FSInputFile

from bot.keyboards.keyboards import get_models_keyboard
from bot.locales.utils import get_text
from bot.services.claude import ClaudeService
from bot.services.gpt import GPTService
from bot.services.together import TogetherService
from config import CLAUDE_MODEL, DAILY_TOKENS, FREE_TOKENS, GPT_MODEL, TOGETHER_MODEL
from database import Database, UserManager

# Создаем словарь для маппинга моделей и сервисов
MODEL_SERVICES = {
    GPT_MODEL: GPTService(),
    CLAUDE_MODEL: ClaudeService(),
    TOGETHER_MODEL: TogetherService(),
}

MODEL_NAMES = {GPT_MODEL: "GPT-4", CLAUDE_MODEL: "Claude 3", TOGETHER_MODEL: "Together"}

# Константа для требуемого количества приглашений
REQUIRED_INVITES = 1

router = Router()


async def send_localized_message(
    message: types.Message,
    key: str,
    user: dict,
    reply_markup: Optional[types.InlineKeyboardMarkup] = None,
    return_text: bool = False,  # Добавляем параметр
    **kwargs,
) -> Union[str, None]:
    language_code = user.get("language_code", "en")
    text = get_text(key, language_code, **kwargs)  # Получаем локализованный текст

    if return_text:
        return text  # Возвращаем текст, если нужно
    else:
        await message.answer(text, reply_markup=reply_markup)  # Отправляем сообщение
        return None


@router.message(Command("invite"))
async def invite_command(message: types.Message, db: Database):
    user_manager = await db.get_user_manager()
    user = await user_manager.get_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code or "en",
    )

    invited_count = len(user.get("invited_users", []))
    invite_link = f"https://t.me/DockMixAIbot?start={user['user_id']}"
    remaining = max(0, REQUIRED_INVITES - invited_count)

    await message.answer(
        f"🔗 Ваша реферальная ссылка: {invite_link}\n\n"
        f"👥 Вы пригласили: {invited_count}/{REQUIRED_INVITES} пользователей\n\n"
        f"ℹ️ {f'Пригласите еще {remaining} пользователя' if remaining else 'Вы уже получили доступ к боту!'}"
    )


@router.message(Command("start"))
async def start_command(message: types.Message, db: Database):
    user_manager = await db.get_user_manager()
    user = await user_manager.get_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code or "en",
    )

    # Путь к изображению
    photo = FSInputFile("image/welcome.png")
    invite_link = f"https://t.me/DockMixAIbot?start={user['user_id']}"

    if not user.get("access_granted"):
        await process_referral(message, user, db)

    # Получаем локализованный текст
    if not user.get("access_granted"):
        caption = await send_localized_message(
            message=message,
            key="access_denied",
            username=user["username"],
            invite_link=invite_link,
            user=user,
            return_text=True,
        )
    else:
        caption = await send_localized_message(
            message=message,
            key="start",
            user=user,
            username=user["username"],
            balance=user["balance"],
            current_model=user.get("current_model", "gpt"),
            return_text=True,
        )

    # Отправляем одно сообщение с фото и текстом
    await message.answer_photo(photo, caption=caption)


@router.message(Command("profile"))
async def profile_command(message: types.Message, db: Database):
    user_manager = await db.get_user_manager()
    user = await user_manager.get_user(
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


@router.message(Command("help"))
async def help_command(message: types.Message, db: Database):

    user_manager = await db.get_user_manager()
    user = await user_manager.get_user(
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
        current_model=user.get("current_model", "gpt"),
    )


@router.message(Command("models"))
async def models_command(message: types.Message, db: Database):
    user_manager = await db.get_user_manager()
    user = await user_manager.get_user(
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
    user_manager = await db.get_user_manager()
    user = await user_manager.get_user(
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
    user_manager = await db.get_user_manager()
    user = await user_manager.get_user(
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


async def process_referral(message: types.Message, user: dict, db: Database) -> None:
    if len(message.text.split()) <= 1:
        return

    try:
        inviter_id = int(message.text.split()[1])
        if inviter_id == user["user_id"]:
            await message.answer(
                "❌ Вы не можете использовать свою собственную реферальную ссылку!"
            )
            return

        inviter = await db.users.find_one({"user_id": inviter_id})
        if not inviter:
            return

        invited_users = inviter.get("invited_users", [])
        if message.from_user.id in invited_users:
            await message.answer("❌ Вы уже были приглашены этим пользователем!")
            return

        await update_inviter_status(
            db, inviter_id, inviter, message.from_user.id, message.bot
        )

    except (ValueError, TypeError) as e:
        print(f"Error processing referral: {str(e)}")


async def update_inviter_status(
    db: Database, inviter_id: int, inviter: dict, new_user_id: int, bot
) -> None:
    invited_users = inviter.get("invited_users", []) + [new_user_id]
    has_reached_goal = len(invited_users) >= REQUIRED_INVITES

    update_data = {"invited_users": invited_users, "access_granted": has_reached_goal}

    # Начисляем бонус только при достижении цели
    if has_reached_goal and len(inviter.get("invited_users", [])) < REQUIRED_INVITES:
        update_data["balance"] = inviter["balance"] + FREE_TOKENS

    await db.users.update_one({"user_id": inviter_id}, {"$set": update_data})

    await send_inviter_notification(
        bot, inviter_id, len(invited_users), has_reached_goal
    )


async def send_inviter_notification(
    bot, inviter_id: int, invited_count: int, has_reached_goal: bool
) -> None:
    notification = f"🎉 У вас новый приглашенный пользователь! ({invited_count}/{REQUIRED_INVITES})"

    if has_reached_goal:
        notification += f"\n💰 Вы получили {FREE_TOKENS} токенов за приглашение!"
        notification += "\n✅ Поздравляем! Вы получили полный доступ к боту!"

    await bot.send_message(inviter_id, notification)


@router.message()
async def handle_message(message: types.Message, db: Database):
    user_manager = await db.get_user_manager()
    user = await user_manager.get_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code or "en",
    )

    if not user.get("access_granted"):
        return await send_localized_message(
            message=message, key="access_denied", user=user
        )

    await process_daily_rewards(message, user, db)

    try:
        await message.bot.send_chat_action(
            chat_id=message.chat.id, action=ChatAction.TYPING
        )

        service = MODEL_SERVICES.get(user["current_model"])
        if not service:
            return await message.answer("❌ Неизвестная модель")

        response = await service.get_response(message.text)
        tokens_cost = 0 if user["current_model"] == TOGETHER_MODEL else 1

        await user_manager.update_balance_and_history(
            message.from_user.id,
            tokens_cost,
            user["current_model"],
            message.text,
            response,
        )

        await message.answer(response)

    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")


async def process_daily_rewards(
    message: types.Message, user: dict, db: Database
) -> None:
    if user.get("tariff") != "paid":
        return

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
