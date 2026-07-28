from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_

from domain.users.value_objects import PlanetaryAge

# Ближайшее задокументированное новолуние, общепринятая опорная дата в
# астрономических расчётах фазы Луны (см. docs/tz/TZ-birthday-cosmic-facts.md).
MOON_REFERENCE_DATE = date_(2000, 1, 6)
SYNODIC_MONTH_DAYS = 29.530588

_MOON_PHASE_NAMES = (
    "новолуние",
    "растущий серп",
    "первая четверть",
    "растущая луна",
    "полнолуние",
    "убывающая луна",
    "последняя четверть",
    "убывающий серп",
)

# Только планеты с орбитальным периодом короче или сравнимым с человеческой
# жизнью — Юпитер и дальше дали бы "0 лет" почти для всех пользователей.
_PLANET_PERIOD_DAYS = (
    ("Меркурий", 87.97),
    ("Венера", 224.7),
    ("Марс", 686.98),
)

_PLANET_ADJECTIVES = {
    "Меркурий": "меркурианских",
    "Венера": "венерианских",
    "Марс": "марсианских",
}

# Защита от ошибки округления float на точных кратных периода (см. тесты).
_EPSILON = 1e-9


def moon_phase_fraction(day: date_) -> float:
    """0.0 = новолуние, 0.5 = полнолуние. Точность в пределах суток — не
    претендует на точность профессиональных альманахов (без поправок на
    эллиптичность орбиты)."""
    days_since = (day - MOON_REFERENCE_DATE).days
    return (days_since % SYNODIC_MONTH_DAYS) / SYNODIC_MONTH_DAYS


def moon_phase_name(fraction: float) -> str:
    index = int(fraction // (1 / 8)) % len(_MOON_PHASE_NAMES)
    return _MOON_PHASE_NAMES[index]


def planetary_ages(birthday: date_, today: date_) -> Sequence[PlanetaryAge]:
    days_lived = (today - birthday).days
    return [
        PlanetaryAge(planet_name=name, age_years=int(days_lived / period_days + _EPSILON))
        for name, period_days in _PLANET_PERIOD_DAYS
    ]


def build_cosmic_facts_text(birthday: date_, today: date_) -> str:
    phase_name = moon_phase_name(moon_phase_fraction(today))
    ages = planetary_ages(birthday, today)
    ages_lines = "\n".join(
        f"{age.planet_name}: тебе исполнилось {age.age_years} {_PLANET_ADJECTIVES[age.planet_name]} лет."
        for age in ages
    )
    return f"🌙 Сегодня фаза Луны: {phase_name}.\n🪐 {ages_lines}"
