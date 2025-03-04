from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Optional, Union

from aiogram import F, Router, types
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import FSInputFile

from bot.handlers.notifier import send_access_update_notification
from bot.keyboards.keyboards import get_models_keyboard
from bot.locales.utils import get_text
from bot.services.claude import ClaudeService
from bot.services.gpt import GPTService
from bot.services.grok import GrokService
from bot.services.together import TogetherService
from config import (
    CLAUDE_MODEL,
    DAILY_TOKENS,
    DALLE_MODEL,
    GPT_MODEL,
    GROK_MODEL,
    IMAGE_COST,
    MODEL_NAMES,
    REFERRAL_TOKENS,
    REQUIRED_CHANNEL,
    TOGETHER_MODEL,
    YOUR_ADMIN_ID,
)
from database import Database

MODEL_SERVICES = {
    GPT_MODEL: GPTService(),
    CLAUDE_MODEL: ClaudeService(),
    TOGETHER_MODEL: TogetherService(),
    GROK_MODEL: GrokService(),
}


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

        # Если пользователь уже имеет доступ, пропускаем проверку подписки
        if user.get("access_granted") == True:
            return await func(message, db, user=user, *args, **kwargs)

        # Иначе проверяем подписку на канал
        try:
            member = await message.bot.get_chat_member(
                REQUIRED_CHANNEL, message.from_user.id
            )
            access_granted = member.status not in ["left", "kicked", "banned"]
        except Exception as e:
            print(f"Ошибка при проверке подписки на канал: {str(e)}")
            access_granted = False

        if not access_granted:
            await send_localized_message(
                message, "access_denied_subscription", user, channel=REQUIRED_CHANNEL
            )
            # Добавляем инлайн-клавиатуру для присоединения к каналу
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text=get_text(
                                "join_channel_button", user.get("language_code", "en")
                            ),
                            url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}",
                        )
                    ],
                    [
                        types.InlineKeyboardButton(
                            text=get_text(
                                "check_subscription_button",
                                user.get("language_code", "en"),
                            ),
                            callback_data="check_subscription",
                        )
                    ],
                ]
            )
            await message.answer(
                get_text("join_channel_prompt", user.get("language_code", "en")),
                reply_markup=keyboard,
            )
            return

        # Обновляем статус пользователя, если у него есть доступ
        if not user.get("access_granted"):
            await db.users.update_one(
                {"user_id": user["user_id"]},
                {
                    "$set": {
                        "access_granted": True,
                        "tariff": "paid",
                        "last_daily_reward": datetime.now(),
                    }
                },
            )
            user["access_granted"] = True
            user["tariff"] = "paid"

        return await func(message, db, user=user, *args, **kwargs)

    return wrapper


async def check_subscription(message: types.Message, user_id: int) -> bool:
    """Проверяет, подписан ли пользователь на требуемый канал"""
    try:
        member = await message.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status not in ["left", "kicked", "banned"]
    except Exception as e:
        print(f"Ошибка при проверке подписки: {str(e)}")
        return False


@router.message(Command("send_update_notification"))
async def admin_send_notification(message: types.Message, db: Database):
    # Проверка, что это админ (замените на проверку ID вашего админа)
    if message.from_user.id != YOUR_ADMIN_ID:  # Замените YOUR_ADMIN_ID на ID админа
        await message.answer("У вас нет прав для выполнения этой команды")
        return

    # Запускаем рассылку
    success, failed = await send_access_update_notification(db, message.bot)
    await message.answer(
        f"Отправлено уведомлений: {success}, не удалось отправить: {failed}"
    )


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
@require_access  # Добавляем этот декоратор для обеспечения подписки
async def invite_command(message: types.Message, db: Database, user: dict):
    invited_count = len(user.get("invited_users", []))
    invite_link = f"https://t.me/DockMixAIbot?start={user['user_id']}"

    text = "\n\n".join(
        [
            f"🔗 Ваше реферальне посилання: {invite_link}",
            f"👥 Ви запросили: {invited_count} користувачів",
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

    # Если у пользователя уже есть доступ, оставляем его без изменений
    if user.get("access_granted") == True:
        access_granted = True
    else:
        # Иначе проверяем подписку на канал
        access_granted = await check_subscription(message, message.from_user.id)

    # Обрабатываем реферала независимо от статуса подписки
    if len(message.text.split()) > 1:
        await process_referral(message, user, db)

    # Обновляем статус пользователя, если у него есть доступ по подписке
    if access_granted and not user.get("access_granted"):
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {
                "$set": {
                    "access_granted": True,
                    "tariff": "paid",
                    "last_daily_reward": datetime.now(),
                }
            },
        )
        user["access_granted"] = True
        user["tariff"] = "paid"

    # Определяем, какой текст показывать
    caption_key = "access_denied_subscription" if not access_granted else "start"
    caption = await send_localized_message(
        message,
        caption_key,
        user,
        channel=REQUIRED_CHANNEL if not access_granted else None,
        invite_link=invite_link,
        balance=user["balance"] if access_granted else None,
        current_model=user.get("current_model", "gpt"),
        return_text=True,
    )

    # Добавляем кнопку подписки, если не имеет доступа
    if not access_granted:
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=get_text(
                            "join_channel_button", user.get("language_code", "en")
                        ),
                        url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}",
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text=get_text(
                            "check_subscription_button", user.get("language_code", "en")
                        ),
                        callback_data="check_subscription",
                    )
                ],
            ]
        )
        await message.answer_photo(photo, caption=caption, reply_markup=keyboard)
    else:
        await message.answer_photo(photo, caption=caption)


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: types.CallbackQuery, db: Database):
    user_manager = await db.get_user_manager()
    user = await user_manager.get_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.language_code or "en",
    )

    # Проверяем обновленный статус подписки
    access_granted = await check_subscription(callback.message, callback.from_user.id)

    if access_granted:
        # Обновляем статус пользователя
        if not user.get("access_granted"):
            await db.users.update_one(
                {"user_id": user["user_id"]},
                {
                    "$set": {
                        "access_granted": True,
                        "tariff": "paid",
                        "last_daily_reward": datetime.now(),
                    }
                },
            )

        await callback.message.edit_caption(
            caption=await send_localized_message(
                callback.message, "subscription_confirmed", user, return_text=True
            ),
            reply_markup=None,
        )

        # Отправляем приветственное сообщение
        welcome_text = await send_localized_message(
            callback.message,
            "start",
            user,
            balance=user["balance"],
            current_model=user.get("current_model", "gpt"),
            return_text=True,
        )
        await callback.message.answer(welcome_text)
    else:
        # Все еще не подписан
        await callback.answer(
            get_text("still_not_subscribed", user.get("language_code", "en")),
            show_alert=True,
        )


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
        await message.answer("У вас недостатньо токенів для генерації зображення.")
        return

    try:
        await message.bot.send_chat_action(
            chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO
        )
        gpt_service = MODEL_SERVICES[GPT_MODEL]
        image_url = await gpt_service.generate_image(prompt)
        await message.answer_photo(image_url)

        tokens_cost = IMAGE_COST
        model = DALLE_MODEL
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
            await message.answer("❌ Ви не можете запросити самого себе!")
            return

        inviter = await db.users.find_one({"user_id": inviter_id})
        if not inviter or message.from_user.id in inviter.get("invited_users", []):
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
    await db.users.update_one(
        {"user_id": inviter_id},
        {
            "$set": {"invited_users": invited_users},
            "$inc": {"balance": REFERRAL_TOKENS},
        },
    )
    await send_inviter_notification(bot, inviter_id, len(invited_users))


async def send_inviter_notification(
    db: Database, bot, inviter_id: int, invited_count: int
) -> None:
    user_manager = await db.get_user_manager()
    user = await user_manager.get_user(inviter_id)

    text = await send_localized_message(
        None,
        "new_invited_user_tokens",
        user,
        invited_count=invited_count,
        referral_tokens=REFERRAL_TOKENS,
        return_text=True,
    )
    await bot.send_message(inviter_id, text)


@router.message()
@require_access
async def handle_message(message: types.Message, db: Database, user: dict):

    # Проверяем баланс перед обработкой сообщения
    tokens_cost = 0 if user["current_model"] == TOGETHER_MODEL else 1
    if user["balance"] < tokens_cost:
        next_day = datetime.now() + timedelta(days=1)
        await send_localized_message(
            message,
            "no_tokens",
            user,
            next_day=next_day.strftime("%Y-%m-%d"),
        )
        return

    try:
        await message.bot.send_chat_action(
            chat_id=message.chat.id, action=ChatAction.TYPING
        )
        service = MODEL_SERVICES.get(user["current_model"])
        if not service:
            await message.answer("❌ Неизвестная модель")
            return

        # Получаем данные пользователя из базы
        user_data = await db.users.find_one({"user_id": message.from_user.id})
        messages_history = user_data.get("messages_history", [])

        # Формируем контекст из последних 5 сообщений
        context = []
        for entry in messages_history[-5:]:  # Берем последние 5 записей
            context.append({"role": "user", "content": entry["message"]})
            context.append({"role": "assistant", "content": entry["response"]})

        # Вызываем get_response с контекстом
        response = await service.get_response(message.text, context=context)

        # Обновляем баланс и добавляем новую запись в историю
        await db.users.update_one(
            {"user_id": message.from_user.id},
            {
                "$inc": {"balance": -tokens_cost},
                "$push": {
                    "messages_history": {
                        "model": user["current_model"],
                        "message": message.text,
                        "response": response,
                        "timestamp": datetime.now(),
                    }
                },
            },
        )
        await message.answer(response)
    except ValueError as ve:
        await message.answer(f"Ошибка ввода: {str(ve)}")
    except ConnectionError as ce:
        await message.answer(f"Ошибка соединения: {str(ce)}")
