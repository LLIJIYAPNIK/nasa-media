from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date as date_

from domain.media.value_objects import MediaSourceKind

# Публичная (не приватная) карта: infrastructure/db/repositories.py тоже
# сверяется с ней при выборе колонки для list_subscribed — один источник
# правды на имя поля источника, а не вторая независимая карта.
SUBSCRIPTION_FIELDS = {
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
        return bool(getattr(self, SUBSCRIPTION_FIELDS[source]))

    def with_subscription(self, source: MediaSourceKind, value: bool) -> User:
        # mypy's dataclass plugin can't verify a **kwargs splat keyed by a
        # runtime-computed field name against the real per-field types.
        return replace(self, **{SUBSCRIPTION_FIELDS[source]: value})  # type: ignore[arg-type]

    def with_birthday(self, birthday: date_) -> User:
        return replace(self, birthday=birthday)
