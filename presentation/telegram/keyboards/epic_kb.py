from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from presentation.telegram.keyboards.subscription_button import build_subscription_button


def get_epic_kb(is_subscribed: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [build_subscription_button(is_subscribed, "epic")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_start")],
        ]
    )
