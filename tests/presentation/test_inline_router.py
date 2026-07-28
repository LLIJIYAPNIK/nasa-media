from collections.abc import Mapping
from datetime import date
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultCachedGif,
    InlineQueryResultCachedPhoto,
)

from domain.digest.entities import DigestEntry, WeeklyHighlightEntry
from domain.digest.week import week_start
from domain.media.entities import ApodEntry, EpicDay
from presentation.telegram.routers.inline_router import build_inline_router
from tests.presentation.fake_telegram import FakeInlineQuery

TODAY = date.today()


def _router(apod_repo=None, epic_repo=None, digest_repo=None, weekly_repo=None) -> Router:
    return build_inline_router(
        apod_repo=apod_repo or AsyncMock(),
        epic_repo=epic_repo or AsyncMock(),
        digest_repo=digest_repo or AsyncMock(),
        weekly_repo=weekly_repo or AsyncMock(),
    )


def _answer_kwargs(inline_query: FakeInlineQuery) -> Mapping[str, Any]:
    assert inline_query.answer.await_args is not None
    return inline_query.answer.await_args.kwargs


async def _trigger(router: Router, query: str) -> FakeInlineQuery:
    inline_query = FakeInlineQuery(query=query)
    await router.inline_query.trigger(cast(InlineQuery, inline_query))
    return inline_query


@pytest.mark.parametrize("query", ["apod", ""])
async def test_apod_query_returns_cached_photo_when_file_id_present(query: str):
    apod_repo = AsyncMock()
    apod_repo.get_by_date.return_value = ApodEntry(date=TODAY, message_id=1, file_id="apod-file")
    router = _router(apod_repo=apod_repo)

    inline_query = await _trigger(router, query)

    apod_repo.get_by_date.assert_awaited_once_with(TODAY)
    results = _answer_kwargs(inline_query)["results"]
    assert len(results) == 1
    assert isinstance(results[0], InlineQueryResultCachedPhoto)
    assert results[0].photo_file_id == "apod-file"


async def test_apod_query_returns_placeholder_when_no_cache_entry():
    apod_repo = AsyncMock()
    apod_repo.get_by_date.return_value = None
    router = _router(apod_repo=apod_repo)

    inline_query = await _trigger(router, "apod")

    results = _answer_kwargs(inline_query)["results"]
    assert len(results) == 1
    assert isinstance(results[0], InlineQueryResultArticle)
    assert results[0].id == "not_ready"


async def test_apod_query_returns_text_fallback_when_entry_has_no_file_id():
    apod_repo = AsyncMock()
    apod_repo.get_by_date.return_value = ApodEntry(date=TODAY, message_id=1, file_id=None)
    router = _router(apod_repo=apod_repo)

    inline_query = await _trigger(router, "apod")

    results = _answer_kwargs(inline_query)["results"]
    assert len(results) == 1
    assert isinstance(results[0], InlineQueryResultArticle)
    assert results[0].id == "no_preview"


async def test_epic_query_returns_cached_gif_when_file_id_present():
    epic_repo = AsyncMock()
    epic_repo.get_by_date.return_value = EpicDay(date=TODAY, gif_message_id=2, file_id="epic-gif-file")
    router = _router(epic_repo=epic_repo)

    inline_query = await _trigger(router, "epic")

    results = _answer_kwargs(inline_query)["results"]
    assert len(results) == 1
    assert isinstance(results[0], InlineQueryResultCachedGif)
    assert results[0].gif_file_id == "epic-gif-file"


async def test_epic_query_returns_placeholder_when_known_but_not_yet_cached():
    epic_repo = AsyncMock()
    epic_repo.get_by_date.return_value = EpicDay(date=TODAY, gif_message_id=None)
    router = _router(epic_repo=epic_repo)

    inline_query = await _trigger(router, "epic")

    results = _answer_kwargs(inline_query)["results"]
    assert isinstance(results[0], InlineQueryResultArticle)
    assert results[0].id == "not_ready"


@pytest.mark.parametrize("query", ["digest", "сводка"])
async def test_digest_query_returns_cached_photo(query: str):
    digest_repo = AsyncMock()
    digest_repo.get_by_date.return_value = DigestEntry(date=TODAY, message_id=3, file_id="digest-file")
    router = _router(digest_repo=digest_repo)

    inline_query = await _trigger(router, query)

    digest_repo.get_by_date.assert_awaited_once_with(TODAY)
    results = _answer_kwargs(inline_query)["results"]
    assert isinstance(results[0], InlineQueryResultCachedPhoto)
    assert results[0].photo_file_id == "digest-file"


@pytest.mark.parametrize("query", ["неделя", "week"])
async def test_weekly_query_returns_cached_photo_for_current_week(query: str):
    weekly_repo = AsyncMock()
    weekly_repo.get_by_date.return_value = WeeklyHighlightEntry(
        week_start_date=week_start(TODAY), message_id=4, file_id="weekly-file"
    )
    router = _router(weekly_repo=weekly_repo)

    inline_query = await _trigger(router, query)

    weekly_repo.get_by_date.assert_awaited_once_with(week_start(TODAY))
    results = _answer_kwargs(inline_query)["results"]
    assert isinstance(results[0], InlineQueryResultCachedPhoto)
    assert results[0].photo_file_id == "weekly-file"


async def test_answer_uses_the_configured_cache_time():
    apod_repo = AsyncMock()
    apod_repo.get_by_date.return_value = None
    router = _router(apod_repo=apod_repo)

    inline_query = await _trigger(router, "apod")

    assert _answer_kwargs(inline_query)["cache_time"] == 300
