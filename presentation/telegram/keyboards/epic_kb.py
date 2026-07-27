from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_epic_kb(is_subscribed: bool) -> InlineKeyboardMarkup:
    subscription_button = (
        InlineKeyboardButton(text="Отписаться от рассылки", callback_data="epic_unsubscribe")
        if is_subscribed
        else InlineKeyboardButton(text="Подключить рассылку", callback_data="epic_subscribe")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [subscription_button],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_start")],
        ]
    )
