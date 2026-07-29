from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from datetime import date as date_

import aiohttp

from domain.digest.value_objects import AsteroidHighlight
from infrastructure.http import fetch_json


class NeoWsClient:
    """Near Earth Objects за конкретный день. NASA отдаёт дистанции строкой —
    приводим к float на границе инфраструктуры, домен работает с числами."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str, base_url: str) -> None:
        self._session = session
        self._api_key = api_key
        self._base_url = base_url

    async def fetch_for_day(self, day: date_) -> Sequence[AsteroidHighlight]:
        return await self.fetch_for_range(day, day)

    async def fetch_for_range(self, start: date_, end: date_) -> Sequence[AsteroidHighlight]:
        """NeoWs принимает произвольный диапазон start_date/end_date за один
        запрос (см. docs/tz/TZ-weekly-highlights.md) — fetch_for_day лишь
        частный случай range из одного дня, не отдельная HTTP-логика."""
        data = await fetch_json(
            self._session,
            self._base_url,
            {"start_date": start.isoformat(), "end_date": end.isoformat(), "api_key": self._api_key},
        )

        highlights = []
        for objects in data.get("near_earth_objects", {}).values():
            for obj in objects:
                diameter = obj["estimated_diameter"]["meters"]
                close_approach = obj["close_approach_data"][0]
                miss_distance = close_approach["miss_distance"]
                velocity = close_approach["relative_velocity"]
                highlights.append(
                    AsteroidHighlight(
                        name=obj["name"],
                        diameter_min_m=float(diameter["estimated_diameter_min"]),
                        diameter_max_m=float(diameter["estimated_diameter_max"]),
                        miss_distance_km=float(miss_distance["kilometers"]),
                        miss_distance_lunar=float(miss_distance["lunar"]),
                        is_hazardous=bool(obj["is_potentially_hazardous_asteroid"]),
                        miss_distance_au=float(miss_distance["astronomical"]),
                        miss_distance_miles=float(miss_distance["miles"]),
                        velocity_km_s=float(velocity["kilometers_per_second"]),
                        velocity_km_h=float(velocity["kilometers_per_hour"]),
                        close_approach_time=datetime.fromtimestamp(
                            close_approach["epoch_date_close_approach"] / 1000, tz=UTC
                        ),
                        jpl_url=obj["nasa_jpl_url"],
                        is_sentry_object=bool(obj["is_sentry_object"]),
                    )
                )
        return highlights
