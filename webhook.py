import stripe
from aiogram import Bot
from aiohttp import web
from motor.motor_asyncio import AsyncIOMotorClient

from config import BOT_TOKEN, MONGO_URL, STRIPE_WEBHOOK_SECRET


async def handle_stripe_webhook(request):
    try:
        payload = await request.text()
        sig_header = request.headers.get("Stripe-Signature")

        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )

        client = AsyncIOMotorClient(MONGO_URL)
        db = client.ai_bot
        bot = Bot(token=BOT_TOKEN)

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]

            user = await db.users.find_one({"payments.payment_id": session.id})
            if user:
                payment = next(
                    (p for p in user["payments"] if p["payment_id"] == session.id), None
                )

                if payment and payment["status"] == "pending":
                    # Обновляем статус и начисляем токены
                    await db.users.update_one(
                        {"_id": user["_id"]},
                        {
                            "$inc": {"balance": payment["tokens"]},
                            "$set": {"payments.$[elem].status": "completed"},
                        },
                        array_filters=[{"elem.payment_id": session.id}],
                    )

                    # Отправляем уведомление пользователю
                    await bot.send_message(
                        user["user_id"],
                        f"✅ Оплата успешно обработана!\n"
                        f"💰 На ваш баланс начислено {payment['tokens']} токенов\n"
                        f"💎 Текущий баланс: {user['balance'] + payment['tokens']} токенов",
                    )

        return web.Response(status=200)
    # В блоке except
    except Exception as e:
        error_message = str(e)
        print(f"Ошибка webhook: {error_message}")

        # Если есть информация о пользователе, отправляем ему уведомление
        if "user" in locals() and user:
            try:
                await bot.send_message(
                    user["user_id"],
                    f"❌ Ошибка при обработке платежа:\n"
                    f"└ {error_message}\n\n"
                    "🔄 Попробуйте оплатить снова или обратитесь в поддержку",
                )
            except Exception as notify_error:
                print(f"Ошибка отправки уведомления: {notify_error}")

        return web.Response(status=400, text=str(e))
