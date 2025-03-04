from aiogram import types

from bot.database.database import Database
from bot.locales.utils import get_text
from config import REFERRAL_TOKENS, REQUIRED_CHANNEL


async def send_access_update_notification(db: Database, bot):
    """Отправляет уведомление о новой системе доступа пользователям без access_granted"""
    # Получаем всех пользователей без access_granted
    users_without_access = await db.users.find({"access_granted": False}).to_list(None)

    success_count = 0
    failed_count = 0

    for user in users_without_access:
        try:
            user_lang = user.get("language_code", "en")

            # Создаем клавиатуру с кнопкой подписки
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text=get_text("join_channel_button", user_lang),
                            url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}",
                        )
                    ],
                    [
                        types.InlineKeyboardButton(
                            text=get_text("check_subscription_button", user_lang),
                            callback_data="check_subscription",
                        )
                    ],
                ]
            )

            # Отправляем сообщение о новой системе доступа
            await bot.send_message(
                user["user_id"],
                get_text(
                    "access_system_update",
                    user_lang,
                    channel=REQUIRED_CHANNEL,
                    referral_tokens=REFERRAL_TOKENS,
                ),
                reply_markup=keyboard,
            )
            success_count += 1
        except Exception as e:
            print(
                f"Ошибка отправки уведомления пользователю {user['user_id']}: {str(e)}"
            )
            failed_count += 1

    print(
        f"Отправлено уведомлений: {success_count}, не удалось отправить: {failed_count}"
    )
    return success_count, failed_count
