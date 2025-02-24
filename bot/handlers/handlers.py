from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Optional, Union

from aiogram import F, Router, types
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import FSInputFile

from bot.keyboards.keyboards import get_models_keyboard
from bot.locales.utils import get_text
from bot.services.claude import ClaudeService
from bot.services.gpt import GPTService
from bot.services.grok import GrokService
from bot.services.together import TogetherService
from config import (
    CLAUDE_MODEL,
    DAILY_TOKENS,
    FREE_TOKENS,
    GPT_MODEL,
    GROK_MODEL,
    TOGETHER_MODEL,
)
from database import Database

MODEL_SERVICES = {
    GPT_MODEL: GPTService(),
    CLAUDE_MODEL: ClaudeService(),
    TOGETHER_MODEL: TogetherService(),
    GROK_MODEL: GrokService(),
}

MODEL_NAMES = {
    GPT_MODEL: "GPT-4o",
    CLAUDE_MODEL: "Claude 3",
    TOGETHER_MODEL: "DeepSeek V3",
    GROK_MODEL: "Grok",
}

REQUIRED_INVITES = 1
router = Router()


def require_access(func):
    @wraps(func)
    async def wrapper(message: types.Message, db: Database, *args, **kwargs):
        user_manager = await db.get_user_manager()
        user = await user_manager.get_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.language_code or "en",
        )
        if not user.get("access_granted"):
            await send_localized_message(message, "access_denied", user)
            return
        return await func(message, db, user=user)

    return wrapper


async def send_localized_message(
    message: types.Message,
    key: str,
    user: dict,
    reply_markup: Optional[types.InlineKeyboardMarkup] = None,
    return_text: bool = False,
    **kwargs,
) -> Union[str, None]:
    language_code = user.get("language_code", "en")
    # Устанавливаем значения по умолчанию для username и invite_link
    kwargs.setdefault("username", user.get("username", ""))
    kwargs.setdefault(
        "invite_link", ""
    )  # Пустая строка, если invite_link не передан или None
    text = get_text(key, language_code, **kwargs)
    if return_text:
        return text
    await message.answer(text, reply_markup=reply_markup)
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

    text = "\n\n".join(
        [
            f"🔗 Ваша реферальная ссылка: {invite_link}",
            f"👥 Вы пригласили: {invited_count}/{REQUIRED_INVITES} пользователей",
            f"ℹ️ {'Пригласите еще ' + str(remaining) + ' пользователя' if remaining else 'Вы уже получили доступ к боту!'}",
        ]
    )
    await message.answer(text)


@router.message(Command("start"))
async def start_command(message: types.Message, db: Database):
    user_manager = await db.get_user_manager()
    user = await user_manager.get_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code or "en",
    )
    photo = FSInputFile("image/welcome.png")
    invite_link = f"https://t.me/DockMixAIbot?start={user['user_id']}"

    if not user.get("access_granted"):
        await process_referral(message, user, db)

    caption_key = "access_denied" if not user.get("access_granted") else "start"
    caption = await send_localized_message(
        message,
        caption_key,
        user,
        invite_link=invite_link if not user.get("access_granted") else None,
        balance=user["balance"] if user.get("access_granted") else None,
        current_model=user.get("current_model", "gpt"),
        return_text=True,
    )
    await message.answer_photo(photo, caption=caption)


@router.message(Command("profile"))
async def profile_command(message: types.Message, db: Database):
    user_manager = await db.get_user_manager()
    user = await user_manager.get_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code or "en",
    )
    await send_localized_message(
        message,
        "profile",
        user,
        user_id=user["user_id"],
        balance=user["balance"],
        current_model=user["current_model"],
    )


@router.message(Command("help"))
async def help_command(message: types.Message, db: Database):
    user_manager = await db.get_user_manager()
    user = await user_manager.get_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code or "en",
    )
    await send_localized_message(
        message,
        "help",
        user,
        balance=user["balance"],
        current_model=user.get("current_model", "gpt"),
    )


@router.message(Command("models"))
@require_access
async def models_command(message: types.Message, db: Database, user: dict):
    await send_localized_message(
        message,
        "select_model",
        user,
        current_model=user["current_model"],
        reply_markup=get_models_keyboard(user.get("language_code", "en")),
    )


@router.callback_query(F.data.startswith("model_"))
@require_access
async def change_model_handler(callback: types.CallbackQuery, db: Database, user: dict):
    model = callback.data.split("_")[1]
    await db.users.update_one(
        {"user_id": callback.from_user.id}, {"$set": {"current_model": model}}
    )
    await send_localized_message(
        callback.message,
        "model_changed",
        user,
        model=MODEL_NAMES[model],
    )


@router.message(Command("image"))
@require_access
async def image_command(message: types.Message, db: Database, user: dict):
    prompt = message.text.split("/image", 1)[1].strip()
    if not prompt:
        await send_localized_message(message, "image_prompt_required", user)
        return

    if user["balance"] < 5:
        await message.answer("У вас недостаточно токенов для генерации изображения.")
        return

    try:
        await message.bot.send_chat_action(
            chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO
        )
        gpt_service = MODEL_SERVICES[GPT_MODEL]
        image_url = await gpt_service.generate_image(prompt)
        await message.answer_photo(image_url)

        tokens_cost = 5
        model = "dalle-3"
        await db.users.update_one(
            {"user_id": message.from_user.id},
            {
                "$inc": {"balance": -tokens_cost},
                "$push": {
                    "history": {
                        "model": model,
                        "prompt": prompt,
                        "response": image_url,
                        "timestamp": datetime.now(),
                    }
                },
            },
        )
    except ValueError as ve:
        await message.answer(f"Ошибка ввода: {str(ve)}")
    except ConnectionError as ce:
        await message.answer(f"Ошибка соединения: {str(ce)}")


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
        if not inviter or message.from_user.id in inviter.get("invited_users", []):
            await message.answer(
                "❌ Вы уже были приглашены этим пользователем!" if inviter else ""
            )
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

    if has_reached_goal and len(inviter.get("invited_users", [])) < REQUIRED_INVITES:
        update_data["balance"] = inviter["balance"] + FREE_TOKENS

    await db.users.update_one({"user_id": inviter_id}, {"$set": update_data})
    await send_inviter_notification(
        bot, inviter_id, len(invited_users), has_reached_goal
    )


async def send_inviter_notification(
    bot, inviter_id: int, invited_count: int, has_reached_goal: bool
) -> None:
    lines = [
        f"🎉 У вас новый приглашенный пользователь! ({invited_count}/{REQUIRED_INVITES})"
    ]
    if has_reached_goal:
        lines.extend(
            [
                f"💰 Вы получили {FREE_TOKENS} токенов за приглашение!",
                "✅ Поздравляем! Вы получили полный доступ к боту!",
            ]
        )
    await bot.send_message(inviter_id, "\n".join(lines))


@router.message()
@require_access
async def handle_message(message: types.Message, db: Database, user: dict):
    await process_daily_rewards(message, user, db)

    try:
        await message.bot.send_chat_action(
            chat_id=message.chat.id, action=ChatAction.TYPING
        )
        service = MODEL_SERVICES.get(user["current_model"])
        if not service:
            await message.answer("❌ Неизвестная модель")
            return

        response = await service.get_response(message.text)
        tokens_cost = 0 if user["current_model"] == TOGETHER_MODEL else 1

        await db.user_manager.update_balance_and_history(
            message.from_user.id,
            tokens_cost,
            user["current_model"],
            message.text,
            response,
        )
        await message.answer(response)
    except ValueError as ve:
        await message.answer(f"Ошибка ввода: {str(ve)}")
    except ConnectionError as ce:
        await message.answer(f"Ошибка соединения: {str(ce)}")


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
