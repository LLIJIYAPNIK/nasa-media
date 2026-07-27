from unittest.mock import AsyncMock

import pytest

from domain.media.value_objects import MediaSourceKind
from presentation.telegram.routers.epic_router import build_epic_router
from tests.presentation.fake_telegram import FakeCallbackQuery


def _router(set_subscription: AsyncMock) -> object:
    return build_epic_router(
        deliver_media=AsyncMock(),
        set_subscription=set_subscription,
        get_or_create_user=AsyncMock(),
    )


@pytest.mark.parametrize(
    ("callback_data", "expected_value", "expected_text"),
    [
        ("epic_subscribe", True, "Вы подписались на рассылку EPIC"),
        ("epic_unsubscribe", False, "Вы отписались от рассылки EPIC"),
    ],
)
async def test_subscribe_callback_calls_use_case_with_correct_source_and_value(
    callback_data: str, expected_value: bool, expected_text: str
) -> None:
    set_subscription = AsyncMock()
    router = _router(set_subscription)
    callback_query = FakeCallbackQuery(data=callback_data, chat_id=777)

    await router.callback_query.trigger(callback_query)

    set_subscription.execute.assert_awaited_once_with(777, MediaSourceKind.EPIC, expected_value)
    callback_query.message.delete.assert_awaited_once()
    callback_query.message.answer.assert_awaited_once_with(expected_text)
