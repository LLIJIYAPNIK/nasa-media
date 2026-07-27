from datetime import date
from unittest.mock import AsyncMock

import pytest

from domain.media.value_objects import MediaSourceKind
from presentation.telegram.routers.apod_router import build_apod_router
from tests.presentation.fake_telegram import FakeCallbackQuery


def _router(set_subscription: AsyncMock) -> object:
    return build_apod_router(
        deliver_media=AsyncMock(),
        deliver_media_range=AsyncMock(),
        set_subscription=set_subscription,
        get_or_create_user=AsyncMock(),
        apod_lower_bound=date(1995, 6, 16),
    )


@pytest.mark.parametrize(
    ("callback_data", "expected_value", "expected_text"),
    [
        ("apod_subscribe", True, "Вы подписались на рассылку APOD"),
        ("apod_unsubscribe", False, "Вы отписались от рассылки APOD"),
    ],
)
async def test_subscribe_callback_calls_use_case_with_correct_source_and_value(
    callback_data: str, expected_value: bool, expected_text: str
) -> None:
    set_subscription = AsyncMock()
    router = _router(set_subscription)
    callback_query = FakeCallbackQuery(data=callback_data, chat_id=555)

    await router.callback_query.trigger(callback_query)

    set_subscription.execute.assert_awaited_once_with(555, MediaSourceKind.APOD, expected_value)
    callback_query.message.delete.assert_awaited_once()
    callback_query.message.answer.assert_awaited_once_with(expected_text)
