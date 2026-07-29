from __future__ import annotations

import asyncio
import re
from pathlib import Path

DEFAULT_CACHE_DIR = Path("var/cache/event-maps")

# Собственные ключи всегда `{event.id}_{YYYY-MM-DD}` (см. event_map_builder.py),
# но ключ приходит в маршрут напрямую от клиента — валидация нужна как
# граница безопасности пути, а не только для собственной генерации.
_SAFE_CACHE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


class EventMapFileCache:
    """Дисковый кеш сгенерированных карт событий — по `event.id` (+ дате
    последней точки геометрии, зашита в сам ключ), см.
    docs/tz/TZ_karta_sobytiya_EONET.md, «Где кешировать». Файловый, не
    Redis/БД — картинок мало и по объёму, живут произвольно долго, лишняя
    инфраструктура не оправдана (см. принцип «не усложнять раньше времени»
    в CLAUDE.md)."""

    def __init__(self, directory: Path = DEFAULT_CACHE_DIR) -> None:
        self._directory = directory

    def _path_for(self, cache_key: str) -> Path | None:
        if not _SAFE_CACHE_KEY.match(cache_key):
            return None
        return self._directory / f"{cache_key}.png"

    async def get(self, cache_key: str) -> bytes | None:
        path = self._path_for(cache_key)
        if path is None:
            return None
        return await asyncio.to_thread(self._read, path)

    @staticmethod
    def _read(path: Path) -> bytes | None:
        if not path.exists():
            return None
        return path.read_bytes()

    async def exists(self, cache_key: str) -> bool:
        path = self._path_for(cache_key)
        if path is None:
            return False
        return await asyncio.to_thread(path.exists)

    async def set(self, cache_key: str, data: bytes) -> None:
        path = self._path_for(cache_key)
        if path is None:
            raise ValueError(f"Небезопасный cache_key: {cache_key!r}")
        await asyncio.to_thread(self._write, path, data)

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
