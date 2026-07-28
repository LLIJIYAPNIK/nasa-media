from datetime import date

from application.digest.source_adapter import DigestSourceAdapter
from application.media.ports import CachedMessageRef, TextPayload
from domain.digest.entities import DigestEntry
from tests.application.fakes import FakeAdminChatGateway, FakeApodProvider, FakeDigestRepository

DAY = date(2024, 1, 1)


def _adapter(digest_repo=None, gateway=None, provider=None) -> DigestSourceAdapter:
    return DigestSourceAdapter(
        provider or FakeApodProvider(payload=TextPayload(text="сводка")),
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


async def test_fetch_and_cache_publishes_provider_payload_and_persists_entry():
    digest_repo = FakeDigestRepository()
    gateway = FakeAdminChatGateway(ref=CachedMessageRef(message_id=99))
    payload = TextPayload(text="сводка дня")
    adapter = _adapter(digest_repo=digest_repo, gateway=gateway, provider=FakeApodProvider(payload=payload))

    ref = await adapter.fetch_and_cache(DAY)

    assert ref == CachedMessageRef(message_id=99)
    assert gateway.published == [payload]
    assert await digest_repo.get_by_date(DAY) == DigestEntry(date=DAY, message_id=99)


async def test_forward_cached_calls_gateway_forward_single():
    gateway = FakeAdminChatGateway()
    adapter = _adapter(gateway=gateway)

    await adapter.forward_cached(CachedMessageRef(message_id=7), chat_id=123)

    assert gateway.forwarded_single == [(7, 123)]
