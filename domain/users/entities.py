from __future__ import annotations

from dataclasses import dataclass, replace

from domain.media.value_objects import MediaSourceKind


@dataclass(frozen=True, slots=True)
class User:
    chat_id: int
    apod_subscribed: bool = False
    epic_subscribed: bool = False

    def is_subscribed(self, source: MediaSourceKind) -> bool:
        return self.apod_subscribed if source is MediaSourceKind.APOD else self.epic_subscribed

    def with_subscription(self, source: MediaSourceKind, value: bool) -> User:
        if source is MediaSourceKind.APOD:
            return replace(self, apod_subscribed=value)
        return replace(self, epic_subscribed=value)
