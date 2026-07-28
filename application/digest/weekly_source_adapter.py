from __future__ import annotations

from datetime import date as date_

from application.digest.ports import WeeklyHighlightsRepository
from application.media.ports import AdminChatGateway, CachedMessageRef, MediaProvider
from domain.digest.entities import WeeklyHighlightEntry


class WeeklyHighlightsSourceAdapter:
    """Реализует MediaSourceAdapter — дословно та же форма, что и
    DigestSourceAdapter (get_cached/fetch_and_cache/forward_cached), только
    сущность и репозиторий свои. Осознанное дублирование — третий одинаковый
    адаптер подряд (после ApodSourceAdapter/EpicSourceAdapter из
    TZ-gif-timelapse.md), схлопывание — обязательный рефакторинг-проход
    после этой фичи (см. docs/tz/TZ-weekly-highlights.md, «Решения»)."""

    def __init__(self, provider: MediaProvider, repo: WeeklyHighlightsRepository, gateway: AdminChatGateway) -> None:
        self._provider = provider
        self._repo = repo
        self._gateway = gateway

    async def get_cached(self, week_start_date: date_) -> CachedMessageRef | None:
        entry = await self._repo.get_by_date(week_start_date)
        return CachedMessageRef(message_id=entry.message_id) if entry else None

    async def fetch_and_cache(self, week_start_date: date_) -> CachedMessageRef:
        payload = await self._provider.fetch(week_start_date)
        ref = await self._gateway.publish(payload)
        await self._repo.save(WeeklyHighlightEntry(week_start_date=week_start_date, message_id=ref.message_id))
        return ref

    async def forward_cached(self, ref: CachedMessageRef, chat_id: int) -> None:
        await self._gateway.forward_single(ref.message_id, chat_id)
