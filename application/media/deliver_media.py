from __future__ import annotations

from datetime import date as date_

from application.media.source_adapters import MediaSourceAdapter


class DeliverMediaForDate:
    """Один use-case на оба источника: кеш → NASA → admin-чат → пользователь."""

    def __init__(self, adapter: MediaSourceAdapter) -> None:
        self._adapter = adapter

    async def execute(self, day: date_, chat_id: int) -> None:
        cached = await self._adapter.get_cached(day)
        if cached is None:
            cached = await self._adapter.fetch_and_cache(day)
        await self._adapter.forward_cached(cached, chat_id)
