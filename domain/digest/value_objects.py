from __future__ import annotations

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
class EarthEventHighlight:
    title: str
    category: str
    event_date: datetime
