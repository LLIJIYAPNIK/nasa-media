from __future__ import annotations

from datetime import date

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender

from application.media.deliver_media import DeliverMediaForDate
from application.subscriptions.manage_subscription import SetSubscription
from application.users.register_user import GetOrCreateUser
from domain.media.value_objects import MediaSourceKind
from presentation.telegram.keyboards.digest_kb import get_digest_kb
from presentation.telegram.message_guards import require_bot, require_message
from presentation.telegram.subscribe_handler import register_subscribe_handlers


def build_digest_router(
    deliver_digest: DeliverMediaForDate,
    set_subscription: SetSubscription,
    get_or_create_user: GetOrCreateUser,
) -> Router:
    router = Router()

    @router.callback_query(F.data == "digest")
    async def cmd_digest(callback_query: CallbackQuery) -> None:
        message = require_message(callback_query)
        await message.delete()
        user = await get_or_create_user.execute(message.chat.id)
        await message.answer(
            "Сводка за сегодня — космическая погода, ближайший астероид, заметное событие на Земле и APOD дня.",
            reply_markup=get_digest_kb(user.digest_subscribed),
        )

    @router.callback_query(F.data == "digest_show")
    async def digest_show(callback_query: CallbackQuery) -> None:
        message = require_message(callback_query)
        async with ChatActionSender.typing(bot=require_bot(message), chat_id=message.chat.id):
            await deliver_digest.execute(date.today(), message.chat.id)

    register_subscribe_handlers(router, MediaSourceKind.DIGEST, set_subscription)

    return router
