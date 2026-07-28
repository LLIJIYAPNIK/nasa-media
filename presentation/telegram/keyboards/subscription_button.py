from aiogram.types import InlineKeyboardButton


def build_subscription_button(is_subscribed: bool, prefix: str) -> InlineKeyboardButton:
    """Общая кнопка подписки/отписки для apod_kb/epic_kb/digest_kb — то же
    дублирование, из-за которого появился register_subscribe_handlers
    (subscribe_handler.py), просто на стороне клавиатуры, а не хендлера."""
    if is_subscribed:
        return InlineKeyboardButton(text="Отписаться от рассылки", callback_data=f"{prefix}_unsubscribe")
    return InlineKeyboardButton(text="Подключить рассылку", callback_data=f"{prefix}_subscribe")
