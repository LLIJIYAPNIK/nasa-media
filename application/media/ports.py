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
class AnimationPayload:
    """EPIC: собранная из кадров суток анимация (сейчас — GIF, см.
    TZ-gif-timelapse.md), без подписи."""

    gif_bytes: bytes


MediaPayload = SinglePhotoPayload | AnimationPayload


@dataclass(frozen=True, slots=True)
class CachedMessageRef:
    """Что возвращает admin-чат после первой публикации — то, что кладём в
    репозиторий. Один message_id для обоих источников: EPIC раньше кешировал
    отдельные кадры как медиа-группу, теперь — как и APOD, одно сообщение."""

    message_id: int


class MediaProvider(Protocol):
    async def fetch(self, day: date_) -> MediaPayload:
        """Кидает MediaNotAvailable, если у NASA нет данных за дату."""
        ...


class Translator(Protocol):
    async def translate_to_ru(self, text: str) -> str: ...


class AdminChatGateway(Protocol):
    async def publish(self, payload: MediaPayload) -> CachedMessageRef: ...

    async def forward_single(self, message_id: int, chat_id: int) -> None: ...


class GreetingSender(Protocol):
    """Личное текстовое сообщение пользователю — не через admin-чат: не
    кешируется и не переиспользуется другими получателями."""

    async def send_text(self, chat_id: int, text: str) -> None: ...


class ApodRepository(Protocol):
    async def get_by_date(self, day: date_) -> ApodEntry | None: ...

    async def save(self, entry: ApodEntry) -> None: ...


class EpicRepository(Protocol):
    async def get_by_date(self, day: date_) -> EpicDay | None: ...

    async def save(self, day: EpicDay) -> None: ...

    async def ensure_known_dates(self, days: Sequence[date_]) -> None:
        """Создаёт EpicDay(gif_message_id=None) для дат, которых ещё нет в репозитории."""
        ...


class UserRepository(Protocol):
    async def get_by_chat_id(self, chat_id: int) -> User | None: ...

    async def add(self, chat_id: int) -> User: ...

    async def save(self, user: User) -> None: ...

    async def list_subscribed(self, source: MediaSourceKind) -> Sequence[User]: ...

    async def list_with_birthday_set(self) -> Sequence[User]:
        """Дальнейшая фильтрация по месяцу/дню — доменным правилом
        is_birthday_today, не здесь (см. domain/users/birthday.py)."""
        ...
