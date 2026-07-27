from __future__ import annotations

import asyncio
from datetime import date as date_

import aiohttp

from application.media.ports import SinglePhotoPayload, Translator
from domain.media.apod_caption import build_apod_caption
from domain.media.exceptions import MediaNotAvailable
from infrastructure.http import fetch_json

APOD_MAX_DESCRIPTION_LENGTH = 512


class ApodProvider:
    """Заменяет handlers/APOD/tools/await_date_data.py:current_date() — теперь
    на aiohttp (не блокирует event loop, в отличие от requests.get), через
    общую долгоживущую ClientSession вместо новой на каждый запрос."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str, base_url: str, translator: Translator) -> None:
        self._session = session
        self._api_key = api_key
        self._base_url = base_url
        self._translator = translator

    async def fetch(self, day: date_) -> SinglePhotoPayload:
        data = await fetch_json(self._session, self._base_url, {"date": day.isoformat(), "api_key": self._api_key})

        if data.get("media_type") != "image" or not (data.get("hdurl") or data.get("url")):
            raise MediaNotAvailable(f"NASA APOD за {day} недоступен")

        title, description = await asyncio.gather(
            self._translator.translate_to_ru(data["title"]),
            self._translator.translate_to_ru(data["explanation"][:APOD_MAX_DESCRIPTION_LENGTH]),
        )
        caption = build_apod_caption(day, title, description, data.get("copyright"))

        return SinglePhotoPayload(image_url=data.get("hdurl", data["url"]), caption=caption)
