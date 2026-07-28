from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from application.subscriptions.manage_subscription import SetSubscription
from domain.media.value_objects import MediaSourceKind
from presentation.telegram.message_guards import require_message

_LABELS = {
    MediaSourceKind.APOD: "APOD",
    MediaSourceKind.EPIC: "EPIC",
    MediaSourceKind.DIGEST: "сводки",
    MediaSourceKind.WEEKLY_HIGHLIGHTS: "итогов недели",
}


def register_subscribe_handlers(router: Router, source: MediaSourceKind, set_subscription: SetSubscription) -> None:
    """apod_router и epic_router отличались только источником и подписью —
    один хендлер вместо двух копий."""
    prefix = source.value
    label = _LABELS[source]

    @router.callback_query(F.data.in_({f"{prefix}_subscribe", f"{prefix}_unsubscribe"}))
    async def subscribe(callback_query: CallbackQuery) -> None:
        message = require_message(callback_query)
        await message.delete()
        value = callback_query.data == f"{prefix}_subscribe"
        await set_subscription.execute(message.chat.id, source, value)
        text = f"Вы подписались на рассылку {label}" if value else f"Вы отписались от рассылки {label}"
        await message.answer(text)
