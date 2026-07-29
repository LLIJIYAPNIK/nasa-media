from datetime import date

from application.web.epic_page_query import EpicTexture, GetEpicPageSnapshot
from tests.application.fakes import FakeEpicAvailability, FakeEpicTextureBuilder


def _query(availability=None, texture_builder=None) -> GetEpicPageSnapshot:
    return GetEpicPageSnapshot(availability or FakeEpicAvailability(), texture_builder or FakeEpicTextureBuilder())


async def test_returns_none_when_no_known_dates():
    snapshot = await _query(availability=FakeEpicAvailability([])).execute()

    assert snapshot is None


async def test_picks_the_latest_known_date_not_the_first():
    availability = FakeEpicAvailability([date(2024, 1, 1), date(2024, 1, 5), date(2024, 1, 3)])
    texture_builder = FakeEpicTextureBuilder(EpicTexture(cache_key="2024-01-05", centroid_lat=1.0, centroid_lon=2.0))

    await _query(availability, texture_builder).execute()

    assert texture_builder.built_for == [date(2024, 1, 5)]


async def test_returns_none_when_texture_builder_returns_none():
    texture_builder = FakeEpicTextureBuilder(None)

    snapshot = await _query(
        availability=FakeEpicAvailability([date(2024, 1, 1)]), texture_builder=texture_builder
    ).execute()

    assert snapshot is None


async def test_returns_snapshot_with_expected_fields_on_success():
    availability = FakeEpicAvailability([date(2024, 1, 1)])
    texture_builder = FakeEpicTextureBuilder(
        EpicTexture(cache_key="2024-01-01", centroid_lat=12.5, centroid_lon=-45.25)
    )

    snapshot = await _query(availability, texture_builder).execute()

    assert snapshot is not None
    assert snapshot.frame_date == date(2024, 1, 1)
    assert snapshot.centroid_lat == 12.5
    assert snapshot.centroid_lon == -45.25
    assert snapshot.texture_url == "/api/epic/textures/2024-01-01.jpg"
