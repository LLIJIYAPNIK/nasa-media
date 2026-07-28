from __future__ import annotations

from datetime import date as date_
from datetime import timedelta


def week_start(day: date_) -> date_:
    """Понедельник недели, которой принадлежит day (ISO-стандарт: неделя
    начинается с понедельника, weekday() == 0)."""
    return day - timedelta(days=day.weekday())
