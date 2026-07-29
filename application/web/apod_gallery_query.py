from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date as date_
from datetime import timedelta
from typing import Protocol

from domain.media.apod_day_count import APOD_LAUNCH_DATE
from domain.media.entities import ApodWebEntry
from infrastructure.nasa.apod_client import ApodRangeItem


class ApodRangeClient(Protocol):
    async def fetch_for_range(self, start: date_, end: date_) -> Sequence[ApodRangeItem]: ...


class ApodWebCacheRepository(Protocol):
    async def get_by_dates(self, dates: Sequence[date_]) -> dict[date_, ApodWebEntry]: ...

    async def save_many(self, entries: Sequence[ApodWebEntry]) -> None: ...


@dataclass(frozen=True, slots=True)
class ApodGalleryItem:
    """JSON-DTO для тайла сетки — дата уже ISO-строкой, тот же паттерн, что
    у earth_event_date в HomepageDetail (docs/tz/TZ-web-apod.md)."""

    date: str
    title: str
    explanation: str
    copyright: str | None
    image_url: str
    hdurl: str | None


@dataclass(frozen=True, slots=True)
class ApodGalleryPage:
    items: Sequence[ApodGalleryItem]
    next_cursor: str | None


class GetApodGalleryPage:
    """Курсор — дата, не номер страницы: окно из page_size календарных дней
    перед `before` (или от `today`, если `before` не передан), назад до
    APOD_LAUNCH_DATE. Кеш в БД персистентный (см. docs/tz/TZ-web-apod.md) —
    NASA запрашивается только за даты, которых ещё нет в репозитории."""

    def __init__(self, apod_client: ApodRangeClient, repository: ApodWebCacheRepository, page_size: int) -> None:
        self._apod_client = apod_client
        self._repository = repository
        self._page_size = page_size

    async def execute(self, before: date_ | None, today: date_, page_size: int | None = None) -> ApodGalleryPage:
        window = self._window_dates(before, today, page_size or self._page_size)
        if not window:
            return ApodGalleryPage(items=(), next_cursor=None)

        cached = dict(await self._repository.get_by_dates(window))
        missing = [day for day in window if day not in cached]

        if missing:
            fetched = await self._apod_client.fetch_for_range(min(missing), max(missing))
            missing_set = set(missing)
            new_entries = [self._to_entry(item) for item in fetched if item.date in missing_set]
            if new_entries:
                await self._repository.save_many(new_entries)
            for entry in new_entries:
                cached[entry.date] = entry

        items = [self._to_item(cached[day]) for day in window if day in cached]
        oldest = window[-1]
        next_cursor = None if oldest == APOD_LAUNCH_DATE else oldest.isoformat()

        return ApodGalleryPage(items=items, next_cursor=next_cursor)

    @staticmethod
    def _window_dates(before: date_ | None, today: date_, page_size: int) -> list[date_]:
        end_date = before - timedelta(days=1) if before else today
        if end_date < APOD_LAUNCH_DATE:
            return []
        start_date = max(APOD_LAUNCH_DATE, end_date - timedelta(days=page_size - 1))
        span = (end_date - start_date).days
        return [end_date - timedelta(days=offset) for offset in range(span + 1)]

    @staticmethod
    def _to_entry(item: ApodRangeItem) -> ApodWebEntry:
        return ApodWebEntry(
            date=item.date,
            title=item.title,
            explanation=item.explanation,
            copyright=item.copyright,
            image_url=item.image_url,
            hdurl=item.hdurl,
        )

    @staticmethod
    def _to_item(entry: ApodWebEntry) -> ApodGalleryItem:
        return ApodGalleryItem(
            date=entry.date.isoformat(),
            title=entry.title,
            explanation=entry.explanation,
            copyright=entry.copyright,
            image_url=entry.image_url,
            hdurl=entry.hdurl,
        )
