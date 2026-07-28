from datetime import date, datetime
from io import BytesIO
from unittest.mock import AsyncMock, patch

from PIL import Image

from application.digest.weekly_provider import WeeklyHighlightsProvider
from application.digest.weekly_source_adapter import WeeklyHighlightsSourceAdapter
from application.media.ports import CachedMessageRef, GeneratedImagePayload
from domain.digest.entities import WeeklyHighlightEntry
from domain.digest.value_objects import AsteroidHighlight, SpaceWeatherHighlight
from tests.application.fakes import (
    FakeAdminChatGateway,
    FakeApodProvider,
    FakeNaturalEventClient,
    FakeNearEarthObjectClient,
    FakeSpaceWeatherClient,
    FakeWeeklyHighlightsRepository,
)

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
    )


# --- WeeklyHighlightsProvider ---


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


# --- WeeklyHighlightsSourceAdapter (mirrors test_digest_source_adapter.py) ---


def _adapter(repo=None, gateway=None, provider=None) -> WeeklyHighlightsSourceAdapter:
    return WeeklyHighlightsSourceAdapter(
        provider or FakeApodProvider(payload=GeneratedImagePayload(image_bytes=b"png-bytes")),
        repo or FakeWeeklyHighlightsRepository(),
        gateway or FakeAdminChatGateway(),
    )


async def test_get_cached_returns_ref_on_hit():
    repo = FakeWeeklyHighlightsRepository()
    await repo.save(WeeklyHighlightEntry(week_start_date=WEEK_START, message_id=42))
    adapter = _adapter(repo=repo)

    cached = await adapter.get_cached(WEEK_START)

    assert cached == CachedMessageRef(message_id=42)


async def test_get_cached_is_a_miss_when_never_fetched():
    adapter = _adapter()

    assert await adapter.get_cached(WEEK_START) is None


async def test_fetch_and_cache_publishes_provider_payload_and_persists_entry():
    repo = FakeWeeklyHighlightsRepository()
    gateway = FakeAdminChatGateway(ref=CachedMessageRef(message_id=99))
    payload = GeneratedImagePayload(image_bytes=b"png-bytes-2")
    adapter = _adapter(repo=repo, gateway=gateway, provider=FakeApodProvider(payload=payload))

    ref = await adapter.fetch_and_cache(WEEK_START)

    assert ref == CachedMessageRef(message_id=99)
    assert gateway.published == [payload]
    assert await repo.get_by_date(WEEK_START) == WeeklyHighlightEntry(week_start_date=WEEK_START, message_id=99)


async def test_forward_cached_calls_gateway_forward_single():
    gateway = FakeAdminChatGateway()
    adapter = _adapter(gateway=gateway)

    await adapter.forward_cached(CachedMessageRef(message_id=7), chat_id=123)

    assert gateway.forwarded_single == [(7, 123)]
