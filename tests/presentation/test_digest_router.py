from datetime import date
from typing import cast
from unittest.mock import AsyncMock

import pytest
from aiogram import Router
from aiogram.types import CallbackQuery

from domain.media.value_objects import MediaSourceKind
from presentation.telegram.routers.digest_router import build_digest_router
from tests.presentation.fake_telegram import FakeCallbackQuery


def _router(deliver_digest: AsyncMock, set_subscription: AsyncMock) -> Router:
    return build_digest_router(
        deliver_digest=deliver_digest,
        set_subscription=set_subscription,
        get_or_create_user=AsyncMock(),
    )


@pytest.mark.parametrize(
    ("callback_data", "expected_value", "expected_text"),
    [
        ("digest_subscribe", True, "Вы подписались на рассылку сводки"),
        ("digest_unsubscribe", False, "Вы отписались от рассылки сводки"),
    ],
)
async def test_subscribe_callback_calls_use_case_with_correct_source_and_value(
    callback_data: str, expected_value: bool, expected_text: str
) -> None:
    set_subscription = AsyncMock()
    router = _router(AsyncMock(), set_subscription)
    callback_query = FakeCallbackQuery(data=callback_data, chat_id=777)

    await router.callback_query.trigger(cast(CallbackQuery, callback_query))

    set_subscription.execute.assert_awaited_once_with(777, MediaSourceKind.DIGEST, expected_value)
    callback_query.message.delete.assert_awaited_once()
    callback_query.message.answer.assert_awaited_once_with(expected_text)


async def test_digest_show_delivers_todays_digest():
    deliver_digest = AsyncMock()
    router = _router(deliver_digest, AsyncMock())
    callback_query = FakeCallbackQuery(data="digest_show", chat_id=555)

    await router.callback_query.trigger(cast(CallbackQuery, callback_query))

    deliver_digest.execute.assert_awaited_once_with(date.today(), 555)
