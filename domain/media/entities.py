from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_


@dataclass(frozen=True, slots=True)
class ApodEntry:
    date: date_
    message_id: int


@dataclass(frozen=True, slots=True)
class EpicDay:
    date: date_
    gif_message_id: int | None = None

    @property
    def is_cached(self) -> bool:
        return self.gif_message_id is not None
