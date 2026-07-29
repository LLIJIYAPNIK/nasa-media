from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import date as date_
from datetime import timedelta
from typing import Protocol

from application.digest.ports import NaturalEventClient, NearEarthObjectClient, SpaceWeatherClient
from application.web.homepage_query import SPACE_WEATHER_TYPE_LABELS
from domain.digest.digest_text import pick_closest_asteroid, pick_latest_earth_event, pick_significant_space_weather
from domain.digest.size_comparison import compare_to_familiar_object
from domain.digest.speed_comparison import compare_speed_to_familiar_reference
from domain.digest.value_objects import EarthEventHighlight, EventSource
from domain.media.exceptions import MediaNotAvailable
from infrastructure.nasa.apod_client import ApodData


class UnknownHomepageDetailKind(Exception):
    """Кидается для kind вне известных 4 — роутер превращает это в 404 с
    понятным телом (см. docs/tz/TZ-web.md, «Роуты»)."""


class ApodRawClient(Protocol):
    async def fetch_raw(self, day: date_) -> ApodData: ...


class EventMapBuilder(Protocol):
    """Порт для карты события Земли — см.
    docs/tz/TZ_karta_sobytiya_EONET.md. Возвращает уже закешированный или
    только что сгенерированный `cache_key` (без сети — реализация сама
    решает, генерировать заново или отдать из кеша), либо `None`, если
    у события нет координат/id, либо генерация не удалась (недоступность
    карты не должна ломать остальную карточку)."""

    async def build(self, event: EarthEventHighlight) -> str | None: ...


@dataclass(frozen=True, slots=True)
class SpaceWeatherEventItem:
    """Один пункт полного списка DONKI-уведомлений за день в модалке —
    см. docs/tz/TZ-web-space-weather-detail.md."""

    type: str
    label: str
    issued_at: str


@dataclass(frozen=True, slots=True)
class HomepageDetail:
    """Полное содержимое модалки для одной из 4 карточек ежедневной
    статистики. Плоская структура с полями под все 4 kind сразу — проще
    сериализовать в JSON, чем union-тип, а разница между kind невелика."""

    kind: str
    available: bool
    message: str | None = None

    apod_title: str | None = None
    apod_description: str | None = None
    apod_image_url: str | None = None
    apod_copyright: str | None = None

    asteroid_name: str | None = None
    asteroid_diameter_min_m: float | None = None
    asteroid_diameter_max_m: float | None = None
    asteroid_size_comparison: str | None = None
    asteroid_is_hazardous: bool | None = None
    asteroid_miss_distance_lunar: float | None = None
    asteroid_miss_distance_km: float | None = None
    asteroid_miss_distance_au: float | None = None
    asteroid_miss_distance_miles: float | None = None
    asteroid_velocity_km_s: float | None = None
    asteroid_velocity_km_h: float | None = None
    asteroid_speed_comparison: str | None = None
    asteroid_close_approach_time: str | None = None
    asteroid_jpl_url: str | None = None
    asteroid_is_sentry_object: bool | None = None

    space_weather_events: list[SpaceWeatherEventItem] | None = None
    space_weather_summary_type: str | None = None
    space_weather_summary_label: str | None = None
    space_weather_summary_issued_at: str | None = None

    earth_event_title: str | None = None
    earth_event_category: str | None = None
    earth_event_categories: Sequence[str] = ()
    earth_event_date: str | None = None
    earth_event_description: str | None = None
    earth_event_closed_at: str | None = None
    earth_event_magnitude_value: float | None = None
    earth_event_magnitude_unit: str | None = None
    earth_event_magnitude_description: str | None = None
    earth_event_sources: Sequence[EventSource] = ()
    earth_event_link: str | None = None
    earth_event_map_url: str | None = None


class GetHomepageDetail:
    def __init__(
        self,
        apod_client: ApodRawClient,
        space_weather_client: SpaceWeatherClient,
        near_earth_object_client: NearEarthObjectClient,
        natural_event_client: NaturalEventClient,
        event_map_builder: EventMapBuilder,
    ) -> None:
        self._apod_client = apod_client
        self._space_weather_client = space_weather_client
        self._near_earth_object_client = near_earth_object_client
        self._natural_event_client = natural_event_client
        self._event_map_builder = event_map_builder
        self._handlers: dict[str, Callable[[date_], Awaitable[HomepageDetail]]] = {
            "apod": self._apod_detail,
            "asteroid": self._asteroid_detail,
            "space-weather": self._space_weather_detail,
            "earth-event": self._earth_event_detail,
        }

    async def execute(self, kind: str, today: date_) -> HomepageDetail:
        handler = self._handlers.get(kind)
        if handler is None:
            raise UnknownHomepageDetailKind(kind)
        return await handler(today)

    async def _apod_detail(self, today: date_) -> HomepageDetail:
        try:
            data = await self._apod_client.fetch_raw(today)
        except MediaNotAvailable:
            return await self._apod_detail_fallback_to_previous_day(today)
        return HomepageDetail(
            kind="apod",
            available=True,
            apod_title=data.title,
            apod_description=data.explanation,
            apod_image_url=data.image_url,
            apod_copyright=data.copyright,
        )

    async def _apod_detail_fallback_to_previous_day(self, today: date_) -> HomepageDetail:
        # NASA иногда публикует APOD за сегодня с задержкой (часовые пояса,
        # ручная модерация) — вместо пустой модалки показываем вчерашнюю
        # картинку с пояснением, а не оставляем карточку без содержимого.
        try:
            data = await self._apod_client.fetch_raw(today - timedelta(days=1))
        except MediaNotAvailable:
            return HomepageDetail(
                kind="apod", available=False, message="Картинка дня на сегодня ещё не опубликована NASA."
            )
        return HomepageDetail(
            kind="apod",
            available=True,
            message="Картинка дня на сегодня ещё не опубликована NASA — показываем вчерашнюю.",
            apod_title=data.title,
            apod_description=data.explanation,
            apod_image_url=data.image_url,
            apod_copyright=data.copyright,
        )

    async def _asteroid_detail(self, today: date_) -> HomepageDetail:
        asteroids = await self._near_earth_object_client.fetch_for_day(today)
        asteroid = pick_closest_asteroid(asteroids)
        if asteroid is None:
            return HomepageDetail(kind="asteroid", available=False, message="Заметных астероидов сегодня нет.")
        return HomepageDetail(
            kind="asteroid",
            available=True,
            asteroid_name=asteroid.name,
            asteroid_diameter_min_m=asteroid.diameter_min_m,
            asteroid_diameter_max_m=asteroid.diameter_max_m,
            asteroid_size_comparison=compare_to_familiar_object(asteroid.diameter_max_m),
            asteroid_is_hazardous=asteroid.is_hazardous,
            asteroid_miss_distance_lunar=asteroid.miss_distance_lunar,
            asteroid_miss_distance_km=asteroid.miss_distance_km,
            asteroid_miss_distance_au=asteroid.miss_distance_au,
            asteroid_miss_distance_miles=asteroid.miss_distance_miles,
            asteroid_velocity_km_s=asteroid.velocity_km_s,
            asteroid_velocity_km_h=asteroid.velocity_km_h,
            asteroid_speed_comparison=compare_speed_to_familiar_reference(asteroid.velocity_km_s),
            asteroid_close_approach_time=asteroid.close_approach_time.isoformat(),
            asteroid_jpl_url=asteroid.jpl_url,
            asteroid_is_sentry_object=asteroid.is_sentry_object,
        )

    async def _space_weather_detail(self, today: date_) -> HomepageDetail:
        events = await self._space_weather_client.fetch_for_day(today)
        if not events:
            return HomepageDetail(kind="space-weather", available=False, message="Космос сегодня спокоен.")

        significant = pick_significant_space_weather(events)
        return HomepageDetail(
            kind="space-weather",
            available=True,
            space_weather_events=[
                SpaceWeatherEventItem(
                    type=event.message_type,
                    label=SPACE_WEATHER_TYPE_LABELS.get(event.message_type, event.message_type),
                    issued_at=event.issued_at.isoformat(),
                )
                for event in sorted(events, key=lambda event: event.issued_at)
            ],
            space_weather_summary_type=significant.message_type if significant else None,
            space_weather_summary_label=(
                SPACE_WEATHER_TYPE_LABELS.get(significant.message_type, significant.message_type)
                if significant
                else "Спокойно"
            ),
            space_weather_summary_issued_at=significant.issued_at.isoformat() if significant else None,
        )

    async def _earth_event_detail(self, _today: date_) -> HomepageDetail:
        # EONET не фильтруется по дате (см. application/digest/ports.py) —
        # параметр только ради единой сигнатуры обработчиков в self._handlers.
        events = await self._natural_event_client.fetch_recent()
        event = pick_latest_earth_event(events)
        if event is None:
            return HomepageDetail(kind="earth-event", available=False, message="Заметных событий на Земле сегодня нет.")

        map_cache_key = await self._event_map_builder.build(event)
        map_url = f"/api/homepage/earth-event-map/{map_cache_key}.png" if map_cache_key else None

        return HomepageDetail(
            kind="earth-event",
            available=True,
            earth_event_title=event.title,
            earth_event_category=event.category,
            earth_event_categories=event.categories,
            earth_event_date=event.event_date.isoformat(),
            earth_event_description=event.description,
            earth_event_closed_at=event.closed_at.isoformat() if event.closed_at else None,
            earth_event_magnitude_value=event.magnitude_value,
            earth_event_magnitude_unit=event.magnitude_unit,
            earth_event_magnitude_description=event.magnitude_description,
            earth_event_sources=event.sources,
            earth_event_link=event.link or None,
            earth_event_map_url=map_url,
        )
