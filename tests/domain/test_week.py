from datetime import date

import pytest

from domain.digest.week import week_start


@pytest.mark.parametrize(
    ("day", "expected_monday"),
    [
        (date(2026, 7, 27), date(2026, 7, 27)),  # понедельник — сам себе начало недели
        (date(2026, 7, 28), date(2026, 7, 27)),  # вторник
        (date(2026, 7, 29), date(2026, 7, 27)),  # среда
        (date(2026, 7, 30), date(2026, 7, 27)),  # четверг
        (date(2026, 7, 31), date(2026, 7, 27)),  # пятница
        (date(2026, 8, 1), date(2026, 7, 27)),  # суббота
        (date(2026, 8, 2), date(2026, 7, 27)),  # воскресенье
    ],
)
def test_week_start_returns_monday_of_the_same_week(day: date, expected_monday: date):
    assert week_start(day) == expected_monday
