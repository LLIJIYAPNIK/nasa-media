from datetime import date, datetime

from application.digest.source_adapter import DigestSourceAdapter
from application.media.ports import CachedMessageRef, TextPayload
from domain.digest.entities import DigestEntry
from domain.digest.value_objects import SpaceWeatherHighlight
from domain.media.entities import ApodEntry
from tests.application.fakes import (
    FakeAdminChatGateway,
    FakeApodRepository,
    FakeDigestRepository,
    FakeNaturalEventClient,
    FakeNearEarthObjectClient,
    FakeSpaceWeatherClient,
)

DAY = date(2024, 1, 1)


def _adapter(
    space_weather_client=None,
    near_earth_object_client=None,
    natural_event_client=None,
    apod_repo=None,
    digest_repo=None,
    gateway=None,
) -> DigestSourceAdapter:
    return DigestSourceAdapter(
        space_weather_client or FakeSpaceWeatherClient(),
        near_earth_object_client or FakeNearEarthObjectClient(),
        natural_event_client or FakeNaturalEventClient(),
        apod_repo or FakeApodRepository(),
        digest_repo or FakeDigestRepository(),
        gateway or FakeAdminChatGateway(),
    )


async def test_get_cached_returns_ref_on_hit():
    digest_repo = FakeDigestRepository()
    await digest_repo.save(DigestEntry(date=DAY, message_id=42))
    adapter = _adapter(digest_repo=digest_repo)

    cached = await adapter.get_cached(DAY)

    assert cached == CachedMessageRef(message_id=42)


async def test_get_cached_is_a_miss_when_never_fetched():
    adapter = _adapter()

    assert await adapter.get_cached(DAY) is None


async def test_fetch_and_cache_publishes_text_payload_and_persists_entry():
    digest_repo = FakeDigestRepository()
    gateway = FakeAdminChatGateway(ref=CachedMessageRef(message_id=99))
    adapter = _adapter(digest_repo=digest_repo, gateway=gateway)

    ref = await adapter.fetch_and_cache(DAY)

    assert ref == CachedMessageRef(message_id=99)
    assert len(gateway.published) == 1
    assert isinstance(gateway.published[0], TextPayload)
    assert await digest_repo.get_by_date(DAY) == DigestEntry(date=DAY, message_id=99)


async def test_fetch_and_cache_includes_apod_line_when_apod_already_cached():
    apod_repo = FakeApodRepository()
    await apod_repo.save(ApodEntry(date=DAY, message_id=1))
    gateway = FakeAdminChatGateway()
    adapter = _adapter(apod_repo=apod_repo, gateway=gateway)

    await adapter.fetch_and_cache(DAY)

    payload = gateway.published[0]
    assert isinstance(payload, TextPayload)
    assert "APOD" in payload.text


async def test_fetch_and_cache_omits_apod_line_when_apod_not_cached_yet():
    gateway = FakeAdminChatGateway()
    adapter = _adapter(gateway=gateway)

    await adapter.fetch_and_cache(DAY)

    payload = gateway.published[0]
    assert isinstance(payload, TextPayload)
    assert "APOD" not in payload.text


async def test_fetch_and_cache_uses_significant_space_weather_in_text():
    space_weather_client = FakeSpaceWeatherClient([SpaceWeatherHighlight("GST", datetime(2024, 1, 1, 10))])
    gateway = FakeAdminChatGateway()
    adapter = _adapter(space_weather_client=space_weather_client, gateway=gateway)

    await adapter.fetch_and_cache(DAY)

    payload = gateway.published[0]
    assert isinstance(payload, TextPayload)
    assert "Геомагнитная буря" in payload.text


async def test_forward_cached_calls_gateway_forward_single():
    gateway = FakeAdminChatGateway()
    adapter = _adapter(gateway=gateway)

    await adapter.forward_cached(CachedMessageRef(message_id=7), chat_id=123)

    assert gateway.forwarded_single == [(7, 123)]
