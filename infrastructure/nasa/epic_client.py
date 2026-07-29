from __future__ import annotations

import asyncio
from datetime import date as date_

import aiohttp

from application.media.ports import AnimationPayload
from domain.media.exceptions import MediaNotAvailable
from infrastructure.files.gif_builder import build_gif
from infrastructure.nasa.epic_frames import EPIC_ARCHIVE_BASE_URL, fetch_day_frames, fetch_frame_bytes

__all__ = ["EPIC_ARCHIVE_BASE_URL", "EpicProvider"]


class EpicProvider:
    """Заменяет handlers/EPIC/tools/await_message.py. В отличие от старого
    кода (жёстко `for item in range(9)`, падает если кадров меньше девяти),
    качает ровно столько кадров, сколько вернул NASA API, и параллельно —
    вместо последовательной загрузки кадр за кадром.

    Скачивание списка кадров и байт конкретного кадра — в
    infrastructure/nasa/epic_frames.py, общее с веб-страницей /epic (см.
    docs/tz/TZ-web-epic.md), чтобы не дублировать разбор ответа NASA."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str, api_base_url: str) -> None:
        self._session = session
        self._api_key = api_key
        self._api_base_url = api_base_url

    async def fetch(self, day: date_) -> AnimationPayload:
        frames = await fetch_day_frames(self._session, self._api_key, self._api_base_url, day)
        if not frames:
            raise MediaNotAvailable(f"NASA EPIC за {day} — нет кадров")

        images = await asyncio.gather(
            *(fetch_frame_bytes(self._session, self._api_key, day, frame.image) for frame in frames)
        )
        gif_bytes = await build_gif(images)
        return AnimationPayload(gif_bytes=gif_bytes)
