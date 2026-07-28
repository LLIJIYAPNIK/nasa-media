from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from presentation.telegram.keyboards.subscription_button import build_subscription_button


def get_digest_kb(is_subscribed: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Показать сводку", callback_data="digest_show")],
            [build_subscription_button(is_subscribed, "digest")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_start")],
        ]
    )
