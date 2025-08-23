import os
from datetime import datetime, timedelta

from aiogram import Router, types
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramBadRequest

from bot.database.database import Database
from bot.database.models import User
from bot.services.ai_service import AIService

from .base import (
    get_user_decorator, send_localized_message, send_response_safely,
    MODEL_SERVICES, logger
)
from .agents import handle_agent_creation_conversation

async def safe_delete_message(bot, chat_id: int, message_id: int) -> None:
    # Безопасное удаление сообщения с обработкой ошибок
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest as e:
        # Сообщение уже удалено или не существует - это нормально
        if "message to delete not found" not in str(e).lower():
            logger.warning(f"Failed to delete message {message_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error deleting message {message_id}: {str(e)}")

# ================================================
# Роутер для сообщений
# ================================================
router = Router()

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
    # Подготовка контекста из истории сообщений
    context = []
    for i, entry in enumerate(history[-5:]):
        content_key = "message" if i % 2 == 0 else "response"
        content = entry.get(content_key, "")
        
        # Пропускаем сообщения с пустым содержимым
        if content and content.strip():
            context.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": content.strip(),
            })
    
    return context

# ================================================
# Главный обработчик сообщений
# ================================================
@router.message()
@get_user_decorator
async def handle_message(message: types.Message, db: Database, user: User):
    """Главный обработчик всех сообщений пользователей"""
    
    # Check if user is in conversation state (agent creation/editing)
    if await handle_agent_creation_conversation(message, db, user):
        return
    
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
        
        # Get system prompt from current agent if available
        current_agent = user.get_current_agent()
        base_system_prompt = current_agent.system_prompt if current_agent else ""
        
        # Добавляем ограничение длины ответа для всех запросов
        length_constraint = "ВАЖНО: Ответ должен быть не длиннее 4000 символов. Если нужно показать длинный код - сократи его или покажи только ключевые части."
        
        if base_system_prompt:
            system_prompt = f"{base_system_prompt}\n\n{length_constraint}"
        else:
            system_prompt = length_constraint

        # Обработка сообщения в зависимости от типа
        if message.photo:
            response = await process_image_message(message, service)
            content = ""
        else:
            # Get history for current context (agent or default)
            current_history = user.get_current_history()
            context = prepare_context_from_history(current_history)
            response = await service.get_response(
                message.text, context=context, system_prompt=system_prompt
            )
            content = message.text

        # Обновление баланса и истории (включаем информацию об агенте)
        manager = await db.get_user_manager()
        model_info = user.current_model
        if current_agent:
            model_info += f" (Agent: {current_agent.name})"
        
        await manager.update_balance_and_history(
            user.user_id, tokens_cost, model_info, content, response, 
            agent_id=current_agent.agent_id if current_agent else None
        )

        # Безопасно удаляем сообщение ожидания и отправляем ответ
        await safe_delete_message(message.bot, message.chat.id, wait_message.message_id)
        await send_response_safely(message, response)

    except Exception as e:
        await safe_delete_message(message.bot, message.chat.id, wait_message.message_id)
        logger.error(f"Message handling failed: {str(e)}")
        await message.answer(f"Помилка обробки повідомлення: {str(e)}")
