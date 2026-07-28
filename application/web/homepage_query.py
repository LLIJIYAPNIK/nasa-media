from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date as date_

from application.digest.ports import NaturalEventClient, NearEarthObjectClient, SpaceWeatherClient
from domain.digest.digest_text import pick_closest_asteroid, pick_latest_earth_event, pick_significant_space_weather
from domain.media.apod_day_count import days_since_apod_launch

# Короткие подписи без эмодзи для веба — отдельно от домена digest_text._SPACE_WEATHER_LABELS
# (тот словарь приватный и заточен под Telegram-текст, см. docs/tz/TZ-web.md,
# «Данные для страницы»). Используется и здесь, и в homepage_detail_query.py.
SPACE_WEATHER_TYPE_LABELS = {
    "GST": "Геомагнитная буря",
    "FLR": "Солнечная вспышка",
    "CME": "Выброс корональной массы",
    "IPS": "Межпланетная ударная волна",
    "RBE": "Всплеск релятивистских электронов",
}


@dataclass(frozen=True, slots=True)
class HomepageSnapshot:
    apod_day_number: int
    asteroid_name: str | None = None
    asteroid_miss_distance_lunar: float | None = None
    space_weather_label: str | None = None
    earth_event_title: str | None = None
    earth_event_category: str | None = None


class GetHomepageSnapshot:
    """Собирает 4 краткие карточки главной страницы — не через
    application/media/admin-chat-кеш (тот про «закешировать и переслать в
    Telegram-чат»), а напрямую из тех же портов источников, что и дайджест
    бота (см. docs/tz/TZ-web.md, «Данные для страницы»)."""

    def __init__(
        self,
        space_weather_client: SpaceWeatherClient,
        near_earth_object_client: NearEarthObjectClient,
        natural_event_client: NaturalEventClient,
    ) -> None:
        self._space_weather_client = space_weather_client
        self._near_earth_object_client = near_earth_object_client
        self._natural_event_client = natural_event_client

    async def execute(self, today: date_) -> HomepageSnapshot:
        space_weather_events, asteroids, earth_events = await asyncio.gather(
            self._space_weather_client.fetch_for_day(today),
            self._near_earth_object_client.fetch_for_day(today),
            self._natural_event_client.fetch_recent(),
        )

        asteroid = pick_closest_asteroid(asteroids)
        space_weather = pick_significant_space_weather(space_weather_events)
        earth_event = pick_latest_earth_event(earth_events)

        return HomepageSnapshot(
            apod_day_number=days_since_apod_launch(today),
            asteroid_name=asteroid.name if asteroid else None,
            asteroid_miss_distance_lunar=asteroid.miss_distance_lunar if asteroid else None,
            space_weather_label=(
                SPACE_WEATHER_TYPE_LABELS.get(space_weather.message_type, space_weather.message_type)
                if space_weather
                else None
            ),
            earth_event_title=earth_event.title if earth_event else None,
            earth_event_category=earth_event.category if earth_event else None,
        )
