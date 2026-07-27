from datetime import date

import pytest

from application.media.ports import CachedMessageRef, PhotoGroupPayload, SinglePhotoPayload
from application.media.source_adapters import ApodSourceAdapter, EpicSourceAdapter
from domain.media.entities import ApodEntry
from domain.media.exceptions import MediaNotAvailable
from tests.application.fakes import FakeAdminChatGateway, FakeApodProvider, FakeApodRepository, FakeEpicRepository


async def test_apod_adapter_returns_cached_ref_on_hit():
    repo = FakeApodRepository()
    day = date(2024, 1, 1)
    await repo.save(ApodEntry(date=day, message_id=42))
    adapter = ApodSourceAdapter(FakeApodProvider(), repo, FakeAdminChatGateway())

    cached = await adapter.get_cached(day)

    assert cached == CachedMessageRef(message_id=42)


async def test_apod_adapter_is_a_cache_miss_when_never_fetched():
    adapter = ApodSourceAdapter(FakeApodProvider(), FakeApodRepository(), FakeAdminChatGateway())

    assert await adapter.get_cached(date(2024, 1, 1)) is None


async def test_apod_adapter_fetches_publishes_and_persists_on_miss():
    repo = FakeApodRepository()
    day = date(2024, 1, 1)
    payload = SinglePhotoPayload(image_url="http://example.com/x.jpg", caption="caption")
    gateway = FakeAdminChatGateway(ref=CachedMessageRef(message_id=99))
    adapter = ApodSourceAdapter(FakeApodProvider(payload=payload), repo, gateway)

    ref = await adapter.fetch_and_cache(day)

    assert ref == CachedMessageRef(message_id=99)
    assert gateway.published == [payload]
    assert await repo.get_by_date(day) == ApodEntry(date=day, message_id=99)


async def test_apod_adapter_forwards_via_gateway():
    gateway = FakeAdminChatGateway()
    adapter = ApodSourceAdapter(FakeApodProvider(), FakeApodRepository(), gateway)

    await adapter.forward_cached(CachedMessageRef(message_id=7), chat_id=123)

    assert gateway.forwarded_single == [(7, 123)]


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


async def test_epic_adapter_fetches_and_caches_frames():
    repo = FakeEpicRepository()
    day = date(2024, 1, 1)
    await repo.ensure_known_dates([day])
    gateway = FakeAdminChatGateway(ref=CachedMessageRef(frame_file_ids=("a", "b")))
    payload = PhotoGroupPayload(images=[b"1", b"2"])
    adapter = EpicSourceAdapter(FakeApodProvider(payload=payload), repo, gateway)

    ref = await adapter.fetch_and_cache(day)

    assert ref.frame_file_ids == ("a", "b")
    saved = await repo.get_by_date(day)
    assert [frame.telegram_file_id for frame in saved.frames] == ["a", "b"]
    assert saved.is_cached is True


async def test_epic_adapter_forwards_group_via_gateway():
    gateway = FakeAdminChatGateway()
    adapter = EpicSourceAdapter(FakeApodProvider(), FakeEpicRepository(), gateway)

    await adapter.forward_cached(CachedMessageRef(frame_file_ids=("a", "b")), chat_id=123)

    assert gateway.forwarded_group == [(("a", "b"), 123)]
