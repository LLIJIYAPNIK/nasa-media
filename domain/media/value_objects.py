from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Iterator

MAX_DATE_RANGE_DAYS = 5

# NASA EPIC не отдаёт снимки раньше этой даты — характеристика самого API,
# в старом коде было зашито прямо в хендлере, конфигурируемым параметром
# никогда не было.
EPIC_LOWER_BOUND = date(2015, 6, 13)


class MediaSourceKind(Enum):
    APOD = "apod"
    EPIC = "epic"


class InvalidMediaDate(ValueError):
    """Дата или диапазон дат нарушает правила источника."""


@dataclass(frozen=True, slots=True)
class DateRange:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise InvalidMediaDate("Конечная дата должна быть не раньше начальной")
        if (self.end - self.start) > timedelta(days=MAX_DATE_RANGE_DAYS):
            raise InvalidMediaDate(f"Разница между датами не должна превышать {MAX_DATE_RANGE_DAYS} дней")

    def iter_dates(self) -> Iterator[date]:
        current = self.start
        while current <= self.end:
            yield current
            current += timedelta(days=1)


def ensure_within_bounds(value: date, lower_bound: date, today: date) -> None:
    if value < lower_bound:
        raise InvalidMediaDate(f"Минимальная дата — {lower_bound.isoformat()}")
    if value > today:
        raise InvalidMediaDate("Максимальная дата — сегодня")
