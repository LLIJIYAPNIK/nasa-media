from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_
from typing import Protocol

from domain.digest.entities import DigestEntry
from domain.digest.value_objects import AsteroidHighlight, EarthEventHighlight, SpaceWeatherHighlight


class SpaceWeatherClient(Protocol):
    async def fetch_for_day(self, day: date_) -> Sequence[SpaceWeatherHighlight]: ...


class NearEarthObjectClient(Protocol):
    async def fetch_for_day(self, day: date_) -> Sequence[AsteroidHighlight]: ...


class NaturalEventClient(Protocol):
    """Не принимает `day` — EONET не поддерживает фильтр по дате на уровне
    API, см. docs/tz/TZ-daily-digest.md."""

    async def fetch_recent(self) -> Sequence[EarthEventHighlight]: ...


class DigestRepository(Protocol):
    async def get_by_date(self, day: date_) -> DigestEntry | None: ...

    async def save(self, entry: DigestEntry) -> None: ...
