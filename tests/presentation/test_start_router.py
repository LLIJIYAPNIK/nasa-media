from unittest.mock import AsyncMock

from presentation.telegram.routers.start_router import WELCOME_TEXT, build_start_router
from tests.presentation.fake_telegram import FakeCallbackQuery


async def test_back_to_start_shows_welcome_message_and_clears_state():
    router = build_start_router(get_or_create_user=AsyncMock())
    callback_query = FakeCallbackQuery(data="back_to_start", chat_id=1)
    state = AsyncMock()

    await router.callback_query.trigger(callback_query, state=state)

    callback_query.message.delete.assert_awaited_once()
    state.clear.assert_awaited_once()
    callback_query.message.answer.assert_awaited_once()
    assert callback_query.message.answer.await_args.args[0] == WELCOME_TEXT
