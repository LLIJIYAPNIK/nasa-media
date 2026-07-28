from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date as date_

from domain.media.value_objects import MediaSourceKind

_SUBSCRIPTION_FIELDS = {
    MediaSourceKind.APOD: "apod_subscribed",
    MediaSourceKind.EPIC: "epic_subscribed",
    MediaSourceKind.DIGEST: "digest_subscribed",
}


@dataclass(frozen=True, slots=True)
class User:
    chat_id: int
    apod_subscribed: bool = False
    epic_subscribed: bool = False
    digest_subscribed: bool = False
    birthday: date_ | None = None

    def is_subscribed(self, source: MediaSourceKind) -> bool:
        return bool(getattr(self, _SUBSCRIPTION_FIELDS[source]))

    def with_subscription(self, source: MediaSourceKind, value: bool) -> User:
        # mypy's dataclass plugin can't verify a **kwargs splat keyed by a
        # runtime-computed field name against the real per-field types.
        return replace(self, **{_SUBSCRIPTION_FIELDS[source]: value})  # type: ignore[arg-type]

    def with_birthday(self, birthday: date_) -> User:
        return replace(self, birthday=birthday)
