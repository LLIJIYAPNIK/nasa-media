from __future__ import annotations

from datetime import date

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.chat_action import ChatActionSender

from application.media.deliver_media import DeliverMediaForDate
from application.subscriptions.manage_subscription import SetSubscription
from application.users.register_user import GetOrCreateUser
from domain.media.exceptions import MediaNotAvailable
from domain.media.value_objects import EPIC_LOWER_BOUND, InvalidMediaDate, MediaSourceKind
from presentation.telegram.date_input import parse_requested_date
from presentation.telegram.keyboards.epic_kb import get_epic_kb
from presentation.telegram.message_guards import require_bot, require_message
from presentation.telegram.states import EpicDateForm
from presentation.telegram.subscribe_handler import register_subscribe_handlers


def build_epic_router(
    deliver_media: DeliverMediaForDate,
    set_subscription: SetSubscription,
    get_or_create_user: GetOrCreateUser,
) -> Router:
    router = Router()

    @router.callback_query(F.data == "epic")
    async def start(callback_query: CallbackQuery, state: FSMContext) -> None:
        message = require_message(callback_query)
        await state.set_state(EpicDateForm.date)
        await message.delete()
        user = await get_or_create_user.execute(message.chat.id)
        await message.answer(
            "EPIC - Earth Polychromatic Imaging Camera\n\nВведите дату (ГГГГ-ММ-ДД):",
            reply_markup=get_epic_kb(user.epic_subscribed),
        )

    @router.message(StateFilter(EpicDateForm.date))
    async def finish(message: Message, state: FSMContext) -> None:
        try:
            requested = parse_requested_date(message.text, EPIC_LOWER_BOUND, date.today())
        except InvalidMediaDate as error:
            await message.reply(str(error))
            return

        async with ChatActionSender.upload_photo(bot=require_bot(message), chat_id=message.chat.id):
            try:
                await deliver_media.execute(requested, message.chat.id)
            except MediaNotAvailable:
                await message.reply("У NASA нет изображений за этот день. Попробуйте другую дату.")
        await state.clear()

    register_subscribe_handlers(router, MediaSourceKind.EPIC, set_subscription)

    return router
