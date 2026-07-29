from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date as date_
from typing import Any

import aiohttp

from application.media.ports import SinglePhotoPayload, Translator
from domain.media.apod_caption import build_apod_caption
from domain.media.exceptions import MediaNotAvailable
from infrastructure.http import fetch_json

APOD_MAX_DESCRIPTION_LENGTH = 512

# googletrans нестабилен (см. CLAUDE.md, «Вне текущего скоупа») — всплеск в
# 20-30 параллельных запросов на свежий диапазон дат сетки APOD реалистично
# в это упирается, поэтому перевод дат диапазона ограничен по параллельности.
_RANGE_TRANSLATION_CONCURRENCY = 5


@dataclass(frozen=True, slots=True)
class ApodRangeItem:
    """Один день APOD из fetch_for_range — SD (image_url) и HD (hdurl)
    хранятся раздельно, в отличие от ApodData (там уже схлопнуты в одно
    поле — осмысленно для единственной подписи Telegram/модалки главной, но
    не для сетки из десятков тайлов, см. docs/tz/TZ-web-apod.md)."""

    date: date_
    title: str
    explanation: str
    copyright: str | None
    image_url: str
    hdurl: str | None


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

        title, description = await self._translate_title_and_explanation(data["title"], data["explanation"])

        return ApodData(
            title=title,
            explanation=description,
            copyright=data.get("copyright"),
            image_url=data.get("hdurl", data["url"]),
        )

    async def fetch_for_range(self, start: date_, end: date_) -> Sequence[ApodRangeItem]:
        """Один запрос к NASA (start_date/end_date) вместо запроса на каждую
        дату диапазона — используется веб-сеткой APOD (docs/tz/TZ-web-apod.md),
        не ботом. Дни с видео или без картинки молча пропускаются, как и в
        fetch_raw, но не валят весь диапазон; дата, на которой упал перевод,
        тоже пропускается — частичная деградация вместо потери всей страницы."""
        data = await fetch_json(
            self._session,
            self._base_url,
            {"start_date": start.isoformat(), "end_date": end.isoformat(), "api_key": self._api_key},
        )

        candidates = [item for item in data if item.get("media_type") == "image" and item.get("url")]

        semaphore = asyncio.Semaphore(_RANGE_TRANSLATION_CONCURRENCY)
        items = await asyncio.gather(*(self._translate_range_item(semaphore, item) for item in candidates))
        return [item for item in items if item is not None]

    async def _translate_range_item(self, semaphore: asyncio.Semaphore, item: dict[str, Any]) -> ApodRangeItem | None:
        async with semaphore:
            try:
                title, explanation = await self._translate_title_and_explanation(item["title"], item["explanation"])
            except Exception:
                # Порванный перевод одной даты не должен ронять всю страницу
                # сетки (docs/tz/TZ-web-apod.md, «Откуда данные и кеш») — эта
                # дата просто не попадает в результат и не кешируется.
                return None

        return ApodRangeItem(
            date=date_.fromisoformat(item["date"]),
            title=title,
            explanation=explanation,
            copyright=item.get("copyright"),
            image_url=item["url"],
            hdurl=item.get("hdurl"),
        )

    async def _translate_title_and_explanation(self, title: str, explanation: str) -> tuple[str, str]:
        translated_title, translated_explanation = await asyncio.gather(
            self._translator.translate_to_ru(title),
            self._translator.translate_to_ru(explanation[:APOD_MAX_DESCRIPTION_LENGTH]),
        )
        return translated_title, translated_explanation


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
