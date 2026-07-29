from infrastructure.web.event_map_cache import EventMapFileCache


async def test_event_map_cache_roundtrip(tmp_path):
    cache = EventMapFileCache(directory=tmp_path)

    assert await cache.get("EONET_1_2024-01-01") is None
    assert await cache.exists("EONET_1_2024-01-01") is False

    await cache.set("EONET_1_2024-01-01", b"png-bytes")

    assert await cache.exists("EONET_1_2024-01-01") is True
    assert await cache.get("EONET_1_2024-01-01") == b"png-bytes"


async def test_event_map_cache_rejects_unsafe_keys(tmp_path):
    cache = EventMapFileCache(directory=tmp_path)

    assert await cache.get("../../etc/passwd") is None
    assert await cache.exists("../../etc/passwd") is False

    for unsafe_key in ("../secret", "a/b", "a.b", ""):
        try:
            await cache.set(unsafe_key, b"data")
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {unsafe_key!r}")
