from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_


@dataclass(frozen=True, slots=True)
class DigestEntry:
    date: date_
    message_id: int


@dataclass(frozen=True, slots=True)
class WeeklyHighlightEntry:
    week_start_date: date_
    message_id: int
