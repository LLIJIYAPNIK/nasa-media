from datetime import date

from domain.users.birthday import is_birthday_today


def test_matches_same_month_and_day_regardless_of_year():
    assert is_birthday_today(date(1990, 3, 15), date(2026, 3, 15)) is True


def test_does_not_match_different_day():
    assert is_birthday_today(date(1990, 3, 15), date(2026, 3, 16)) is False


def test_does_not_match_different_month():
    assert is_birthday_today(date(1990, 3, 15), date(2026, 4, 15)) is False


def test_february_29_matches_february_29_in_leap_year():
    assert is_birthday_today(date(2000, 2, 29), date(2028, 2, 29)) is True


def test_february_29_matches_february_28_in_non_leap_year():
    assert is_birthday_today(date(2000, 2, 29), date(2026, 2, 28)) is True


def test_february_29_does_not_match_march_1_in_non_leap_year():
    assert is_birthday_today(date(2000, 2, 29), date(2026, 3, 1)) is False
