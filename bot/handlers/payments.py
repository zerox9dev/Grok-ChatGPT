from aiogram import F, Router, types
from aiogram.filters import Command

from bot.keyboards.main import get_start_keyboard
from bot.services.payment import PaymentService
from database import Database

router = Router()
payment_service = PaymentService()

PRICES = {
    "100": {"tokens": 100, "amount": 5},
    "500": {"tokens": 500, "amount": 20},
    "1000": {"tokens": 1000, "amount": 35},
    "5000": {"tokens": 5000, "amount": 150},
}


@router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: types.CallbackQuery, db: Database):
    amount = callback.data.split("_")[1]

    if amount not in PRICES:
        await callback.message.answer("❌ Ошибка: неверная сумма оплаты")
        await callback.answer()
        return

    try:
        payment_data = await payment_service.create_payment(
            amount=PRICES[amount]["amount"]
        )

        # Сохраняем информацию о платеже
        await db.users.update_one(
            {"user_id": callback.from_user.id},
            {
                "$push": {
                    "payments": {
                        "payment_id": payment_data["payment_id"],
                        "amount": PRICES[amount]["amount"],
                        "tokens": PRICES[amount]["tokens"],
                        "status": "pending",
                    }
                }
            },
        )

        await callback.message.answer(
            f"💳 Оплата {PRICES[amount]['amount']}$ за {PRICES[amount]['tokens']} токенов\n\n"
            f"🔗 Ссылка на оплату: {payment_data['payment_url']}\n\n"
            "⏳ После оплаты токены будут начислены автоматически"
        )

    except Exception as e:
        error_message = str(e)
        await callback.message.answer(
            f"❌ Ошибка при создании платежа:\n"
            f"└ {error_message}\n\n"
            "🔄 Попробуйте позже или обратитесь в поддержку"
        )

    await callback.answer()


# Добавим обработчик ошибок в webhook.py
@router.callback_query(F.data == "payment_error")
async def handle_payment_error(callback: types.CallbackQuery):
    await callback.message.answer(
        "❌ Платеж не удался\n"
        "Возможные причины:\n"
        "1. Недостаточно средств\n"
        "2. Банк отклонил платеж\n"
        "3. Технические проблемы\n\n"
        "🔄 Попробуйте снова или используйте другую карту"
    )
    await callback.answer()
