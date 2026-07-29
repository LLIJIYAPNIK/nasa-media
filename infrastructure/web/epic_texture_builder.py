from __future__ import annotations

import asyncio
from datetime import date as date_
from io import BytesIO

import aiohttp
from PIL import Image

from application.web.epic_page_query import EpicTexture
from infrastructure.nasa.epic_frames import fetch_day_frames, fetch_frame_bytes
from infrastructure.web.epic_texture_cache import EpicTextureFileCache

# Полноэкранный "hero"-визуал — крупнее, чем кадр GIF в Telegram (640×640,
# см. TZ-gif-timelapse.md), но без веса оригинала NASA (обычно ~2048×2048
# PNG). JPEG, не PNG — фону/альфа-каналу негде взяться, шейдер сам решает,
# какое полушарие видимое (см. docs/tz/TZ-web-epic.md, «Решения»).
TEXTURE_MAX_DIMENSIONS = (1024, 1024)
TEXTURE_JPEG_QUALITY = 88


def _resize_to_jpeg(image_bytes: bytes, max_dimensions: tuple[int, int], quality: int) -> bytes:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image.thumbnail(max_dimensions)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


class NasaEpicTextureBuilder:
    """Реализация `EpicTextureBuilder` (application/web/epic_page_query.py)
    — см. docs/tz/TZ-web-epic.md. Средний кадр дня как декаль на сфере;
    метаданные (для centroid) запрашиваются каждый раз (дешёвый JSON), а
    байты кадра — только при кеш-промахе (дорогая часть)."""

    def __init__(
        self, session: aiohttp.ClientSession, api_key: str, api_base_url: str, cache: EpicTextureFileCache
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._api_base_url = api_base_url
        self._cache = cache

    async def build(self, day: date_) -> EpicTexture | None:
        frames = await fetch_day_frames(self._session, self._api_key, self._api_base_url, day)
        if not frames:
            return None

        frame = frames[len(frames) // 2]
        cache_key = day.isoformat()

        if not await self._cache.exists(cache_key):
            raw_bytes = await fetch_frame_bytes(self._session, self._api_key, day, frame.image)
            # Ресайз — блокирующий Pillow-вызов, уводим в поток (тот же
            # принцип, что и в infrastructure/files/temp_file.py).
            texture_bytes = await asyncio.to_thread(
                _resize_to_jpeg, raw_bytes, TEXTURE_MAX_DIMENSIONS, TEXTURE_JPEG_QUALITY
            )
            await self._cache.set(cache_key, texture_bytes)

        return EpicTexture(cache_key=cache_key, centroid_lat=frame.centroid_lat, centroid_lon=frame.centroid_lon)
