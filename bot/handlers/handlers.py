import logging
import re
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Union, Callable, Any

from aiogram import F, Router, types
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command, CommandObject



from bot.database.database import Database, UserManager
from bot.database.models import User
from bot.keyboards.keyboards import get_models_keyboard
from bot.locales.utils import get_text
from bot.services.ai_service import AIService
from config import (
    REFERRAL_TOKENS,
    YOUR_ADMIN_ID,
)

# ================================================
# Инициализация и конфигурация
# ================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_SERVICES = {}  # Кэш сервисов моделей
router = Router()

# ================================================
# Утилитные функции для форматирования
# ================================================
def format_to_html(text: str) -> str:
    """Универсальная функция форматирования markdown в HTML"""
    patterns = [
        (r"### \*\*(.*?)\*\*", r"<b><u>\1</u></b>"),  # Заголовки
        (r"\*\*(.*?)\*\*", r"<b>\1</b>"),              # Жирный текст
        (r"\*(.*?)\*", r"<i>\1</i>"),                  # Курсив
        (r"---", "—————————"),                          # Разделители
    ]
    
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text





# ================================================
# Универсальные декораторы
# ================================================
def require_access(func: Callable) -> Callable:
    """Универсальный декоратор для проверки доступа и получения пользователя"""
    @wraps(func)
    async def wrapper(message: types.Message, db: Database, *args, **kwargs):
        manager = await db.get_user_manager()
        user = await manager.get_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.language_code,
        )

        # Автоматически предоставляем доступ всем пользователям
        if not user.access_granted:
            await manager.update_user(user.user_id, {
                "access_granted": True,
                "tariff": "paid",
                "last_daily_reward": datetime.now(),
            })
            user.access_granted = True
            user.tariff = "paid"

        return await func(message, db, user=user, *args, **kwargs)
    return wrapper





# ================================================
# Универсальные функции-хелперы
# ================================================
async def send_localized_message(
    message: types.Message, key: str, user: User,
    reply_markup: Optional[types.InlineKeyboardMarkup] = None,
    return_text: bool = False, **kwargs
) -> Optional[str]:
    """Универсальная функция для отправки локализованных сообщений"""
    kwargs.update({
        "user_id": user.user_id,
        "username": user.username or "",
        "invite_link": f"https://t.me/DockMixAIbot?start={user.user_id}",
        "balance": getattr(user, 'balance', 0),
        "current_model": getattr(user, 'current_model', 'GPT')
    })
    
    text = get_text(key, user.language_code, **kwargs)
    if return_text:
        return text
    await message.answer(text, reply_markup=reply_markup)
    return None


def create_simple_command_handler(message_key: str) -> Callable:
    """Фабрика для создания простых обработчиков команд"""
    @require_access
    async def handler(message: types.Message, db: Database, user: User):
        await send_localized_message(message, message_key, user)
    return handler


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


async def handle_user_initialization(message: types.Message, db: Database) -> User:
    """Инициализация пользователя с автоматическим предоставлением доступа"""
    manager = await db.get_user_manager()
    user = await manager.get_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code,
    )

    # Обрабатываем реферальную ссылку если есть
    if len(message.text.split()) > 1:
        await process_referral(message, user, db)

    # Автоматически предоставляем доступ
    if not user.access_granted:
        await manager.update_user(user.user_id, {
            "access_granted": True,
            "tariff": "paid",
            "last_daily_reward": datetime.now(),
        })
        user.access_granted = True
        user.tariff = "paid"

    return user


@router.message(Command("start"))
async def start_command(message: types.Message, db: Database):
    """Команда запуска бота"""
    user = await handle_user_initialization(message, db)
    await send_localized_message(message, "start", user)





# ================================================
# Обработчики команд (упрощенные с помощью универсальных функций)
# ================================================
@router.message(Command("profile"))
async def profile_command(message: types.Message, db: Database):
    """Показать профиль пользователя"""
    await create_simple_command_handler("profile")(message, db)


@router.message(Command("help"))
async def help_command(message: types.Message, db: Database):
    """Показать справку"""
    await create_simple_command_handler("help")(message, db)


@router.message(Command("reset"))
@require_access
async def reset_command(message: types.Message, db: Database, user: User):
    """Очистить историю сообщений"""
    manager = await db.get_user_manager()
    await manager.update_user(user.user_id, {"messages_history": []})
    await send_localized_message(message, "history_reset", user)


@router.message(Command("models"))
@require_access
async def models_command(message: types.Message, db: Database, user: User):
    """Показать доступные модели"""
    await send_localized_message(
        message, "select_model", user,
        reply_markup=get_models_keyboard(user.language_code)
    )


@router.callback_query(F.data.startswith("model_"))
@require_access
async def change_model_handler(callback: types.CallbackQuery, db: Database, user: User):
    """Изменить текущую модель"""
    model = callback.data.split("_")[1]
    manager = await db.get_user_manager()
    await manager.update_user(user.user_id, {"current_model": model})
    await send_localized_message(callback.message, "model_changed", user, model=model)











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


# ================================================
# Вспомогательные функции для обработки сообщений
# ================================================
def get_ai_service(model_name: str) -> AIService:
    """Получить или создать AI сервис для модели"""
    if model_name not in MODEL_SERVICES:
        MODEL_SERVICES[model_name] = AIService(model_name=model_name)
    return MODEL_SERVICES[model_name]


async def process_image_message(message: types.Message, service: AIService) -> str:
    """Обработка сообщения с изображением"""
    import os
    
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_path = f"temp_{message.from_user.id}_{photo.file_id}.jpg"
    
    try:
        await message.bot.download_file(file.file_path, file_path)
        response = await service.read_image(file_path)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
    
    return response


def prepare_context_from_history(history: list) -> list:
    """Подготовка контекста из истории сообщений"""
    return [
        {
            "role": "user" if i % 2 == 0 else "assistant",
            "content": entry.get("message" if i % 2 == 0 else "response", ""),
        }
        for i, entry in enumerate(history[-5:])
    ]


async def send_response_safely(message: types.Message, response: str) -> None:
    """Безопасная отправка ответа с fallback форматированием"""
    try:
        formatted_response = format_to_html(response)
        await message.answer(formatted_response, parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(response)
        logger.error(f"HTML format error: {str(e)}")


@router.message()
@require_access
async def handle_message(message: types.Message, db: Database, user: User):
    """Главный обработчик всех сообщений пользователей"""
    tokens_cost = 1
    
    # Проверка баланса
    if user.balance < tokens_cost:
        next_day = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        await send_localized_message(message, "no_tokens", user, next_day=next_day)
        return

    wait_message = await message.answer("⏳")

    try:
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        service = get_ai_service(user.current_model)

        # Обработка сообщения в зависимости от типа
        if message.photo:
            response = await process_image_message(message, service)
            content = ""
        else:
            context = prepare_context_from_history(user.messages_history)
            response = await service.get_response(message.text, context=context)
            content = message.text

        # Обновление баланса и истории
        manager = await db.get_user_manager()
        await manager.update_balance_and_history(
            user.user_id, tokens_cost, user.current_model, content, response
        )

        # Удаляем сообщение ожидания и отправляем ответ
        await message.bot.delete_message(message.chat.id, wait_message.message_id)
        await send_response_safely(message, response)

    except Exception as e:
        await message.bot.delete_message(message.chat.id, wait_message.message_id)
        logger.error(f"Message handling failed: {str(e)}")
        await message.answer(f"Помилка обробки повідомлення: {str(e)}")
