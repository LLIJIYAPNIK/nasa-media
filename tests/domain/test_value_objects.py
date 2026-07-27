from datetime import date

import pytest

from domain.media.value_objects import DateRange, InvalidMediaDate, ensure_within_bounds


def test_date_range_rejects_start_after_end():
    with pytest.raises(InvalidMediaDate):
        DateRange(start=date(2024, 1, 5), end=date(2024, 1, 1))


def test_date_range_rejects_more_than_five_days():
    with pytest.raises(InvalidMediaDate):
        DateRange(start=date(2024, 1, 1), end=date(2024, 1, 7))


def test_date_range_accepts_exactly_five_days():
    DateRange(start=date(2024, 1, 1), end=date(2024, 1, 6))


def test_date_range_iter_dates_is_inclusive():
    date_range = DateRange(start=date(2024, 1, 1), end=date(2024, 1, 3))

    assert list(date_range.iter_dates()) == [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]


def test_ensure_within_bounds_rejects_before_lower_bound():
    with pytest.raises(InvalidMediaDate):
        ensure_within_bounds(date(2000, 1, 1), lower_bound=date(2015, 6, 13), today=date(2024, 1, 1))


def test_ensure_within_bounds_rejects_future_date():
    with pytest.raises(InvalidMediaDate):
        ensure_within_bounds(date(2024, 1, 2), lower_bound=date(2015, 6, 13), today=date(2024, 1, 1))


def test_ensure_within_bounds_accepts_valid_date():
    ensure_within_bounds(date(2024, 1, 1), lower_bound=date(2015, 6, 13), today=date(2024, 1, 1))
