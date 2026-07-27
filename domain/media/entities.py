from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_


@dataclass(frozen=True, slots=True)
class ApodEntry:
    date: date_
    message_id: int


@dataclass(frozen=True, slots=True)
class EpicFrame:
    telegram_file_id: str
    position: int


@dataclass(frozen=True, slots=True)
class EpicDay:
    date: date_
    frames: tuple[EpicFrame, ...] = ()

    @property
    def is_cached(self) -> bool:
        return len(self.frames) > 0
