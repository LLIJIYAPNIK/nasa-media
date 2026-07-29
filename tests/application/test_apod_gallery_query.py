from datetime import date, timedelta

from application.web.apod_gallery_query import GetApodGalleryPage
from domain.media.apod_day_count import APOD_LAUNCH_DATE
from domain.media.entities import ApodWebEntry
from infrastructure.nasa.apod_client import ApodRangeItem
from tests.application.fakes import FakeApodRangeClient, FakeApodWebCacheRepository


def _entry(day: date, suffix: str = "") -> ApodWebEntry:
    return ApodWebEntry(
        date=day,
        title=f"Title{suffix}",
        explanation=f"Text{suffix}",
        copyright=None,
        image_url=f"http://img{suffix}",
        hdurl=None,
    )


def _range_item(day: date, suffix: str = "") -> ApodRangeItem:
    return ApodRangeItem(
        date=day,
        title=f"Title{suffix}",
        explanation=f"Text{suffix}",
        copyright=None,
        image_url=f"http://img{suffix}",
        hdurl=None,
    )


async def test_execute_uses_cache_without_hitting_apod_client_when_window_fully_cached():
    today = date(2024, 1, 10)
    window = [date(2024, 1, 10), date(2024, 1, 9), date(2024, 1, 8)]
    repository = FakeApodWebCacheRepository([_entry(day) for day in window])
    range_client = FakeApodRangeClient()
    query = GetApodGalleryPage(range_client, repository, page_size=3)

    page = await query.execute(before=None, today=today)

    assert range_client.range_calls == []
    assert [item.date for item in page.items] == ["2024-01-10", "2024-01-09", "2024-01-08"]


async def test_execute_fetches_only_missing_dates_and_merges_sorted_by_date_desc():
    today = date(2024, 1, 10)
    repository = FakeApodWebCacheRepository([_entry(date(2024, 1, 10), "10")])
    range_client = FakeApodRangeClient([_range_item(date(2024, 1, 9), "9"), _range_item(date(2024, 1, 8), "8")])
    query = GetApodGalleryPage(range_client, repository, page_size=3)

    page = await query.execute(before=None, today=today)

    assert range_client.range_calls == [(date(2024, 1, 8), date(2024, 1, 9))]
    assert [item.date for item in page.items] == ["2024-01-10", "2024-01-09", "2024-01-08"]
    assert len(repository.save_many_calls) == 1
    assert {entry.date for entry in repository.save_many_calls[0]} == {date(2024, 1, 9), date(2024, 1, 8)}


async def test_execute_next_cursor_is_none_when_window_reaches_launch_date():
    today = APOD_LAUNCH_DATE + timedelta(days=2)
    window = [APOD_LAUNCH_DATE, APOD_LAUNCH_DATE + timedelta(days=1), APOD_LAUNCH_DATE + timedelta(days=2)]
    repository = FakeApodWebCacheRepository([_entry(day) for day in window])
    query = GetApodGalleryPage(FakeApodRangeClient(), repository, page_size=5)

    page = await query.execute(before=None, today=today)

    assert page.next_cursor is None
    assert len(page.items) == 3


async def test_execute_next_cursor_is_oldest_date_when_window_does_not_reach_boundary():
    today = date(2024, 1, 10)
    window = [date(2024, 1, 10), date(2024, 1, 9), date(2024, 1, 8)]
    repository = FakeApodWebCacheRepository([_entry(day) for day in window])
    query = GetApodGalleryPage(FakeApodRangeClient(), repository, page_size=3)

    page = await query.execute(before=None, today=today)

    assert page.next_cursor == "2024-01-08"


async def test_execute_window_is_computed_from_today_when_before_is_not_passed():
    today = date(2024, 1, 10)
    repository = FakeApodWebCacheRepository([_entry(today)])
    query = GetApodGalleryPage(FakeApodRangeClient(), repository, page_size=1)

    page = await query.execute(before=None, today=today)

    assert [item.date for item in page.items] == ["2024-01-10"]


async def test_execute_window_is_computed_from_before_cursor():
    repository = FakeApodWebCacheRepository([_entry(date(2024, 1, 9))])
    query = GetApodGalleryPage(FakeApodRangeClient(), repository, page_size=1)

    page = await query.execute(before=date(2024, 1, 10), today=date(2024, 1, 10))

    assert [item.date for item in page.items] == ["2024-01-09"]


async def test_execute_returns_empty_page_when_before_is_at_or_before_launch_date():
    query = GetApodGalleryPage(FakeApodRangeClient(), FakeApodWebCacheRepository(), page_size=10)

    page = await query.execute(before=APOD_LAUNCH_DATE, today=date(2024, 1, 10))

    assert page.items == ()
    assert page.next_cursor is None
