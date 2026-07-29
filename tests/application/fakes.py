from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_

from application.media.ports import CachedMessageRef, MediaPayload
from domain.digest.entities import DigestEntry, WeeklyHighlightEntry
from domain.digest.value_objects import AsteroidHighlight, EarthEventHighlight, SpaceWeatherHighlight
from domain.media.entities import ApodEntry, EpicDay
from domain.media.exceptions import MediaNotAvailable
from domain.media.value_objects import MediaSourceKind
from domain.users.entities import User
from infrastructure.nasa.apod_client import ApodData


class FakeApodRawClient:
    def __init__(
        self,
        data: ApodData | None = None,
        raise_not_available: bool = False,
        unavailable_days: Sequence[date_] = (),
    ) -> None:
        self.data = data
        self.raise_not_available = raise_not_available
        self.unavailable_days = set(unavailable_days)
        self.calls: list[date_] = []

    async def fetch_raw(self, day: date_) -> ApodData:
        self.calls.append(day)
        if self.raise_not_available or day in self.unavailable_days:
            raise MediaNotAvailable("нет данных")
        assert self.data is not None, "FakeApodRawClient needs data when raise_not_available=False"
        return self.data


class FakeApodProvider:
    def __init__(self, payload: MediaPayload | None = None, raise_not_available: bool = False) -> None:
        self.payload = payload
        self.raise_not_available = raise_not_available
        self.calls: list[date_] = []

    async def fetch(self, day: date_) -> MediaPayload:
        self.calls.append(day)
        if self.raise_not_available:
            raise MediaNotAvailable("нет данных")
        assert self.payload is not None, "FakeApodProvider needs a payload when raise_not_available=False"
        return self.payload


class FakeApodRepository:
    def __init__(self) -> None:
        self._storage: dict[date_, ApodEntry] = {}

    async def get_by_date(self, day: date_) -> ApodEntry | None:
        return self._storage.get(day)

    async def save(self, entry: ApodEntry) -> None:
        self._storage[entry.date] = entry


class FakeEpicRepository:
    def __init__(self) -> None:
        self._storage: dict[date_, EpicDay] = {}

    async def get_by_date(self, day: date_) -> EpicDay | None:
        return self._storage.get(day)

    async def save(self, day: EpicDay) -> None:
        self._storage[day.date] = day

    async def ensure_known_dates(self, days: Sequence[date_]) -> None:
        for day in days:
            if day not in self._storage:
                self._storage[day] = EpicDay(date=day)


class FakeAdminChatGateway:
    def __init__(self, ref: CachedMessageRef | None = None) -> None:
        self.ref: CachedMessageRef = ref or CachedMessageRef(message_id=1)
        self.published: list[MediaPayload] = []
        self.forwarded_single: list[tuple[int, int]] = []

    async def publish(self, payload: MediaPayload) -> CachedMessageRef:
        self.published.append(payload)
        return self.ref

    async def forward_single(self, message_id: int, chat_id: int) -> None:
        self.forwarded_single.append((message_id, chat_id))


class FakeUserRepository:
    def __init__(self, users: Sequence[User] | None = None) -> None:
        self._by_chat_id: dict[int, User] = {user.chat_id: user for user in (users or [])}

    async def get_by_chat_id(self, chat_id: int) -> User | None:
        return self._by_chat_id.get(chat_id)

    async def add(self, chat_id: int) -> User:
        user = User(chat_id=chat_id)
        self._by_chat_id[chat_id] = user
        return user

    async def save(self, user: User) -> None:
        self._by_chat_id[user.chat_id] = user

    async def list_subscribed(self, source: MediaSourceKind) -> Sequence[User]:
        return [user for user in self._by_chat_id.values() if user.is_subscribed(source)]

    async def list_with_birthday_set(self) -> Sequence[User]:
        return [user for user in self._by_chat_id.values() if user.birthday is not None]


class FakeGreetingSender:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []
        self.sent_images: list[tuple[int, bytes, str | None]] = []

    async def send_text(self, chat_id: int, text: str) -> None:
        self.sent.append((chat_id, text))

    async def send_image(self, chat_id: int, image_bytes: bytes, caption: str | None = None) -> None:
        self.sent_images.append((chat_id, image_bytes, caption))


class FakeSpaceWeatherClient:
    def __init__(self, events: Sequence[SpaceWeatherHighlight] | None = None) -> None:
        self.events = events or []
        self.calls: list[date_] = []
        self.range_calls: list[tuple[date_, date_]] = []

    async def fetch_for_day(self, day: date_) -> Sequence[SpaceWeatherHighlight]:
        self.calls.append(day)
        return self.events

    async def fetch_for_range(self, start: date_, end: date_) -> Sequence[SpaceWeatherHighlight]:
        self.range_calls.append((start, end))
        return self.events


class FakeNearEarthObjectClient:
    def __init__(self, asteroids: Sequence[AsteroidHighlight] | None = None) -> None:
        self.asteroids = asteroids or []
        self.calls: list[date_] = []
        self.range_calls: list[tuple[date_, date_]] = []

    async def fetch_for_day(self, day: date_) -> Sequence[AsteroidHighlight]:
        self.calls.append(day)
        return self.asteroids

    async def fetch_for_range(self, start: date_, end: date_) -> Sequence[AsteroidHighlight]:
        self.range_calls.append((start, end))
        return self.asteroids


class FakeNaturalEventClient:
    def __init__(self, events: Sequence[EarthEventHighlight] | None = None) -> None:
        self.events = events or []
        self.calls = 0

    async def fetch_recent(self) -> Sequence[EarthEventHighlight]:
        self.calls += 1
        return self.events


class FakeDigestRepository:
    def __init__(self) -> None:
        self._storage: dict[date_, DigestEntry] = {}

    async def get_by_date(self, day: date_) -> DigestEntry | None:
        return self._storage.get(day)

    async def save(self, entry: DigestEntry) -> None:
        self._storage[entry.date] = entry


class FakeWeeklyHighlightsRepository:
    def __init__(self) -> None:
        self._storage: dict[date_, WeeklyHighlightEntry] = {}

    async def get_by_date(self, week_start_date: date_) -> WeeklyHighlightEntry | None:
        return self._storage.get(week_start_date)

    async def save(self, entry: WeeklyHighlightEntry) -> None:
        self._storage[entry.week_start_date] = entry
