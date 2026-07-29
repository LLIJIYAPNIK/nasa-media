from infrastructure.web.epic_texture_cache import EpicTextureFileCache


async def test_epic_texture_cache_roundtrip(tmp_path):
    cache = EpicTextureFileCache(directory=tmp_path)

    assert await cache.get("2024-01-01") is None
    assert await cache.exists("2024-01-01") is False

    await cache.set("2024-01-01", b"jpeg-bytes")

    assert await cache.exists("2024-01-01") is True
    assert await cache.get("2024-01-01") == b"jpeg-bytes"


async def test_epic_texture_cache_rejects_unsafe_keys(tmp_path):
    cache = EpicTextureFileCache(directory=tmp_path)

    assert await cache.get("../../etc/passwd") is None
    assert await cache.exists("../../etc/passwd") is False

    for unsafe_key in ("../secret", "a/b", "a.b", ""):
        try:
            await cache.set(unsafe_key, b"data")
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {unsafe_key!r}")
