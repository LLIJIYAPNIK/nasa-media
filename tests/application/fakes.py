from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_

from application.media.ports import CachedMessageRef, MediaPayload
from domain.media.entities import ApodEntry, EpicDay
from domain.media.exceptions import MediaNotAvailable
from domain.media.value_objects import MediaSourceKind
from domain.users.entities import User


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
