import math
from datetime import date, timedelta

import pytest

from domain.users.cosmic_facts import (
    MOON_REFERENCE_DATE,
    build_cosmic_facts_text,
    moon_phase_fraction,
    moon_phase_name,
    planetary_ages,
)

# --- moon_phase_fraction ---


def test_moon_phase_fraction_is_zero_at_reference_date():
    assert moon_phase_fraction(MOON_REFERENCE_DATE) == pytest.approx(0.0, abs=1e-6)


def test_moon_phase_fraction_is_half_after_half_synodic_month():
    day = MOON_REFERENCE_DATE + timedelta(days=15)
    assert moon_phase_fraction(day) == pytest.approx(0.5, abs=0.05)


# --- moon_phase_name ---


@pytest.mark.parametrize(
    ("fraction", "expected"),
    [
        (0.0, "новолуние"),
        (0.124, "новолуние"),
        (0.125, "растущий серп"),
        (0.25, "первая четверть"),
        (0.375, "растущая луна"),
        (0.5, "полнолуние"),
        (0.625, "убывающая луна"),
        (0.75, "последняя четверть"),
        (0.875, "убывающий серп"),
        (0.999, "убывающий серп"),
    ],
)
def test_moon_phase_name_boundaries(fraction: float, expected: str):
    assert moon_phase_name(fraction) == expected


# --- planetary_ages ---


def test_planetary_ages_exact_multiples_of_each_period():
    birthday = date(2000, 1, 1)
    mercury_today = birthday + timedelta(days=math.ceil(87.97 * 2))
    venus_today = birthday + timedelta(days=math.ceil(224.7 * 3))
    mars_today = birthday + timedelta(days=math.ceil(686.98 * 1))

    mercury_age = next(age for age in planetary_ages(birthday, mercury_today) if age.planet_name == "Меркурий")
    venus_age = next(age for age in planetary_ages(birthday, venus_today) if age.planet_name == "Венера")
    mars_age = next(age for age in planetary_ages(birthday, mars_today) if age.planet_name == "Марс")

    assert mercury_age.age_years == 2
    assert venus_age.age_years == 3
    assert mars_age.age_years == 1


def test_planetary_ages_returns_fixed_order():
    ages = planetary_ages(date(2000, 1, 1), date(2020, 1, 1))
    assert [age.planet_name for age in ages] == ["Меркурий", "Венера", "Марс"]


# --- build_cosmic_facts_text ---


def test_build_cosmic_facts_text_contains_all_planets_and_moon_phase():
    text = build_cosmic_facts_text(date(2000, 1, 1), date(2020, 1, 1))

    assert "Меркурий" in text
    assert "Венера" in text
    assert "Марс" in text
    assert "меркурианских" in text
    assert "венерианских" in text
    assert "марсианских" in text
    assert moon_phase_name(moon_phase_fraction(date(2020, 1, 1))) in text
