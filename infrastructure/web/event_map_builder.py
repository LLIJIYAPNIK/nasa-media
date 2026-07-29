from __future__ import annotations

import aiohttp

from domain.digest.value_objects import EarthEventHighlight
from infrastructure.web.event_map import render_event_map
from infrastructure.web.event_map_cache import EventMapFileCache


class OsmEventMapBuilder:
    """Реализация `EventMapBuilder` (application/web/homepage_detail_query.py)
    поверх OSM-тайлов — см. docs/tz/TZ_karta_sobytiya_EONET.md."""

    def __init__(self, session: aiohttp.ClientSession, cache: EventMapFileCache) -> None:
        self._session = session
        self._cache = cache

    async def build(self, event: EarthEventHighlight) -> str | None:
        if not event.id or not event.geometry:
            return None
        latest_point = event.geometry[-1]
        cache_key = f"{event.id}_{latest_point.date.date().isoformat()}"

        if await self._cache.exists(cache_key):
            return cache_key

        image_bytes = await render_event_map(self._session, latest_point)
        if image_bytes is None:
            return None

        await self._cache.set(cache_key, image_bytes)
        return cache_key
