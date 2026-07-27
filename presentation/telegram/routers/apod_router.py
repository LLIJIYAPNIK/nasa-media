from __future__ import annotations

from datetime import date

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.chat_action import ChatActionSender

from application.media.deliver_media import DeliverMediaForDate
from application.media.deliver_media_range import DeliverMediaForDateRange
from application.subscriptions.manage_subscription import SetSubscription
from application.users.register_user import GetOrCreateUser
from domain.media.exceptions import MediaNotAvailable
from domain.media.value_objects import DateRange, InvalidMediaDate, MediaSourceKind
from presentation.telegram.date_input import parse_requested_date
from presentation.telegram.keyboards.apod_kb import get_apod_kb
from presentation.telegram.message_guards import require_bot, require_message
from presentation.telegram.states import ApodCurrentDateForm, ApodDateRangeForm
from presentation.telegram.subscribe_handler import register_subscribe_handlers


def build_apod_router(
    deliver_media: DeliverMediaForDate,
    deliver_media_range: DeliverMediaForDateRange,
    set_subscription: SetSubscription,
    get_or_create_user: GetOrCreateUser,
    apod_lower_bound: date,
) -> Router:
    router = Router()

    async def deliver_to(message: Message, chat_id: int, day: date) -> None:
        async with ChatActionSender.upload_photo(bot=require_bot(message), chat_id=chat_id):
            try:
                await deliver_media.execute(day, chat_id)
            except MediaNotAvailable:
                await message.answer(f"NASA ещё не добавили изображение за {day}")

    @router.callback_query(F.data == "apod")
    async def cmd_apod(callback_query: CallbackQuery) -> None:
        message = require_message(callback_query)
        await message.delete()
        user = await get_or_create_user.execute(message.chat.id)
        await message.answer(
            "APOD - Astronomy Picture of the Day\n\nВыберите вариант:",
            reply_markup=get_apod_kb(user.apod_subscribed),
        )

    @router.callback_query(F.data == "today_date")
    async def get_today_date(callback_query: CallbackQuery) -> None:
        message = require_message(callback_query)
        await deliver_to(message, message.chat.id, date.today())

    @router.callback_query(F.data == "current_date")
    async def get_current_date_data(callback_query: CallbackQuery, state: FSMContext) -> None:
        message = require_message(callback_query)
        await state.set_state(ApodCurrentDateForm.current_date)
        await message.delete()
        await message.answer("Введите дату (ГГГГ-ММ-ДД):")

    @router.message(StateFilter(ApodCurrentDateForm.current_date))
    async def finish_current_date(message: Message, state: FSMContext) -> None:
        try:
            requested = parse_requested_date(message.text, apod_lower_bound, date.today())
        except InvalidMediaDate as error:
            await message.reply(str(error))
            return
        await deliver_to(message, message.chat.id, requested)
        await state.clear()

    @router.callback_query(F.data == "few_dates")
    async def get_few_dates(callback_query: CallbackQuery, state: FSMContext) -> None:
        message = require_message(callback_query)
        await state.set_state(ApodDateRangeForm.start_date)
        await message.delete()
        await message.answer(
            "Чтобы получить фото во временном промежутке нужно заполнить данные для начала и конца "
            "промежутка.\nДавайте начнём: укажите начало временного промежутка:"
        )

    @router.message(StateFilter(ApodDateRangeForm.start_date))
    async def get_end_date(message: Message, state: FSMContext) -> None:
        try:
            parse_requested_date(message.text, apod_lower_bound, date.today())
        except InvalidMediaDate as error:
            await message.reply(str(error))
            return
        await state.update_data(start_date=message.text)
        await state.set_state(ApodDateRangeForm.end_date)
        await message.answer("Конечная дата (разница не более 5 дней):")

    @router.message(StateFilter(ApodDateRangeForm.end_date))
    async def finish(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        try:
            end = parse_requested_date(message.text, apod_lower_bound, date.today())
            date_range = DateRange(start=date.fromisoformat(data["start_date"]), end=end)
        except InvalidMediaDate as error:
            await message.reply(str(error))
            return

        async with ChatActionSender.upload_photo(bot=require_bot(message), chat_id=message.chat.id):
            unavailable_dates = await deliver_media_range.execute(date_range, message.chat.id)

        await state.clear()
        if unavailable_dates:
            missing = ", ".join(str(day) for day in unavailable_dates)
            await message.answer(f"Готово, но NASA ещё не добавили изображения за: {missing}")
        else:
            await message.answer("Информация успешно сохранена!")

    register_subscribe_handlers(router, MediaSourceKind.APOD, set_subscription)

    return router
