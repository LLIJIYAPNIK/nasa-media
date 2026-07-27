from datetime import date

from application.media.deliver_media import DeliverMediaForDate
from application.media.ports import CachedMessageRef


class RecordingAdapter:
    def __init__(self, cached: CachedMessageRef | None) -> None:
        self.cached = cached
        self.fetch_and_cache_calls = 0
        self.forwarded: list[tuple[CachedMessageRef, int]] = []

    async def get_cached(self, day):
        return self.cached

    async def fetch_and_cache(self, day):
        self.fetch_and_cache_calls += 1
        self.cached = CachedMessageRef(message_id=99)
        return self.cached

    async def forward_cached(self, ref, chat_id):
        self.forwarded.append((ref, chat_id))


async def test_delivers_cached_media_without_fetching():
    ref = CachedMessageRef(message_id=1)
    adapter = RecordingAdapter(cached=ref)
    use_case = DeliverMediaForDate(adapter)

    await use_case.execute(date(2024, 1, 1), chat_id=123)

    assert adapter.fetch_and_cache_calls == 0
    assert adapter.forwarded == [(ref, 123)]


async def test_fetches_and_caches_on_miss_then_forwards():
    adapter = RecordingAdapter(cached=None)
    use_case = DeliverMediaForDate(adapter)

    await use_case.execute(date(2024, 1, 1), chat_id=123)

    assert adapter.fetch_and_cache_calls == 1
    assert adapter.forwarded == [(CachedMessageRef(message_id=99), 123)]
