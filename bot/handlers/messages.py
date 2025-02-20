from datetime import datetime

from aiogram import F, Router, types
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter

from bot.services.claude import ClaudeService
from bot.services.gpt import GPTService
from config import CLAUDE_MODEL, GPT_MODEL
from database import Database

router = Router()
gpt_service = GPTService()
claude_service = ClaudeService()


@router.message(StateFilter(None))
async def handle_message(message: types.Message, db: Database):
    user = await db.users.find_one({"user_id": message.from_user.id})

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
        if user["current_model"] == GPT_MODEL:
            response = await gpt_service.get_response(message.text)
        elif user["current_model"] == CLAUDE_MODEL:
            response = await claude_service.get_response(message.text)
        else:
            await message.answer("❌ Неизвестная модель")
            return

        # Сохраняем историю и вычитаем токены
        await db.users.update_one(
            {"user_id": message.from_user.id},
            {
                "$inc": {"balance": -1},
                "$push": {
                    "messages_history": {
                        "model": user["current_model"],
                        "message": message.text,
                        "response": response,
                        "timestamp": datetime.utcnow(),
                    }
                },
            },
        )

        await message.answer(response)
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка: {str(e)}")
