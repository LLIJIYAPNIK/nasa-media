from datetime import date

import pytest

from application.media.ports import AnimationPayload, CachedMessageRef, SinglePhotoPayload
from application.media.source_adapters import EpicSourceAdapter, GenericSourceAdapter
from domain.digest.entities import WeeklyHighlightEntry
from domain.media.entities import ApodEntry
from domain.media.exceptions import MediaNotAvailable
from tests.application.fakes import (
    FakeAdminChatGateway,
    FakeApodProvider,
    FakeApodRepository,
    FakeEpicRepository,
    FakeWeeklyHighlightsRepository,
)


def _apod_adapter(repo=None, gateway=None, provider=None) -> GenericSourceAdapter[ApodEntry]:
    return GenericSourceAdapter(
        provider or FakeApodProvider(),
        repo or FakeApodRepository(),
        gateway or FakeAdminChatGateway(),
        lambda day, message_id: ApodEntry(day, message_id),
    )


async def test_generic_adapter_returns_cached_ref_on_hit():
    repo = FakeApodRepository()
    day = date(2024, 1, 1)
    await repo.save(ApodEntry(date=day, message_id=42))
    adapter = _apod_adapter(repo=repo)

    cached = await adapter.get_cached(day)

    assert cached == CachedMessageRef(message_id=42)


async def test_generic_adapter_is_a_cache_miss_when_never_fetched():
    adapter = _apod_adapter()

    assert await adapter.get_cached(date(2024, 1, 1)) is None


async def test_generic_adapter_fetches_publishes_and_persists_on_miss():
    repo = FakeApodRepository()
    day = date(2024, 1, 1)
    payload = SinglePhotoPayload(image_url="http://example.com/x.jpg", caption="caption")
    gateway = FakeAdminChatGateway(ref=CachedMessageRef(message_id=99))
    adapter = _apod_adapter(repo=repo, gateway=gateway, provider=FakeApodProvider(payload=payload))

    ref = await adapter.fetch_and_cache(day)

    assert ref == CachedMessageRef(message_id=99)
    assert gateway.published == [payload]
    assert await repo.get_by_date(day) == ApodEntry(date=day, message_id=99)


async def test_generic_adapter_forwards_via_gateway():
    gateway = FakeAdminChatGateway()
    adapter = _apod_adapter(gateway=gateway)

    await adapter.forward_cached(CachedMessageRef(message_id=7), chat_id=123)

    assert gateway.forwarded_single == [(7, 123)]


async def test_generic_adapter_make_entry_works_with_a_differently_shaped_entry():
    """Прогон с WeeklyHighlightEntry (поле week_start_date, не date) —
    доказывает, что GenericSourceAdapter не завязан на конкретное имя поля
    даты в Entry, только на make_entry(day, message_id)."""
    repo = FakeWeeklyHighlightsRepository()
    week_start_date = date(2024, 1, 1)
    gateway = FakeAdminChatGateway(ref=CachedMessageRef(message_id=11))
    adapter = GenericSourceAdapter(
        FakeApodProvider(payload=SinglePhotoPayload(image_url="http://x", caption="c")),
        repo,
        gateway,
        lambda day, message_id: WeeklyHighlightEntry(day, message_id),
    )

    await adapter.fetch_and_cache(week_start_date)

    assert await repo.get_by_date(week_start_date) == WeeklyHighlightEntry(
        week_start_date=week_start_date, message_id=11
    )


async def test_epic_adapter_raises_when_date_unknown_to_nasa():
    adapter = EpicSourceAdapter(FakeApodProvider(), FakeEpicRepository(), FakeAdminChatGateway())

    with pytest.raises(MediaNotAvailable):
        await adapter.get_cached(date(2024, 1, 1))


async def test_epic_adapter_returns_none_when_known_but_not_yet_cached():
    repo = FakeEpicRepository()
    day = date(2024, 1, 1)
    await repo.ensure_known_dates([day])
    adapter = EpicSourceAdapter(FakeApodProvider(), repo, FakeAdminChatGateway())

    assert await adapter.get_cached(day) is None


async def test_epic_adapter_fetches_and_caches_gif():
    repo = FakeEpicRepository()
    day = date(2024, 1, 1)
    await repo.ensure_known_dates([day])
    gateway = FakeAdminChatGateway(ref=CachedMessageRef(message_id=55))
    payload = AnimationPayload(gif_bytes=b"gif-bytes")
    adapter = EpicSourceAdapter(FakeApodProvider(payload=payload), repo, gateway)

    ref = await adapter.fetch_and_cache(day)

    assert ref == CachedMessageRef(message_id=55)
    saved = await repo.get_by_date(day)
    assert saved is not None
    assert saved.gif_message_id == 55
    assert saved.is_cached is True


async def test_epic_adapter_forwards_via_gateway():
    gateway = FakeAdminChatGateway()
    adapter = EpicSourceAdapter(FakeApodProvider(), FakeEpicRepository(), gateway)

    await adapter.forward_cached(CachedMessageRef(message_id=55), chat_id=123)

    assert gateway.forwarded_single == [(55, 123)]
