from __future__ import annotations

from collections.abc import Callable
from datetime import date as date_
from typing import Protocol

from application.media.ports import AdminChatGateway, CachedMessageRef, EpicRepository, MediaProvider
from domain.media.entities import EpicDay
from domain.media.exceptions import MediaNotAvailable


class MediaSourceAdapter(Protocol):
    """Единый контракт для DeliverMediaForDate — специфика источника спрятана за ним."""

    async def get_cached(self, day: date_) -> CachedMessageRef | None: ...

    async def fetch_and_cache(self, day: date_) -> CachedMessageRef: ...

    async def forward_cached(self, ref: CachedMessageRef, chat_id: int) -> None: ...


class _HasMessageId(Protocol):
    @property
    def message_id(self) -> int: ...


class SimpleCacheRepository[EntryT: _HasMessageId](Protocol):
    """Источники с "плоским" кешем: одна запись на дату (или начало недели),
    без промежуточного состояния "дата известна, но контент ещё не собран"
    — APOD, дайджест, итоги недели. EPIC сюда не подходит — двухфазный кеш
    (см. EpicSourceAdapter ниже)."""

    async def get_by_date(self, day: date_) -> EntryT | None: ...

    async def save(self, entry: EntryT) -> None: ...


class GenericSourceAdapter[EntryT: _HasMessageId]:
    """Реализует MediaSourceAdapter для любого источника с SimpleCacheRepository
    — заменяет дословно повторявшиеся ApodSourceAdapter/DigestSourceAdapter/
    WeeklyHighlightsSourceAdapter (см. docs/tz/TZ-weekly-highlights.md,
    «Решения» — третий одинаковый класс подряд сделал дублирование
    неоспоримым). make_entry строит Entry конкретного источника — единственное,
    чем источники отличались друг от друга."""

    def __init__(
        self,
        provider: MediaProvider,
        repo: SimpleCacheRepository[EntryT],
        gateway: AdminChatGateway,
        make_entry: Callable[[date_, int], EntryT],
    ) -> None:
        self._provider = provider
        self._repo = repo
        self._gateway = gateway
        self._make_entry = make_entry

    async def get_cached(self, day: date_) -> CachedMessageRef | None:
        entry = await self._repo.get_by_date(day)
        return CachedMessageRef(message_id=entry.message_id) if entry else None

    async def fetch_and_cache(self, day: date_) -> CachedMessageRef:
        payload = await self._provider.fetch(day)
        ref = await self._gateway.publish(payload)
        await self._repo.save(self._make_entry(day, ref.message_id))
        return ref

    async def forward_cached(self, ref: CachedMessageRef, chat_id: int) -> None:
        await self._gateway.forward_single(ref.message_id, chat_id)


class EpicSourceAdapter:
    """EPIC не подходит под GenericSourceAdapter — get_cached различает "дата
    неизвестна NASA" (MediaNotAvailable) и "известна, но GIF ещё не собран"
    (None), а не просто "есть/нет записи"."""

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
