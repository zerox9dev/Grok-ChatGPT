import asyncio
import logging
import os
import re
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Union

from aiogram import F, Router, types
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile

from bot.database.database import Database, UserManager
from bot.database.models import User
from bot.keyboards.keyboards import get_models_keyboard
from bot.locales.utils import get_text
from bot.services.gpt import GPTService
from bot.services.grok import GrokService
from config import (
    DAILY_TOKENS,
    DALLE_MODEL,
    GPT_MODEL,
    GROK_MODEL,
    IMAGE_COST,
    MODEL_NAMES,
    REFERRAL_TOKENS,
    REQUIRED_CHANNEL,
    YOUR_ADMIN_ID,
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_SERVICES = {
    GPT_MODEL: GPTService(),
    GROK_MODEL: GrokService(),
}


router = Router()


def escape_markdown(text):
    """Экранирует специальные символы MarkdownV2"""
    chars = [
        "_",
        "*",
        "[",
        "]",
        "(",
        ")",
        "~",
        "`",
        ">",
        "#",
        "+",
        "-",
        "=",
        "|",
        "{",
        "}",
        ".",
        "!",
    ]
    for char in chars:
        text = text.replace(char, f"\\{char}")
    return text


def format_to_html(text):
    # Заголовки
    text = re.sub(r"### \*\*(.*?)\*\*", r"<b><u>\1</u></b>", text)

    # Жирный текст
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)

    # Курсив
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)

    # Разделители - заменяем на строку символов
    text = text.replace("---", "—————————")

    return text


async def check_subscription(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status not in ["left", "kicked", "banned"]
    except Exception as e:
        logger.error(f"Subscription check failed for user {user_id}: {str(e)}")
        return False


def require_access(func):
    @wraps(func)
    async def wrapper(message: types.Message, db: Database, *args, **kwargs):
        manager = await db.get_user_manager()
        user = await manager.get_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.language_code,
        )

        # Проверяем подписку независимо от текущего access_granted
        access_granted = await check_subscription(message.bot, user.user_id)

        if not access_granted:
            # Если не подписан, отправляем сообщение и прерываем выполнение
            await send_localized_message(
                message,
                "access_denied_subscription",
                user,
                channel=REQUIRED_CHANNEL,
                reply_markup=get_subscription_keyboard(user.language_code),
            )
            # Если access_granted был True, сбрасываем его в False
            if user.access_granted:
                await manager.update_user(
                    user.user_id,
                    {
                        "access_granted": False,
                        "tariff": "free",
                    },  # Сбрасываем тариф и доступ
                )
            return

        # Если подписан, но access_granted был False, обновляем
        if not user.access_granted:
            await manager.update_user(
                user.user_id,
                {
                    "access_granted": True,
                    "tariff": "paid",
                    "last_daily_reward": datetime.now(),
                },
            )
            user.access_granted = True
            user.tariff = "paid"

        # Выполняем основную функцию
        return await func(message, db, user=user, *args, **kwargs)

    return wrapper


def get_subscription_keyboard(language_code: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=get_text("join_channel_button", language_code),
                    url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("check_subscription_button", language_code),
                    callback_data="check_subscription",
                )
            ],
        ]
    )


async def send_localized_message(
    message: types.Message,
    key: str,
    user: User,
    reply_markup: Optional[types.InlineKeyboardMarkup] = None,
    return_text: bool = False,
    **kwargs,
) -> Union[str, None]:
    kwargs.setdefault("username", user.username or "")
    kwargs.setdefault("invite_link", "")
    text = get_text(key, user.language_code, **kwargs)
    if return_text:
        return text
    await message.answer(text, reply_markup=reply_markup)
    return None


@router.message(Command("send_all"))
async def admin_send_all(message: types.Message, command: CommandObject, db: Database):
    if message.from_user.id != YOUR_ADMIN_ID:
        await message.answer("У вас нет прав для выполнения этой команды")
        return

    if not command.args:
        await message.answer("Использование: /send_all текст сообщения")
        return

    text = command.args
    users = await db.users.find({}).to_list(None)
    success_count = 0
    failed_count = 0

    for user in users:
        try:
            await message.bot.send_message(user["user_id"], text)
            success_count += 1
        except Exception as e:
            print(f"Ошибка отправки сообщения пользователю {user['user_id']}: {str(e)}")
            failed_count += 1

    await message.answer(
        f"Отправлено сообщений: {success_count}, не удалось отправить: {failed_count}"
    )


@router.message(Command("invite"))
@require_access
async def invite_command(message: types.Message, db: Database, user: User):
    invite_link = f"https://t.me/DockMixAIbot?start={user.user_id}"
    text = "\n\n".join(
        [
            f"🔗 Ваше реферальное посилання: {invite_link}",
            f"👥 Ви запросили: {len(user.invited_users)} користувачів",
        ]
    )
    await message.answer(text)


@router.message(Command("start"))
async def start_command(message: types.Message, db: Database):
    manager = await db.get_user_manager()
    user = await manager.get_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code,
    )

    invite_link = f"https://t.me/DockMixAIbot?start={user.user_id}"
    if len(message.text.split()) > 1:
        await process_referral(message, user, db)

    # Проверяем подписку всегда
    access_granted = await check_subscription(message.bot, user.user_id)
    if access_granted and not user.access_granted:
        await manager.update_user(
            user.user_id,
            {
                "access_granted": True,
                "tariff": "paid",
                "last_daily_reward": datetime.now(),
            },
        )
        user.access_granted = True
        user.tariff = "paid"
    elif not access_granted and user.access_granted:
        await manager.update_user(
            user.user_id,
            {"access_granted": False, "tariff": "free"},
        )
        user.access_granted = False
        user.tariff = "free"

    caption_key = "start" if access_granted else "access_denied_subscription"
    caption = await send_localized_message(
        message,
        caption_key,
        user,
        channel=None if access_granted else REQUIRED_CHANNEL,
        invite_link=invite_link,
        balance=user.balance,
        current_model=user.current_model,
        return_text=True,
    )

    # Отправляем фото только если у пользователя нет доступа
    reply_markup = (
        None if access_granted else get_subscription_keyboard(user.language_code)
    )
    if not access_granted:
        photo = FSInputFile("image/welcome.png")
        await message.answer_photo(photo, caption=caption, reply_markup=reply_markup)
    else:
        await message.answer(caption, reply_markup=reply_markup)


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: types.CallbackQuery, db: Database):
    manager = await db.get_user_manager()
    user = await manager.get_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.language_code,
    )
    access_granted = await check_subscription(callback.message.bot, user.user_id)

    if access_granted:
        await manager.update_user(
            user.user_id,
            {
                "access_granted": True,
                "tariff": "paid",
                "last_daily_reward": datetime.now(),
            },
        )
        await callback.message.edit_caption(
            caption=await send_localized_message(
                callback.message, "subscription_confirmed", user, return_text=True
            ),
            reply_markup=None,
        )
        welcome_text = await send_localized_message(
            callback.message,
            "start",
            user,
            balance=user.balance,
            current_model=user.current_model,
            return_text=True,
        )
        await callback.message.answer(welcome_text)
    else:
        await callback.answer(
            get_text("still_not_subscribed", user.language_code), show_alert=True
        )


@router.message(Command("profile"))
async def profile_command(message: types.Message, db: Database):
    manager = await db.get_user_manager()
    user = await manager.get_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code,
    )
    await send_localized_message(
        message,
        "profile",
        user,
        user_id=user.user_id,
        balance=user.balance,
        current_model=user.current_model,
    )


@router.message(Command("help"))
async def help_command(message: types.Message, db: Database):
    manager = await db.get_user_manager()
    user = await manager.get_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code,
    )
    await send_localized_message(
        message, "help", user, balance=user.balance, current_model=user.current_model
    )


@router.message(Command("reset"))
@require_access
async def reset_command(message: types.Message, db: Database, user: User):
    manager = await db.get_user_manager()
    await manager.update_user(user.user_id, {"messages_history": []})
    await send_localized_message(message, "history_reset", user)


@router.message(Command("models"))
@require_access
async def models_command(message: types.Message, db: Database, user: User):
    await send_localized_message(
        message,
        "select_model",
        user,
        current_model=user.current_model,
        reply_markup=get_models_keyboard(user.language_code),
    )


@router.callback_query(F.data.startswith("model_"))
@require_access
async def change_model_handler(callback: types.CallbackQuery, db: Database, user: User):
    model = callback.data.split("_")[1]
    manager = await db.get_user_manager()
    await manager.update_user(user.user_id, {"current_model": model})
    await send_localized_message(
        callback.message, "model_changed", user, model=MODEL_NAMES[model]
    )


@router.message(Command("image"))
@require_access
async def image_command(message: types.Message, db: Database, user: User):
    try:
        prompt = message.text.split("/image", 1)[1].strip()
    except IndexError:
        await send_localized_message(message, "image_prompt_required", user)
        return

    if user.balance < IMAGE_COST:
        await message.answer("У вас недостатньо токенів для генерації зображення.")
        return

    try:
        await message.bot.send_chat_action(
            chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO
        )
        gpt_service = MODEL_SERVICES[GPT_MODEL]
        image_url = await gpt_service.generate_image(prompt)
        await message.answer_photo(image_url)

        manager = await db.get_user_manager()
        await manager.update_balance_and_history(
            user.user_id, IMAGE_COST, DALLE_MODEL, prompt, image_url
        )
    except Exception as e:
        logger.error(f"Image generation failed: {str(e)}")
        await message.answer(f"Помилка генерації зображення: {str(e)}")


@router.message(Command("audio"))
@require_access
async def audio_command(message: types.Message, db: Database, user: User):
    try:
        text = message.text.split("/audio", 1)[1].strip()
    except IndexError:
        await send_localized_message(message, "audio_prompt_required", user)
        return

    if user.balance < 5:
        await message.answer("У вас недостатньо токенів для генерації аудіо.")
        return

    try:
        await message.bot.send_chat_action(
            chat_id=message.chat.id, action=ChatAction.RECORD_VOICE
        )

        gpt_service = MODEL_SERVICES[GPT_MODEL]
        output_path = f"audio_{message.from_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3"

        await gpt_service.text_to_speech(text, output_path=output_path)

        if os.path.exists(output_path):
            audio = FSInputFile(output_path)
            await message.answer_voice(audio)

            # Дожидаемся завершения отправки, потом удаляем файл
            await asyncio.sleep(1)
            os.remove(output_path)

            manager = await db.get_user_manager()
            await manager.update_balance_and_history(
                user.user_id, 5, "tts-1", text, "audio_generated"
            )
        else:
            await message.answer("Помилка: файл аудіо не був створений")
    except Exception as e:
        logger.error(f"Audio generation failed: {str(e)}")
        await message.answer(f"Помилка генерації аудіо: {str(e)}")


async def process_referral(message: types.Message, user: User, db: Database) -> None:
    if len(message.text.split()) <= 1:
        return
    try:
        inviter_id = int(message.text.split()[1])
        if inviter_id == user.user_id:
            await message.answer("❌ Ви не можете запросити самого себе!")
            return

        inviter = await db.users.find_one({"user_id": inviter_id})
        if not inviter or message.from_user.id in inviter.get("invited_users", []):
            return

        manager = await db.get_user_manager()
        await manager.add_invited_user(inviter_id, message.from_user.id)
        await send_inviter_notification(
            inviter_id, len(inviter.get("invited_users", []) + 1), db, message.bot
        )
    except (ValueError, TypeError) as e:
        logger.error(f"Помилка обробки реферала: {str(e)}")


async def send_inviter_notification(
    inviter_id: int, invited_count: int, db: Database, bot
) -> None:
    manager = await db.get_user_manager()
    user = await manager.get_user(
        inviter_id, None, "en"
    )  # Username не нужен для уведомления
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
async def handle_message(message: types.Message, db: Database, user: User):
    # Проверка баланса
    tokens_cost = 0 if user.current_model == "tts-1" else 1
    if user.balance < tokens_cost:
        next_day = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        await send_localized_message(message, "no_tokens", user, next_day=next_day)
        return

    # Отправляем сообщение об ожидании
    wait_message = await message.answer(
        "⏳ Ваш запит обробляється, будь ласка, зачекайте..."
    )

    try:
        await message.bot.send_chat_action(
            chat_id=message.chat.id, action=ChatAction.TYPING
        )
        service = MODEL_SERVICES.get(user.current_model)
        if not service:
            await message.bot.delete_message(message.chat.id, wait_message.message_id)
            await message.answer(
                "❌ Невідома модель, спробуйте вибрати ще раз модель /models"
            )
            return

        # Обработка сообщения
        if message.photo:
            # Обработка фото...
            photo = message.photo[-1]
            file = await message.bot.get_file(photo.file_id)
            file_path = f"temp_{message.from_user.id}_{photo.file_id}.jpg"
            await message.bot.download_file(file.file_path, file_path)
            response = await service.read_image(file_path)
            import os

            os.remove(file_path)
        else:
            # Обработка текста...
            history = user.messages_history[-5:]
            context = [
                {
                    "role": "user" if i % 2 == 0 else "assistant",
                    "content": entry["message" if i % 2 == 0 else "response"],
                }
                for i, entry in enumerate(history)
            ]
            response = await service.get_response(message.text, context=context)

        # Обновление баланса
        manager = await db.get_user_manager()
        if not message.photo:
            await manager.update_balance_and_history(
                user.user_id, tokens_cost, user.current_model, message.text, response
            )
        else:
            await manager.update_balance_and_history(
                user.user_id, tokens_cost, user.current_model, "", response
            )

        # Удаляем сообщение об ожидании
        await message.bot.delete_message(message.chat.id, wait_message.message_id)

        # Отправка ответа
        try:
            formatted_response = format_to_html(response)
            await message.answer(formatted_response, parse_mode=ParseMode.HTML)
        except Exception as e:
            await message.answer(response)
            logger.error(f"HTML format error: {str(e)}")
    except Exception as e:
        # Удаляем сообщение об ожидании при ошибке
        await message.bot.delete_message(message.chat.id, wait_message.message_id)
        logger.error(f"Message handling failed: {str(e)}")
        await message.answer(f"Помилка обробки повідомлення: {str(e)}")
