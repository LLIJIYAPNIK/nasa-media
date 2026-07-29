from datetime import date, datetime, timedelta

import pytest

from application.web.homepage_detail_query import GetHomepageDetail, SpaceWeatherEventItem, UnknownHomepageDetailKind
from domain.digest.speed_comparison import compare_speed_to_familiar_reference
from domain.digest.value_objects import AsteroidHighlight, EarthEventHighlight, EventSource, SpaceWeatherHighlight
from infrastructure.nasa.apod_client import ApodData
from tests.application.fakes import (
    FakeApodRawClient,
    FakeEventMapBuilder,
    FakeNaturalEventClient,
    FakeNearEarthObjectClient,
    FakeSpaceWeatherClient,
)

DAY = date(2024, 1, 1)


def _query(
    apod_client=None,
    space_weather_client=None,
    near_earth_object_client=None,
    natural_event_client=None,
    event_map_builder=None,
) -> GetHomepageDetail:
    return GetHomepageDetail(
        apod_client or FakeApodRawClient(raise_not_available=True),
        space_weather_client or FakeSpaceWeatherClient(),
        near_earth_object_client or FakeNearEarthObjectClient(),
        natural_event_client or FakeNaturalEventClient(),
        event_map_builder or FakeEventMapBuilder(),
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


async def test_apod_detail_falls_back_to_previous_day_when_today_not_published_yet():
    apod_data = ApodData(title="Title", explanation="Text", copyright="Jane", image_url="http://img")
    apod_client = FakeApodRawClient(data=apod_data, unavailable_days=[DAY])

    detail = await _query(apod_client=apod_client).execute("apod", DAY)

    assert detail.available is True
    assert detail.apod_title == "Title"
    assert detail.apod_image_url == "http://img"
    assert detail.message
    assert apod_client.calls == [DAY, DAY - timedelta(days=1)]


async def test_apod_detail_unavailable_when_today_and_previous_day_both_missing():
    detail = await _query(apod_client=FakeApodRawClient(raise_not_available=True)).execute("apod", DAY)

    assert detail.available is False
    assert detail.apod_title is None


async def test_asteroid_detail_available_includes_full_diameter_range_and_comparison():
    asteroid = AsteroidHighlight(
        name="2024 YR4",
        diameter_min_m=100.0,
        diameter_max_m=140.0,
        miss_distance_km=340000.0,
        miss_distance_lunar=0.9,
        is_hazardous=True,
        miss_distance_au=0.0023,
        miss_distance_miles=211_266.6,
        velocity_km_s=12.5,
        velocity_km_h=45_000.0,
        close_approach_time=datetime(2024, 1, 1, 10),
        jpl_url="https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=2024+YR4",
        is_sentry_object=True,
    )

    detail = await _query(near_earth_object_client=FakeNearEarthObjectClient([asteroid])).execute("asteroid", DAY)

    assert detail.available is True
    assert detail.asteroid_name == "2024 YR4"
    assert detail.asteroid_diameter_min_m == 100.0
    assert detail.asteroid_diameter_max_m == 140.0
    assert detail.asteroid_size_comparison
    assert detail.asteroid_is_hazardous is True
    assert detail.asteroid_miss_distance_lunar == 0.9
    assert detail.asteroid_miss_distance_km == 340000.0
    assert detail.asteroid_miss_distance_au == 0.0023
    assert detail.asteroid_miss_distance_miles == 211_266.6
    assert detail.asteroid_velocity_km_s == 12.5
    assert detail.asteroid_velocity_km_h == 45_000.0
    assert detail.asteroid_speed_comparison == compare_speed_to_familiar_reference(12.5)
    assert detail.asteroid_close_approach_time == datetime(2024, 1, 1, 10).isoformat()
    assert detail.asteroid_jpl_url == "https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=2024+YR4"
    assert detail.asteroid_is_sentry_object is True


async def test_asteroid_detail_unavailable_when_no_asteroids():
    detail = await _query().execute("asteroid", DAY)

    assert detail.available is False
    assert detail.message


async def test_space_weather_detail_available_includes_summary_type_and_time():
    event = SpaceWeatherHighlight("GST", datetime(2024, 1, 1, 10))

    detail = await _query(space_weather_client=FakeSpaceWeatherClient([event])).execute("space-weather", DAY)

    assert detail.available is True
    assert detail.space_weather_summary_type == "GST"
    assert detail.space_weather_summary_label == "Геомагнитная буря"
    assert detail.space_weather_summary_issued_at == datetime(2024, 1, 1, 10).isoformat()
    assert detail.space_weather_events == [
        SpaceWeatherEventItem(type="GST", label="Геомагнитная буря", issued_at=datetime(2024, 1, 1, 10).isoformat())
    ]


async def test_space_weather_detail_lists_all_events_sorted_by_time():
    early = SpaceWeatherHighlight("FLR", datetime(2024, 1, 1, 6))
    late = SpaceWeatherHighlight("GST", datetime(2024, 1, 1, 18))

    detail = await _query(space_weather_client=FakeSpaceWeatherClient([late, early])).execute("space-weather", DAY)

    assert detail.available is True
    assert [item.type for item in detail.space_weather_events] == ["FLR", "GST"]
    # GST (rank 0) beats FLR (rank 1) regardless of order in the input list.
    assert detail.space_weather_summary_type == "GST"


async def test_space_weather_detail_available_but_calm_when_no_significant_event():
    event = SpaceWeatherHighlight("Report", datetime(2024, 1, 1, 6))

    detail = await _query(space_weather_client=FakeSpaceWeatherClient([event])).execute("space-weather", DAY)

    assert detail.available is True
    assert detail.space_weather_events == [
        SpaceWeatherEventItem(type="Report", label="Еженедельный отчёт", issued_at=datetime(2024, 1, 1, 6).isoformat())
    ]
    assert detail.space_weather_summary_type is None
    assert detail.space_weather_summary_label == "Спокойно"
    assert detail.space_weather_summary_issued_at is None


async def test_space_weather_detail_unavailable_when_no_events_at_all():
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


async def test_earth_event_detail_includes_full_eonet_fields():
    event = EarthEventHighlight(
        title="Wildfire Fairpoint",
        category="Wildfires",
        event_date=datetime(2024, 1, 1),
        id="EONET_21829",
        categories=["Wildfires"],
        description="3 Miles W from Fairpoint, SD",
        closed_at=None,
        link="https://eonet.gsfc.nasa.gov/api/v3/events/EONET_21829",
        sources=[EventSource(label="IRWIN", url="https://irwin.doi.gov/observer/incidents/1")],
        magnitude_value=510.0,
        magnitude_unit="acres",
    )
    map_builder = FakeEventMapBuilder(cache_key="EONET_21829_2024-01-01")

    detail = await _query(natural_event_client=FakeNaturalEventClient([event]), event_map_builder=map_builder).execute(
        "earth-event", DAY
    )

    assert detail.available is True
    assert detail.earth_event_categories == ["Wildfires"]
    assert detail.earth_event_description == "3 Miles W from Fairpoint, SD"
    assert detail.earth_event_closed_at is None
    assert detail.earth_event_magnitude_value == 510.0
    assert detail.earth_event_magnitude_unit == "acres"
    assert detail.earth_event_sources == [EventSource(label="IRWIN", url="https://irwin.doi.gov/observer/incidents/1")]
    assert detail.earth_event_link == "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_21829"
    assert detail.earth_event_map_url == "/api/homepage/earth-event-map/EONET_21829_2024-01-01.png"
    assert map_builder.built_for == [event]


async def test_earth_event_detail_closed_status():
    event = EarthEventHighlight(
        title="Closed storm", category="Severe Storms", event_date=datetime(2024, 1, 1), closed_at=datetime(2024, 1, 5)
    )

    detail = await _query(natural_event_client=FakeNaturalEventClient([event])).execute("earth-event", DAY)

    assert detail.earth_event_closed_at == datetime(2024, 1, 5).isoformat()


async def test_earth_event_detail_map_url_absent_when_builder_returns_none():
    event = EarthEventHighlight("Tropical Storm", "Severe Storms", datetime(2024, 1, 1))

    detail = await _query(
        natural_event_client=FakeNaturalEventClient([event]), event_map_builder=FakeEventMapBuilder(cache_key=None)
    ).execute("earth-event", DAY)

    assert detail.earth_event_map_url is None


async def test_earth_event_detail_unavailable_when_no_events():
    detail = await _query().execute("earth-event", DAY)

    assert detail.available is False
    assert detail.message


async def test_unknown_kind_raises():
    with pytest.raises(UnknownHomepageDetailKind):
        await _query().execute("weekly-highlights", DAY)
