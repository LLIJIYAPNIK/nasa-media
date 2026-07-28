from __future__ import annotations

import time
from datetime import date as date_

from application.web.homepage_query import HomepageSnapshot

DEFAULT_TTL_SECONDS = 300


class SnapshotCache:
    """Простой in-memory TTL-кэш HomepageSnapshot по дате (см.
    docs/tz/TZ-web.md, «Кэширование NASA-запросов на веб-стороне»). Один
    слот, а не словарь по датам — снапшот всегда запрашивается только для
    «сегодня»."""

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._ttl_seconds = ttl_seconds
        self._entry: tuple[date_, float, HomepageSnapshot] | None = None

    def get(self, day: date_) -> HomepageSnapshot | None:
        if self._entry is None:
            return None
        cached_day, cached_at, snapshot = self._entry
        if cached_day != day or (time.monotonic() - cached_at) > self._ttl_seconds:
            return None
        return snapshot

    def set(self, day: date_, snapshot: HomepageSnapshot) -> None:
        self._entry = (day, time.monotonic(), snapshot)
