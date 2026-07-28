from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date as date_

import aiohttp

from application.media.ports import SinglePhotoPayload, Translator
from domain.media.apod_caption import build_apod_caption
from domain.media.exceptions import MediaNotAvailable
from infrastructure.http import fetch_json

APOD_MAX_DESCRIPTION_LENGTH = 512


@dataclass(frozen=True, slots=True)
class ApodData:
    """APOD за дату, уже переведённый на русский, без сборки в Telegram-подпись
    — используется и ApodProvider (бот), и application/web (модалка карточки
    APOD на главной странице), см. docs/tz/TZ-web.md."""

    title: str
    explanation: str
    copyright: str | None
    image_url: str


class ApodClient:
    """Заменяет handlers/APOD/tools/await_date_data.py:current_date() — теперь
    на aiohttp (не блокирует event loop, в отличие от requests.get), через
    общую долгоживущую ClientSession вместо новой на каждый запрос."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str, base_url: str, translator: Translator) -> None:
        self._session = session
        self._api_key = api_key
        self._base_url = base_url
        self._translator = translator

    async def fetch_raw(self, day: date_) -> ApodData:
        data = await fetch_json(self._session, self._base_url, {"date": day.isoformat(), "api_key": self._api_key})

        if data.get("media_type") != "image" or not (data.get("hdurl") or data.get("url")):
            raise MediaNotAvailable(f"NASA APOD за {day} недоступен")

        title, description = await asyncio.gather(
            self._translator.translate_to_ru(data["title"]),
            self._translator.translate_to_ru(data["explanation"][:APOD_MAX_DESCRIPTION_LENGTH]),
        )

        return ApodData(
            title=title,
            explanation=description,
            copyright=data.get("copyright"),
            image_url=data.get("hdurl", data["url"]),
        )


class ApodProvider:
    """Тонкая обёртка над ApodClient для бота: добавляет сборку Telegram-подписи
    поверх сырых переведённых данных. application/web вызывает ApodClient.fetch_raw
    напрямую, минуя caption (см. docs/tz/TZ-web.md, «Выбор стека»)."""

    def __init__(self, apod_client: ApodClient) -> None:
        self._apod_client = apod_client

    async def fetch(self, day: date_) -> SinglePhotoPayload:
        data = await self._apod_client.fetch_raw(day)
        caption = build_apod_caption(day, data.title, data.explanation, data.copyright)
        return SinglePhotoPayload(image_url=data.image_url, caption=caption)
