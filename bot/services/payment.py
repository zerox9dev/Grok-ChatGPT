import stripe

from config import STRIPE_API_KEY

stripe.api_key = STRIPE_API_KEY


class PaymentService:
    @staticmethod
    async def create_payment(amount: int, currency: str = "usd") -> dict:
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": currency,
                            "product_data": {
                                "name": f"{amount} токенов",
                            },
                            "unit_amount": amount * 100,  # Stripe uses cents
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url="https://t.me/AI_GuideBot",
                cancel_url="https://t.me/AI_GuideBot",
            )
            return {"payment_url": session.url, "payment_id": session.id}
        except Exception as e:
            raise Exception(f"Ошибка создания платежа: {str(e)}")
