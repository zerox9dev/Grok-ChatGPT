from datetime import datetime, timedelta

from aiogram import F, Router, types
from aiogram.filters import Command, CommandObject
from aiogram.exceptions import TelegramBadRequest

from bot.database.database import Database
from bot.database.models import User
from bot.keyboards.keyboards import get_models_keyboard
from bot.utils.localization import get_text
from config import YOUR_ADMIN_ID, REFERRAL_TOKENS

from .base import (
    get_user_decorator, send_localized_message, create_simple_command_handler, logger
)

# ================================================
# Роутер для команд
# ================================================
router = Router()

# ================================================
# Вспомогательные функции
# ================================================
async def process_referral(message: types.Message, user: User, db: Database) -> None:
    """Обработка реферальной ссылки"""
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
    """Отправка уведомления пригласившему пользователю"""
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
# Команды бота
# ================================================
@router.message(Command("send_all"))
async def admin_send_all(message: types.Message, command: CommandObject, db: Database):
    """Административная команда для массовой рассылки"""
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

@router.message(Command("start"))
async def start_command(message: types.Message, db: Database):
    """Команда запуска бота"""
    manager = await db.get_user_manager()
    user = await manager.get_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code,
    )

    # Обрабатываем реферальную ссылку если есть
    if len(message.text.split()) > 1:
        await process_referral(message, user, db)

    await send_localized_message(message, "start", user)

@router.message(Command("invite"))
@get_user_decorator
async def invite_command(message: types.Message, db: Database, user: User):
    """Команда для получения реферальной ссылки"""
    invite_link = f"https://t.me/DockMixAIbot?start={user.user_id}"
    text = "\n\n".join(
        [
            f"🔗 Ваше реферальное посилання: {invite_link}",
            f"👥 Ви запросили: {len(user.invited_users)} користувачів",
        ]
    )
    await message.answer(text)

@router.message(Command("profile"))
@get_user_decorator
async def profile_command(message: types.Message, db: Database, user: User):
    """Показать профиль пользователя с информацией о текущем режиме"""
    # Get current agent and mode info
    current_agent = user.get_current_agent()
    current_history = user.get_current_history()
    
    if current_agent:
        current_mode = get_text("profile_mode_agent", user.language_code, agent_name=current_agent.name)
    else:
        current_mode = get_text("profile_mode_default", user.language_code)
    
    history_count = len(current_history)
    
    await send_localized_message(
        message, "profile", user,
        current_mode=current_mode,
        history_count=history_count
    )

@router.message(Command("help"))
async def help_command(message: types.Message, db: Database):
    """Показать справку"""
    await create_simple_command_handler("help")(message, db)

@router.message(Command("reset"))
@get_user_decorator
async def reset_command(message: types.Message, db: Database, user: User):
    """Очистить историю сообщений для текущего контекста"""
    manager = await db.get_user_manager()
    
    # Get current agent to determine which history to clear
    current_agent = user.get_current_agent()
    agent_id = current_agent.agent_id if current_agent else None
    
    # Clear history for current context
    await manager.clear_history(user.user_id, agent_id)
    
    # Send localized confirmation message
    if current_agent:
        await send_localized_message(
            message, "history_reset_agent", user, agent_name=current_agent.name
        )
    else:
        await send_localized_message(message, "history_reset_default", user)

@router.message(Command("models"))
@get_user_decorator
async def models_command(message: types.Message, db: Database, user: User):
    """Показать доступные модели"""
    await send_localized_message(
        message, "select_model", user,
        reply_markup=get_models_keyboard(user.language_code)
    )

@router.callback_query(F.data.startswith("model_"))
@get_user_decorator
async def change_model_handler(callback: types.CallbackQuery, db: Database, user: User):
    """Изменить текущую модель"""
    model = callback.data.split("_")[1]
    manager = await db.get_user_manager()
    await manager.update_user(user.user_id, {"current_model": model})
    await send_localized_message(callback.message, "model_changed", user, model=model)
