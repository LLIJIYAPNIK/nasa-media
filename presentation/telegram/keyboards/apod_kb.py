from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_apod_kb(is_subscribed: bool) -> InlineKeyboardMarkup:
    subscription_button = (
        InlineKeyboardButton(text="Отписаться от рассылки", callback_data="apod_unsubscribe")
        if is_subscribed
        else InlineKeyboardButton(text="Подключить рассылку", callback_data="apod_subscribe")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Несколько дат", callback_data="few_dates")],
            [InlineKeyboardButton(text="Определенная дата", callback_data="current_date")],
            [InlineKeyboardButton(text="Сегодня", callback_data="today_date")],
            [subscription_button],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_start")],
        ]
    )
