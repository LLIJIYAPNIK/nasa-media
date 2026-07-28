from __future__ import annotations

from collections.abc import Sequence
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
        data = await fetch_json(
            self._session,
            self._base_url,
            {"start_date": day.isoformat(), "end_date": day.isoformat(), "api_key": self._api_key},
        )

        objects = data.get("near_earth_objects", {}).get(day.isoformat(), [])
        highlights = []
        for obj in objects:
            diameter = obj["estimated_diameter"]["meters"]
            miss_distance = obj["close_approach_data"][0]["miss_distance"]
            highlights.append(
                AsteroidHighlight(
                    name=obj["name"],
                    diameter_min_m=float(diameter["estimated_diameter_min"]),
                    diameter_max_m=float(diameter["estimated_diameter_max"]),
                    miss_distance_km=float(miss_distance["kilometers"]),
                    miss_distance_lunar=float(miss_distance["lunar"]),
                    is_hazardous=bool(obj["is_potentially_hazardous_asteroid"]),
                )
            )
        return highlights
