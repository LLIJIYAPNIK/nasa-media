from datetime import date, datetime

import pytest

from application.web.homepage_detail_query import GetHomepageDetail, UnknownHomepageDetailKind
from domain.digest.value_objects import AsteroidHighlight, EarthEventHighlight, SpaceWeatherHighlight
from infrastructure.nasa.apod_client import ApodData
from tests.application.fakes import (
    FakeApodRawClient,
    FakeNaturalEventClient,
    FakeNearEarthObjectClient,
    FakeSpaceWeatherClient,
)

DAY = date(2024, 1, 1)


def _query(
    apod_client=None, space_weather_client=None, near_earth_object_client=None, natural_event_client=None
) -> GetHomepageDetail:
    return GetHomepageDetail(
        apod_client or FakeApodRawClient(raise_not_available=True),
        space_weather_client or FakeSpaceWeatherClient(),
        near_earth_object_client or FakeNearEarthObjectClient(),
        natural_event_client or FakeNaturalEventClient(),
    )


async def test_apod_detail_available():
    apod_data = ApodData(title="Title", explanation="Text", copyright="Jane", image_url="http://img")

    detail = await _query(apod_client=FakeApodRawClient(data=apod_data)).execute("apod", DAY)

    assert detail.available is True
    assert detail.apod_title == "Title"
    assert detail.apod_description == "Text"
    assert detail.apod_copyright == "Jane"
    assert detail.apod_image_url == "http://img"


async def test_apod_detail_unavailable_has_human_message():
    detail = await _query(apod_client=FakeApodRawClient(raise_not_available=True)).execute("apod", DAY)

    assert detail.available is False
    assert detail.message


async def test_asteroid_detail_available_includes_full_diameter_range_and_comparison():
    asteroid = AsteroidHighlight(
        name="2024 YR4",
        diameter_min_m=100.0,
        diameter_max_m=140.0,
        miss_distance_km=340000.0,
        miss_distance_lunar=0.9,
        is_hazardous=True,
    )

    detail = await _query(near_earth_object_client=FakeNearEarthObjectClient([asteroid])).execute("asteroid", DAY)

    assert detail.available is True
    assert detail.asteroid_name == "2024 YR4"
    assert detail.asteroid_diameter_min_m == 100.0
    assert detail.asteroid_diameter_max_m == 140.0
    assert detail.asteroid_size_comparison
    assert detail.asteroid_is_hazardous is True
    assert detail.asteroid_miss_distance_lunar == 0.9


async def test_asteroid_detail_unavailable_when_no_asteroids():
    detail = await _query().execute("asteroid", DAY)

    assert detail.available is False
    assert detail.message


async def test_space_weather_detail_available_includes_type_and_time():
    event = SpaceWeatherHighlight("GST", datetime(2024, 1, 1, 10))

    detail = await _query(space_weather_client=FakeSpaceWeatherClient([event])).execute("space-weather", DAY)

    assert detail.available is True
    assert detail.space_weather_type == "GST"
    assert detail.space_weather_label == "Геомагнитная буря"
    assert detail.space_weather_issued_at == datetime(2024, 1, 1, 10).isoformat()


async def test_space_weather_detail_unavailable_when_calm():
    detail = await _query().execute("space-weather", DAY)

    assert detail.available is False
    assert detail.message


async def test_earth_event_detail_available():
    event = EarthEventHighlight("Tropical Storm", "Severe Storms", datetime(2024, 1, 1))

    detail = await _query(natural_event_client=FakeNaturalEventClient([event])).execute("earth-event", DAY)

    assert detail.available is True
    assert detail.earth_event_title == "Tropical Storm"
    assert detail.earth_event_category == "Severe Storms"
    assert detail.earth_event_date == datetime(2024, 1, 1).isoformat()


async def test_earth_event_detail_unavailable_when_no_events():
    detail = await _query().execute("earth-event", DAY)

    assert detail.available is False
    assert detail.message


async def test_unknown_kind_raises():
    with pytest.raises(UnknownHomepageDetailKind):
        await _query().execute("weekly-highlights", DAY)
