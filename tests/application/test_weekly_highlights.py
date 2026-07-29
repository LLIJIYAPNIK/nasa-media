from datetime import date, datetime
from io import BytesIO
from unittest.mock import AsyncMock, patch

from PIL import Image

from application.digest.weekly_provider import WeeklyHighlightsProvider
from application.media.ports import GeneratedImagePayload
from domain.digest.value_objects import AsteroidHighlight, SpaceWeatherHighlight
from tests.application.fakes import FakeNaturalEventClient, FakeNearEarthObjectClient, FakeSpaceWeatherClient

WEEK_START = date(2024, 1, 1)  # понедельник
WEEK_END = date(2024, 1, 7)


def _asteroid(name: str, diameter_max_m: float) -> AsteroidHighlight:
    return AsteroidHighlight(
        name=name,
        diameter_min_m=diameter_max_m / 2,
        diameter_max_m=diameter_max_m,
        miss_distance_km=100_000.0,
        miss_distance_lunar=0.26,
        is_hazardous=False,
        miss_distance_au=0.00067,
        miss_distance_miles=62_137.1,
        velocity_km_s=10.0,
        velocity_km_h=36_000.0,
        close_approach_time=datetime(2024, 1, 3, 12),
        jpl_url="https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/",
        is_sentry_object=False,
    )


def _provider(space_weather_client=None, near_earth_object_client=None, natural_event_client=None):
    return WeeklyHighlightsProvider(
        space_weather_client or FakeSpaceWeatherClient(),
        near_earth_object_client or FakeNearEarthObjectClient(),
        natural_event_client or FakeNaturalEventClient(),
    )


async def test_fetch_returns_generated_image_payload_with_valid_png():
    payload = await _provider().fetch(WEEK_START)

    assert isinstance(payload, GeneratedImagePayload)
    image = Image.open(BytesIO(payload.image_bytes))
    assert image.format == "PNG"


async def test_fetch_queries_the_full_week_range_not_a_single_day():
    space_weather_client = FakeSpaceWeatherClient()
    near_earth_object_client = FakeNearEarthObjectClient()

    await _provider(space_weather_client, near_earth_object_client).fetch(WEEK_START)

    assert space_weather_client.range_calls == [(WEEK_START, WEEK_END)]
    assert near_earth_object_client.range_calls == [(WEEK_START, WEEK_END)]


async def test_fetch_picks_the_largest_asteroid_of_the_range():
    near_earth_object_client = FakeNearEarthObjectClient([_asteroid("Small", 10), _asteroid("Huge", 900)])

    with patch("application.digest.weekly_provider.build_card", new=AsyncMock(return_value=b"png")) as mock_build:
        await _provider(near_earth_object_client=near_earth_object_client).fetch(WEEK_START)

    lines = mock_build.await_args.kwargs["lines"]
    assert any("Huge" in line for line in lines)
    assert not any("Small" in line for line in lines)


async def test_fetch_uses_significant_space_weather_of_the_range():
    space_weather_client = FakeSpaceWeatherClient([SpaceWeatherHighlight("GST", datetime(2024, 1, 3, 10))])

    with patch("application.digest.weekly_provider.build_card", new=AsyncMock(return_value=b"png")) as mock_build:
        await _provider(space_weather_client=space_weather_client).fetch(WEEK_START)

    lines = mock_build.await_args.kwargs["lines"]
    assert any("Геомагнитная буря" in line for line in lines)
