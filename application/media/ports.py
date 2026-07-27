from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date as date_
from typing import Protocol

from domain.media.entities import ApodEntry, EpicDay
from domain.media.value_objects import MediaSourceKind
from domain.users.entities import User


@dataclass(frozen=True, slots=True)
class SinglePhotoPayload:
    """APOD: одно изображение по прямой ссылке с готовой (переведённой) подписью."""

    image_url: str
    caption: str


@dataclass(frozen=True, slots=True)
class PhotoGroupPayload:
    """EPIC: набор уже скачанных изображений без подписи."""

    images: Sequence[bytes]


MediaPayload = SinglePhotoPayload | PhotoGroupPayload


@dataclass(frozen=True, slots=True)
class SingleMessageRef:
    """Что возвращает admin-чат после публикации SinglePhotoPayload (APOD)."""

    message_id: int


@dataclass(frozen=True, slots=True)
class GroupMessageRef:
    """Что возвращает admin-чат после публикации PhotoGroupPayload (EPIC)."""

    frame_file_ids: tuple[str, ...]


CachedMessageRef = SingleMessageRef | GroupMessageRef


class MediaProvider(Protocol):
    async def fetch(self, day: date_) -> MediaPayload:
        """Кидает MediaNotAvailable, если у NASA нет данных за дату."""
        ...


class Translator(Protocol):
    async def translate_to_ru(self, text: str) -> str: ...


class AdminChatGateway(Protocol):
    async def publish(self, payload: MediaPayload) -> CachedMessageRef: ...

    async def forward_single(self, message_id: int, chat_id: int) -> None: ...

    async def forward_group(self, frame_file_ids: Sequence[str], chat_id: int) -> None: ...


class ApodRepository(Protocol):
    async def get_by_date(self, day: date_) -> ApodEntry | None: ...

    async def save(self, entry: ApodEntry) -> None: ...


class EpicRepository(Protocol):
    async def get_by_date(self, day: date_) -> EpicDay | None: ...

    async def save(self, day: EpicDay) -> None: ...

    async def ensure_known_dates(self, days: Sequence[date_]) -> None:
        """Создаёт EpicDay(frames=()) для дат, которых ещё нет в репозитории."""
        ...


class UserRepository(Protocol):
    async def get_by_chat_id(self, chat_id: int) -> User | None: ...

    async def add(self, chat_id: int) -> User: ...

    async def save(self, user: User) -> None: ...

    async def list_subscribed(self, source: MediaSourceKind) -> Sequence[User]: ...
