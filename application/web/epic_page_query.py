from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date as date_
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EpicPageSnapshot:
    """Всё, что нужно шаблону /epic — см. docs/tz/TZ-web-epic.md. Ни
    подписи, ни текста на странице нет (прямой запрос «ничего лишнего»);
    frame_date хранится только ради ключа кэша/тестируемости, в шаблоне не
    отображается."""

    frame_date: date_
    centroid_lat: float
    centroid_lon: float
    texture_url: str


@dataclass(frozen=True, slots=True)
class EpicTexture:
    cache_key: str
    centroid_lat: float
    centroid_lon: float


class EpicAvailability(Protocol):
    async def fetch_known_dates(self) -> Sequence[date_]: ...


class EpicTextureBuilder(Protocol):
    async def build(self, day: date_) -> EpicTexture | None: ...


class GetEpicPageSnapshot:
    """Собирает снапшот для /epic напрямую из NASA — не через
    application/media/admin-чат-кеш (тот про Telegram), а по тому же
    принципу, что и GetHomepageSnapshot (см. docs/tz/TZ-web.md)."""

    def __init__(self, availability: EpicAvailability, texture_builder: EpicTextureBuilder) -> None:
        self._availability = availability
        self._texture_builder = texture_builder

    async def execute(self) -> EpicPageSnapshot | None:
        known_dates = await self._availability.fetch_known_dates()
        if not known_dates:
            return None

        latest_day = max(known_dates)
        texture = await self._texture_builder.build(latest_day)
        if texture is None:
            return None

        return EpicPageSnapshot(
            frame_date=latest_day,
            centroid_lat=texture.centroid_lat,
            centroid_lon=texture.centroid_lon,
            texture_url=f"/api/epic/textures/{texture.cache_key}.jpg",
        )
