from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="APOD", callback_data="apod")],
            [InlineKeyboardButton(text="EPIC", callback_data="epic")],
        ]
    )
