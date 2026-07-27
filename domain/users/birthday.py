from __future__ import annotations

from calendar import isleap
from datetime import date as date_


def is_birthday_today(birthday: date_, today: date_) -> bool:
    """Сравнение только по месяцу/дню, год не важен. 29 февраля в
    невисокосный год считается за 28-е (см. docs/tz/TZ-birthday.md)."""
    if birthday.month == 2 and birthday.day == 29 and not isleap(today.year):
        return today.month == 2 and today.day == 28
    return birthday.month == today.month and birthday.day == today.day
