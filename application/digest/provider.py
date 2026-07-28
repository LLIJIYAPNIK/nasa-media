from __future__ import annotations

import asyncio
from datetime import date as date_

from application.digest.ports import NaturalEventClient, NearEarthObjectClient, SpaceWeatherClient
from application.media.ports import ApodRepository, TextPayload
from domain.digest.digest_text import (
    build_digest_text,
    pick_closest_asteroid,
    pick_latest_earth_event,
    pick_significant_space_weather,
)


class DigestProvider:
    """Реализует MediaProvider (application/media/ports.py) — как
    ApodProvider/EpicProvider, но без похода в сеть напрямую: собирает уже
    инжектированные порты источников (сеть — внутри самих *Client в
    infrastructure/nasa/), а форматирование — доменными функциями. Выделен
    отдельно от DigestSourceAdapter, чтобы адаптер оставался такой же тонкой
    формой, как ApodSourceAdapter/EpicSourceAdapter (get_cached/
    fetch_and_cache/forward_cached, вся сборка — на стороне провайдера)."""

    def __init__(
        self,
        space_weather_client: SpaceWeatherClient,
        near_earth_object_client: NearEarthObjectClient,
        natural_event_client: NaturalEventClient,
        apod_repo: ApodRepository,
    ) -> None:
        self._space_weather_client = space_weather_client
        self._near_earth_object_client = near_earth_object_client
        self._natural_event_client = natural_event_client
        self._apod_repo = apod_repo

    async def fetch(self, day: date_) -> TextPayload:
        space_weather_events, asteroids, earth_events, apod_entry = await asyncio.gather(
            self._space_weather_client.fetch_for_day(day),
            self._near_earth_object_client.fetch_for_day(day),
            self._natural_event_client.fetch_recent(),
            self._apod_repo.get_by_date(day),
        )
        text = build_digest_text(
            day,
            pick_significant_space_weather(space_weather_events),
            pick_closest_asteroid(asteroids),
            pick_latest_earth_event(earth_events),
            apod_cached=apod_entry is not None,
        )
        return TextPayload(text=text)
