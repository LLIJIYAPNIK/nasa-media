from __future__ import annotations

from typing import cast

from aiogram import Bot
from aiogram.types import CallbackQuery, Message


def require_message(callback_query: CallbackQuery) -> Message:
    """CallbackQuery.message is typed Message | InaccessibleMessage | None
    by aiogram (business connections, very old messages) — our handlers
    only ever act on callbacks from a keyboard we just sent in the same
    chat, so a live Message is a real precondition. Checked for None at
    runtime; InaccessibleMessage is narrowed away with cast rather than
    isinstance so this stays compatible with lightweight duck-typed
    fakes in tests instead of requiring fully constructed aiogram objects."""
    assert callback_query.message is not None
    return cast(Message, callback_query.message)


def require_bot(message: Message) -> Bot:
    """Message.bot is Optional in aiogram's types (relevant for messages
    built outside the dispatcher); any message actually delivered by
    aiogram to a handler always has it set."""
    assert message.bot is not None
    return message.bot
