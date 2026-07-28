from datetime import date, datetime

from application.digest.provider import DigestProvider
from application.media.ports import TextPayload
from domain.digest.value_objects import SpaceWeatherHighlight
from domain.media.entities import ApodEntry
from tests.application.fakes import (
    FakeApodRepository,
    FakeNaturalEventClient,
    FakeNearEarthObjectClient,
    FakeSpaceWeatherClient,
)

DAY = date(2024, 1, 1)


def _provider(
    space_weather_client=None, near_earth_object_client=None, natural_event_client=None, apod_repo=None
) -> DigestProvider:
    return DigestProvider(
        space_weather_client or FakeSpaceWeatherClient(),
        near_earth_object_client or FakeNearEarthObjectClient(),
        natural_event_client or FakeNaturalEventClient(),
        apod_repo or FakeApodRepository(),
    )


async def test_fetch_returns_text_payload():
    payload = await _provider().fetch(DAY)

    assert isinstance(payload, TextPayload)


async def test_fetch_includes_apod_line_when_apod_already_cached():
    apod_repo = FakeApodRepository()
    await apod_repo.save(ApodEntry(date=DAY, message_id=1))

    payload = await _provider(apod_repo=apod_repo).fetch(DAY)

    assert "APOD" in payload.text


async def test_fetch_omits_apod_line_when_apod_not_cached_yet():
    payload = await _provider().fetch(DAY)

    assert "APOD" not in payload.text


async def test_fetch_uses_significant_space_weather_in_text():
    space_weather_client = FakeSpaceWeatherClient([SpaceWeatherHighlight("GST", datetime(2024, 1, 1, 10))])

    payload = await _provider(space_weather_client=space_weather_client).fetch(DAY)

    assert "Геомагнитная буря" in payload.text


async def test_fetch_queries_all_sources_for_the_requested_day():
    space_weather_client = FakeSpaceWeatherClient()
    near_earth_object_client = FakeNearEarthObjectClient()
    natural_event_client = FakeNaturalEventClient()

    await _provider(space_weather_client, near_earth_object_client, natural_event_client).fetch(DAY)

    assert space_weather_client.calls == [DAY]
    assert near_earth_object_client.calls == [DAY]
    assert natural_event_client.calls == 1
