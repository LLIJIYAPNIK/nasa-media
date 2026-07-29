from __future__ import annotations

import asyncio
import re
from pathlib import Path

DEFAULT_CACHE_DIR = Path("var/cache/epic-textures")

# Ключ всегда ISO-дата (YYYY-MM-DD) — та же защита пути, что и в
# event_map_cache.py, второй похожий файловый кеш подряд (см. «Решения» в
# docs/tz/TZ-web-epic.md — не обобщаю с ним в общий класс до третьего
# похожего случая).
_SAFE_CACHE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


class EpicTextureFileCache:
    """Дисковый кеш байт JPEG-текстуры EPIC для /epic — по дате (см.
    docs/tz/TZ-web-epic.md, «Решения»). Файловый, не Redis/БД — по тому же
    обоснованию, что и у EventMapFileCache: картинок мало, лишняя
    инфраструктура не оправдана."""

    def __init__(self, directory: Path = DEFAULT_CACHE_DIR) -> None:
        self._directory = directory

    def _path_for(self, cache_key: str) -> Path | None:
        if not _SAFE_CACHE_KEY.match(cache_key):
            return None
        return self._directory / f"{cache_key}.jpg"

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
