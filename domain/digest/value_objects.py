from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SpaceWeatherHighlight:
    message_type: str
    issued_at: datetime


@dataclass(frozen=True, slots=True)
class AsteroidHighlight:
    name: str
    diameter_min_m: float
    diameter_max_m: float
    miss_distance_km: float
    miss_distance_lunar: float
    is_hazardous: bool
    miss_distance_au: float
    miss_distance_miles: float
    velocity_km_s: float
    velocity_km_h: float
    close_approach_time: datetime
    jpl_url: str
    is_sentry_object: bool


@dataclass(frozen=True, slots=True)
class EventGeometryPoint:
    """Одна точка `geometry` EONET-события. У EONET v3 `magnitudeValue`/
    `magnitudeUnit`/`magnitudeDescription` живут на самой точке, не на
    событии целиком (проверено живым запросом, см. docs/tz/TZ_karta_sobytiya_EONET.md)
    — «текущая» магнитуда события берётся с последней по дате точки."""

    lon: float
    lat: float
    date: datetime
    magnitude_value: float | None = None
    magnitude_unit: str | None = None
    magnitude_description: str | None = None


@dataclass(frozen=True, slots=True)
class EventSource:
    """EONET-источник — `id` (сеть/агентство, например "IRWIN", "InciWeb"),
    не `title` — у API нет отдельного поля названия источника."""

    label: str
    url: str


@dataclass(frozen=True, slots=True)
class EarthEventHighlight:
    title: str
    category: str
    event_date: datetime
    id: str = ""
    categories: Sequence[str] = ()
    description: str | None = None
    closed_at: datetime | None = None
    link: str = ""
    sources: Sequence[EventSource] = ()
    geometry: Sequence[EventGeometryPoint] = ()
    magnitude_value: float | None = None
    magnitude_unit: str | None = None
    magnitude_description: str | None = None
