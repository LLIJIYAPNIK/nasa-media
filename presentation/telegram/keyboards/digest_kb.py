from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_digest_kb(is_subscribed: bool) -> InlineKeyboardMarkup:
    subscription_button = (
        InlineKeyboardButton(text="Отписаться от рассылки", callback_data="digest_unsubscribe")
        if is_subscribed
        else InlineKeyboardButton(text="Подключить рассылку", callback_data="digest_subscribe")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Показать сводку", callback_data="digest_show")],
            [subscription_button],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_start")],
        ]
    )
