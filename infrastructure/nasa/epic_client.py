from __future__ import annotations

import asyncio
from datetime import date as date_

import aiohttp

from application.media.ports import AnimationPayload
from domain.media.exceptions import MediaNotAvailable
from infrastructure.files.gif_builder import build_gif
from infrastructure.http import fetch_bytes, fetch_json

# Фиксированный публичный путь архива NASA EPIC — как и в старом коде, не
# конфигурируется (в отличие от NASA_EPIC_URL, который указывает на API
# списка кадров за дату, см. epic_availability_client.py).
EPIC_ARCHIVE_BASE_URL = "https://api.nasa.gov/EPIC/archive/natural"


class EpicProvider:
    """Заменяет handlers/EPIC/tools/await_message.py. В отличие от старого
    кода (жёстко `for item in range(9)`, падает если кадров меньше девяти),
    качает ровно столько кадров, сколько вернул NASA API, и параллельно —
    вместо последовательной загрузки кадр за кадром."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str, api_base_url: str) -> None:
        self._session = session
        self._api_key = api_key
        self._api_base_url = api_base_url

    async def fetch(self, day: date_) -> AnimationPayload:
        frames_meta = await fetch_json(
            self._session, f"{self._api_base_url}/date/{day.isoformat()}", {"api_key": self._api_key}
        )
        if not frames_meta:
            raise MediaNotAvailable(f"NASA EPIC за {day} — нет кадров")

        images = await asyncio.gather(*(self._download_frame(day, frame) for frame in frames_meta))
        gif_bytes = await build_gif(images)
        return AnimationPayload(gif_bytes=gif_bytes)

    async def _download_frame(self, day: date_, frame_meta: dict) -> bytes:
        image_name = frame_meta["image"]
        url = f"{EPIC_ARCHIVE_BASE_URL}/{day:%Y}/{day:%m}/{day:%d}/png/{image_name}.png"
        return await fetch_bytes(self._session, url, {"api_key": self._api_key})
