from __future__ import annotations

from datetime import date as date_
from typing import Protocol

from application.media.ports import AdminChatGateway, ApodRepository, CachedMessageRef, EpicRepository, MediaProvider
from domain.media.entities import ApodEntry, EpicDay
from domain.media.exceptions import MediaNotAvailable


class MediaSourceAdapter(Protocol):
    """Единый контракт для DeliverMediaForDate — специфика APOD/EPIC спрятана за ним."""

    async def get_cached(self, day: date_) -> CachedMessageRef | None: ...

    async def fetch_and_cache(self, day: date_) -> CachedMessageRef: ...

    async def forward_cached(self, ref: CachedMessageRef, chat_id: int) -> None: ...


class ApodSourceAdapter:
    def __init__(self, provider: MediaProvider, repo: ApodRepository, gateway: AdminChatGateway) -> None:
        self._provider = provider
        self._repo = repo
        self._gateway = gateway

    async def get_cached(self, day: date_) -> CachedMessageRef | None:
        entry = await self._repo.get_by_date(day)
        return CachedMessageRef(message_id=entry.message_id) if entry else None

    async def fetch_and_cache(self, day: date_) -> CachedMessageRef:
        payload = await self._provider.fetch(day)
        ref = await self._gateway.publish(payload)
        await self._repo.save(ApodEntry(date=day, message_id=ref.message_id))
        return ref

    async def forward_cached(self, ref: CachedMessageRef, chat_id: int) -> None:
        await self._gateway.forward_single(ref.message_id, chat_id)


class EpicSourceAdapter:
    def __init__(self, provider: MediaProvider, repo: EpicRepository, gateway: AdminChatGateway) -> None:
        self._provider = provider
        self._repo = repo
        self._gateway = gateway

    async def get_cached(self, day: date_) -> CachedMessageRef | None:
        epic_day = await self._repo.get_by_date(day)
        if epic_day is None:
            raise MediaNotAvailable(f"NASA EPIC за {day} недоступен")
        if epic_day.is_cached:
            assert epic_day.gif_message_id is not None
            return CachedMessageRef(message_id=epic_day.gif_message_id)
        return None

    async def fetch_and_cache(self, day: date_) -> CachedMessageRef:
        payload = await self._provider.fetch(day)
        ref = await self._gateway.publish(payload)
        await self._repo.save(EpicDay(date=day, gif_message_id=ref.message_id))
        return ref

    async def forward_cached(self, ref: CachedMessageRef, chat_id: int) -> None:
        await self._gateway.forward_single(ref.message_id, chat_id)
