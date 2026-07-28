from __future__ import annotations

import asyncio
from datetime import date as date_
from datetime import timedelta

from application.digest.ports import NaturalEventClient, NearEarthObjectClient, SpaceWeatherClient
from application.media.ports import GeneratedImagePayload
from domain.digest.digest_text import (
    build_weekly_highlights_lines,
    pick_largest_asteroid,
    pick_latest_earth_event,
    pick_significant_space_weather,
)
from infrastructure.files.card_builder import build_card


class WeeklyHighlightsProvider:
    """Реализует MediaProvider — по форме как DigestProvider, но день,
    переданный в fetch(), трактуется как понедельник недели (см.
    domain/digest/week.py): сама fetch() считает конец недели и запрашивает
    диапазон, а не один день. Без ссылки на APOD — итоги недели не про
    конкретный день (см. docs/tz/TZ-weekly-highlights.md)."""

    def __init__(
        self,
        space_weather_client: SpaceWeatherClient,
        near_earth_object_client: NearEarthObjectClient,
        natural_event_client: NaturalEventClient,
    ) -> None:
        self._space_weather_client = space_weather_client
        self._near_earth_object_client = near_earth_object_client
        self._natural_event_client = natural_event_client

    async def fetch(self, day: date_) -> GeneratedImagePayload:
        week_start_date = day
        week_end_date = day + timedelta(days=6)

        space_weather_events, asteroids, earth_events = await asyncio.gather(
            self._space_weather_client.fetch_for_range(week_start_date, week_end_date),
            self._near_earth_object_client.fetch_for_range(week_start_date, week_end_date),
            self._natural_event_client.fetch_recent(),
        )
        lines = build_weekly_highlights_lines(
            week_start_date,
            week_end_date,
            pick_significant_space_weather(space_weather_events),
            pick_largest_asteroid(asteroids),
            pick_latest_earth_event(earth_events),
        )
        title, *body_lines = lines
        body_lines = [line for line in body_lines if line]
        image_bytes = await build_card(title=title, lines=body_lines)
        return GeneratedImagePayload(image_bytes=image_bytes, caption=title)
