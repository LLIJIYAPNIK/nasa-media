from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from presentation.telegram.keyboards.subscription_button import build_subscription_button


def get_apod_kb(is_subscribed: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Несколько дат", callback_data="few_dates")],
            [InlineKeyboardButton(text="Определенная дата", callback_data="current_date")],
            [InlineKeyboardButton(text="Сегодня", callback_data="today_date")],
            [InlineKeyboardButton(text="Мой космический день рождения", callback_data="cosmic_birthday")],
            [build_subscription_button(is_subscribed, "apod")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_start")],
        ]
    )
