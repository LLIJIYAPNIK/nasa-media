from datetime import date

from domain.media.apod_day_count import APOD_LAUNCH_DATE, days_since_apod_launch


def test_launch_date_itself_is_day_zero():
    assert days_since_apod_launch(APOD_LAUNCH_DATE) == 0


def test_counts_days_since_launch():
    assert days_since_apod_launch(date(1995, 6, 17)) == 1
    assert days_since_apod_launch(date(1995, 7, 16)) == 30


def test_known_far_future_date():
    assert days_since_apod_launch(date(2024, 1, 1)) == (date(2024, 1, 1) - date(1995, 6, 16)).days
