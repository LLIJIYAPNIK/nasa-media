from __future__ import annotations

import asyncio
from datetime import date as date_

from application.digest.ports import DigestRepository, NaturalEventClient, NearEarthObjectClient, SpaceWeatherClient
from application.media.ports import AdminChatGateway, ApodRepository, CachedMessageRef, TextPayload
from domain.digest.digest_text import (
    build_digest_text,
    pick_closest_asteroid,
    pick_latest_earth_event,
    pick_significant_space_weather,
)
from domain.digest.entities import DigestEntry


class DigestSourceAdapter:
    """Реализует MediaSourceAdapter (application/media/source_adapters.py) —
    подключается к уже существующему DeliverMediaForDate/BroadcastSubscribedUsers
    без изменений в них, см. docs/tz/TZ-daily-digest.md."""

    def __init__(
        self,
        space_weather_client: SpaceWeatherClient,
        near_earth_object_client: NearEarthObjectClient,
        natural_event_client: NaturalEventClient,
        apod_repo: ApodRepository,
        digest_repo: DigestRepository,
        gateway: AdminChatGateway,
    ) -> None:
        self._space_weather_client = space_weather_client
        self._near_earth_object_client = near_earth_object_client
        self._natural_event_client = natural_event_client
        self._apod_repo = apod_repo
        self._digest_repo = digest_repo
        self._gateway = gateway

    async def get_cached(self, day: date_) -> CachedMessageRef | None:
        entry = await self._digest_repo.get_by_date(day)
        return CachedMessageRef(message_id=entry.message_id) if entry else None

    async def fetch_and_cache(self, day: date_) -> CachedMessageRef:
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
        ref = await self._gateway.publish(TextPayload(text=text))
        await self._digest_repo.save(DigestEntry(date=day, message_id=ref.message_id))
        return ref

    async def forward_cached(self, ref: CachedMessageRef, chat_id: int) -> None:
        await self._gateway.forward_single(ref.message_id, chat_id)
