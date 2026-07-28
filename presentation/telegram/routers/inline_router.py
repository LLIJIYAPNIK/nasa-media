from __future__ import annotations

from datetime import date
from typing import Protocol

from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultCachedGif,
    InlineQueryResultCachedPhoto,
    InlineQueryResultUnion,
    InputTextMessageContent,
)

from application.digest.ports import DigestRepository, WeeklyHighlightsRepository
from application.media.ports import ApodRepository, EpicRepository
from domain.digest.week import week_start

# Telegram кеширует ответ на своей стороне: контент, который раздаёт inline-
# режим, обновляется не чаще раза в сутки/неделю (см. docs/tz/TZ-inline-mode.md).
INLINE_CACHE_TIME_SECONDS = 300


class _HasFileId(Protocol):
    @property
    def file_id(self) -> str | None: ...


def _not_ready_result() -> InlineQueryResultArticle:
    return InlineQueryResultArticle(
        id="not_ready",
        title="Ещё не готово",
        description="Загляните в бота напрямую",
        input_message_content=InputTextMessageContent(
            message_text="Этот контент ещё не готов — загляните в бота напрямую."
        ),
    )


def _no_preview_result() -> InlineQueryResultArticle:
    """Кешированная запись есть, но без file_id (сохранена до этой фичи,
    см. TZ-inline-mode.md) — не идеальный, но рабочий fallback вместо отказа."""
    return InlineQueryResultArticle(
        id="no_preview",
        title="Готово — открой бота",
        description="Мгновенный предпросмотр недоступен для этой записи",
        input_message_content=InputTextMessageContent(
            message_text="Контент уже готов, но мгновенный предпросмотр для него недоступен — загляните в бота."
        ),
    )


def _build_results(entry: _HasFileId | None, *, result_id: str, is_gif: bool) -> list[InlineQueryResultUnion]:
    if entry is None:
        return [_not_ready_result()]
    if entry.file_id is None:
        return [_no_preview_result()]
    if is_gif:
        return [InlineQueryResultCachedGif(id=result_id, gif_file_id=entry.file_id)]
    return [InlineQueryResultCachedPhoto(id=result_id, photo_file_id=entry.file_id)]


def build_inline_router(
    apod_repo: ApodRepository,
    epic_repo: EpicRepository,
    digest_repo: DigestRepository,
    weekly_repo: WeeklyHighlightsRepository,
) -> Router:
    """Раздаёт уже закешированный контент (APOD/EPIC/дайджест/итоги недели)
    прямо в любом чужом чате через `@bot_username запрос`, без захода в бота.
    Дата не парсится — только "сегодня"/"эта неделя" (см. TZ-inline-mode.md).
    Требует включения inline-режима для бота через @BotFather (/setinline) —
    организационный шаг, не код."""
    router = Router()

    @router.inline_query()
    async def handle_inline_query(inline_query: InlineQuery) -> None:
        query = inline_query.query.strip().lower()
        today = date.today()

        if query == "epic":
            epic_day = await epic_repo.get_by_date(today)
            entry = epic_day if epic_day and epic_day.is_cached else None
            results = _build_results(entry, result_id="epic", is_gif=True)
        elif query in ("digest", "сводка"):
            digest_entry = await digest_repo.get_by_date(today)
            results = _build_results(digest_entry, result_id="digest", is_gif=False)
        elif query in ("неделя", "week"):
            weekly_entry = await weekly_repo.get_by_date(week_start(today))
            results = _build_results(weekly_entry, result_id="weekly", is_gif=False)
        else:
            apod_entry = await apod_repo.get_by_date(today)
            results = _build_results(apod_entry, result_id="apod", is_gif=False)

        await inline_query.answer(results=results, cache_time=INLINE_CACHE_TIME_SECONDS)

    return router
