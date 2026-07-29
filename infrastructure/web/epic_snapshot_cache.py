from __future__ import annotations

import time

from application.web.epic_page_query import EpicPageSnapshot

# Час, а не 300 сек, как у SnapshotCache главной страницы: у EpicPageSnapshotCache
# нет дешёвой проверки "не устарело ли" без сетевого запроса (SnapshotCache
# сравнивает date.today(), это бесплатно; здесь "последняя дата EPIC" сама
# по себе требует запроса к NASA) — см. docs/tz/TZ-web-epic.md, «Решения».
DEFAULT_TTL_SECONDS = 3600


class EpicPageSnapshotCache:
    """Простой in-memory TTL-кэш EpicPageSnapshot, один слот — по образцу
    infrastructure/web/snapshot_cache.py. Не обобщается с ним в общий класс
    (второй похожий случай, не третий — см. «Решения» в TZ-web-epic.md)."""

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._ttl_seconds = ttl_seconds
        self._entry: tuple[float, EpicPageSnapshot] | None = None

    def get(self) -> EpicPageSnapshot | None:
        if self._entry is None:
            return None
        cached_at, snapshot = self._entry
        if (time.monotonic() - cached_at) > self._ttl_seconds:
            return None
        return snapshot

    def set(self, snapshot: EpicPageSnapshot) -> None:
        self._entry = (time.monotonic(), snapshot)
