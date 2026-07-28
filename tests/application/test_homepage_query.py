from datetime import date, datetime

from application.web.homepage_query import GetHomepageSnapshot
from domain.digest.value_objects import AsteroidHighlight, EarthEventHighlight, SpaceWeatherHighlight
from tests.application.fakes import FakeNaturalEventClient, FakeNearEarthObjectClient, FakeSpaceWeatherClient

DAY = date(2024, 1, 1)


def _query(space_weather_client=None, near_earth_object_client=None, natural_event_client=None) -> GetHomepageSnapshot:
    return GetHomepageSnapshot(
        space_weather_client or FakeSpaceWeatherClient(),
        near_earth_object_client or FakeNearEarthObjectClient(),
        natural_event_client or FakeNaturalEventClient(),
    )


async def test_apod_day_number_is_always_present():
    snapshot = await _query().execute(DAY)

    assert snapshot.apod_day_number == (DAY - date(1995, 6, 16)).days


async def test_snapshot_with_all_four_sources_populated():
    asteroid = AsteroidHighlight(
        name="2024 YR4",
        diameter_min_m=100.0,
        diameter_max_m=140.0,
        miss_distance_km=340000.0,
        miss_distance_lunar=0.9,
        is_hazardous=False,
    )
    space_weather = SpaceWeatherHighlight("GST", datetime(2024, 1, 1, 10))
    earth_event = EarthEventHighlight("Tropical Storm", "Severe Storms", datetime(2024, 1, 1))

    snapshot = await _query(
        space_weather_client=FakeSpaceWeatherClient([space_weather]),
        near_earth_object_client=FakeNearEarthObjectClient([asteroid]),
        natural_event_client=FakeNaturalEventClient([earth_event]),
    ).execute(DAY)

    assert snapshot.asteroid_name == "2024 YR4"
    assert snapshot.asteroid_miss_distance_lunar == 0.9
    assert snapshot.space_weather_label == "Геомагнитная буря"
    assert snapshot.earth_event_title == "Tropical Storm"
    assert snapshot.earth_event_category == "Severe Storms"


async def test_snapshot_with_all_four_sources_empty():
    snapshot = await _query().execute(DAY)

    assert snapshot.asteroid_name is None
    assert snapshot.asteroid_miss_distance_lunar is None
    assert snapshot.space_weather_label is None
    assert snapshot.earth_event_title is None
    assert snapshot.earth_event_category is None


async def test_snapshot_with_mixed_sources():
    asteroid = AsteroidHighlight(
        name="2024 YR4",
        diameter_min_m=100.0,
        diameter_max_m=140.0,
        miss_distance_km=340000.0,
        miss_distance_lunar=0.9,
        is_hazardous=False,
    )

    snapshot = await _query(near_earth_object_client=FakeNearEarthObjectClient([asteroid])).execute(DAY)

    assert snapshot.asteroid_name == "2024 YR4"
    assert snapshot.space_weather_label is None
    assert snapshot.earth_event_title is None


async def test_queries_all_sources_for_the_requested_day():
    space_weather_client = FakeSpaceWeatherClient()
    near_earth_object_client = FakeNearEarthObjectClient()
    natural_event_client = FakeNaturalEventClient()

    await _query(space_weather_client, near_earth_object_client, natural_event_client).execute(DAY)

    assert space_weather_client.calls == [DAY]
    assert near_earth_object_client.calls == [DAY]
    assert natural_event_client.calls == 1
