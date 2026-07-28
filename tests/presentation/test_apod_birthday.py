from datetime import date
from typing import cast
from unittest.mock import AsyncMock

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from domain.users.cosmic_facts import build_cosmic_facts_lines
from domain.users.entities import User
from presentation.telegram.routers.apod_router import build_apod_router
from presentation.telegram.states import ApodBirthdayForm
from tests.presentation.fake_telegram import FakeCallbackQuery, FakeMessage

APOD_LOWER_BOUND = date(1995, 6, 16)


def _router(
    deliver_media: AsyncMock, get_or_create_user: AsyncMock, set_birthday: AsyncMock, greeting_sender: AsyncMock
) -> Router:
    return build_apod_router(
        deliver_media=deliver_media,
        deliver_media_range=AsyncMock(),
        set_subscription=AsyncMock(),
        get_or_create_user=get_or_create_user,
        set_birthday=set_birthday,
        greeting_sender=greeting_sender,
        apod_lower_bound=APOD_LOWER_BOUND,
    )


async def test_cosmic_birthday_asks_for_date_when_not_set_yet():
    get_or_create_user = AsyncMock()
    get_or_create_user.execute.return_value = User(chat_id=1, birthday=None)
    deliver_media = AsyncMock()
    greeting_sender = AsyncMock()
    router = _router(deliver_media, get_or_create_user, AsyncMock(), greeting_sender)
    callback_query = FakeCallbackQuery(data="cosmic_birthday", chat_id=1)
    state = AsyncMock()

    await router.callback_query.trigger(cast(CallbackQuery, callback_query), state=state)

    state.set_state.assert_awaited_once_with(ApodBirthdayForm.date)
    callback_query.message.answer.assert_awaited_once()
    deliver_media.execute.assert_not_awaited()
    greeting_sender.send_image.assert_not_awaited()


async def test_cosmic_birthday_delivers_immediately_when_already_set():
    stored_birthday = date(1990, 5, 20)
    get_or_create_user = AsyncMock()
    get_or_create_user.execute.return_value = User(chat_id=1, birthday=stored_birthday)
    deliver_media = AsyncMock()
    greeting_sender = AsyncMock()
    router = _router(deliver_media, get_or_create_user, AsyncMock(), greeting_sender)
    callback_query = FakeCallbackQuery(data="cosmic_birthday", chat_id=1)
    state = AsyncMock()

    await router.callback_query.trigger(cast(CallbackQuery, callback_query), state=state)

    state.set_state.assert_not_awaited()
    deliver_media.execute.assert_awaited_once_with(stored_birthday, 1)
    expected_title = build_cosmic_facts_lines(stored_birthday, date.today())[0]
    greeting_sender.send_image.assert_awaited_once()
    assert greeting_sender.send_image.await_args.args[0] == 1
    assert greeting_sender.send_image.await_args.kwargs["caption"] == expected_title


async def test_finish_birthday_saves_and_delivers_when_within_apod_bounds():
    set_birthday = AsyncMock()
    deliver_media = AsyncMock()
    greeting_sender = AsyncMock()
    router = _router(deliver_media, AsyncMock(), set_birthday, greeting_sender)
    message = FakeMessage(chat_id=1, text="2000-05-20")
    state = AsyncMock()

    await router.message.trigger(cast(Message, message), state=state, raw_state=ApodBirthdayForm.date.state)

    set_birthday.execute.assert_awaited_once_with(1, date(2000, 5, 20))
    state.clear.assert_awaited_once()
    deliver_media.execute.assert_awaited_once_with(date(2000, 5, 20), 1)
    expected_title = build_cosmic_facts_lines(date(2000, 5, 20), date.today())[0]
    greeting_sender.send_image.assert_awaited_once()
    assert greeting_sender.send_image.await_args.args[0] == 1
    assert greeting_sender.send_image.await_args.kwargs["caption"] == expected_title


async def test_finish_birthday_saves_but_explains_when_before_apod_lower_bound():
    set_birthday = AsyncMock()
    deliver_media = AsyncMock()
    greeting_sender = AsyncMock()
    router = _router(deliver_media, AsyncMock(), set_birthday, greeting_sender)
    message = FakeMessage(chat_id=1, text="1990-01-01")
    state = AsyncMock()

    await router.message.trigger(cast(Message, message), state=state, raw_state=ApodBirthdayForm.date.state)

    set_birthday.execute.assert_awaited_once_with(1, date(1990, 1, 1))
    deliver_media.execute.assert_not_awaited()
    message.answer.assert_awaited_once()
    assert "1995-06-16" in message.answer.await_args.args[0]
    greeting_sender.send_image.assert_not_awaited()


async def test_finish_birthday_rejects_invalid_format_without_saving():
    set_birthday = AsyncMock()
    deliver_media = AsyncMock()
    router = _router(deliver_media, AsyncMock(), set_birthday, AsyncMock())
    message = FakeMessage(chat_id=1, text="not-a-date")
    state = AsyncMock()

    await router.message.trigger(cast(Message, message), state=state, raw_state=ApodBirthdayForm.date.state)

    set_birthday.execute.assert_not_awaited()
    message.reply.assert_awaited_once()


async def test_finish_birthday_rejects_future_date_without_saving():
    set_birthday = AsyncMock()
    deliver_media = AsyncMock()
    router = _router(deliver_media, AsyncMock(), set_birthday, AsyncMock())
    message = FakeMessage(chat_id=1, text="2999-01-01")
    state = AsyncMock()

    await router.message.trigger(cast(Message, message), state=state, raw_state=ApodBirthdayForm.date.state)

    set_birthday.execute.assert_not_awaited()
    message.reply.assert_awaited_once()
