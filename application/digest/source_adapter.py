from __future__ import annotations

from datetime import date as date_

from application.digest.ports import DigestRepository
from application.media.ports import AdminChatGateway, CachedMessageRef, MediaProvider
from domain.digest.entities import DigestEntry


class DigestSourceAdapter:
    """Реализует MediaSourceAdapter (application/media/source_adapters.py) —
    та же тонкая форма, что и ApodSourceAdapter: вся сборка контента — в
    MediaProvider (см. DigestProvider), адаптер только кеширует/пересылает."""

    def __init__(self, provider: MediaProvider, repo: DigestRepository, gateway: AdminChatGateway) -> None:
        self._provider = provider
        self._repo = repo
        self._gateway = gateway

    async def get_cached(self, day: date_) -> CachedMessageRef | None:
        entry = await self._repo.get_by_date(day)
        return CachedMessageRef(message_id=entry.message_id) if entry else None

    async def fetch_and_cache(self, day: date_) -> CachedMessageRef:
        payload = await self._provider.fetch(day)
        ref = await self._gateway.publish(payload)
        await self._repo.save(DigestEntry(date=day, message_id=ref.message_id))
        return ref

    async def forward_cached(self, ref: CachedMessageRef, chat_id: int) -> None:
        await self._gateway.forward_single(ref.message_id, chat_id)
