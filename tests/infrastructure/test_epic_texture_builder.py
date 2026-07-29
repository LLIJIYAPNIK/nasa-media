from datetime import date
from io import BytesIO

from PIL import Image

from infrastructure.nasa.epic_frames import EPIC_ARCHIVE_BASE_URL
from infrastructure.web.epic_texture_builder import NasaEpicTextureBuilder
from infrastructure.web.epic_texture_cache import EpicTextureFileCache
from tests.infrastructure.fake_aiohttp import FakeClientSession, FakeResponse

EPIC_URL = "https://api.nasa.gov/EPIC/api/natural"
DAY = date(2024, 1, 1)


def _fake_png_bytes(color: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


def _frame_json(image: str, lat: float = 10.0, lon: float = 20.0) -> dict:
    return {"image": image, "centroid_coordinates": {"lat": lat, "lon": lon}}


def _frame_url(image: str) -> str:
    return f"{EPIC_ARCHIVE_BASE_URL}/2024/01/01/png/{image}.png?api_key=key"


async def test_build_downloads_middle_frame_and_caches_it(tmp_path):
    session = FakeClientSession(
        {
            f"{EPIC_URL}/date/2024-01-01?api_key=key": FakeResponse(
                json_data=[_frame_json("frame1"), _frame_json("frame2", lat=5.0, lon=6.0), _frame_json("frame3")]
            ),
            _frame_url("frame2"): FakeResponse(body=_fake_png_bytes("red")),
        }
    )
    cache = EpicTextureFileCache(directory=tmp_path)
    builder = NasaEpicTextureBuilder(session, "key", EPIC_URL, cache)

    texture = await builder.build(DAY)

    assert texture is not None
    assert texture.cache_key == "2024-01-01"
    assert texture.centroid_lat == 5.0
    assert texture.centroid_lon == 6.0
    assert await cache.exists("2024-01-01") is True


async def test_build_does_not_redownload_frame_bytes_on_cache_hit(tmp_path):
    session = FakeClientSession(
        {
            f"{EPIC_URL}/date/2024-01-01?api_key=key": FakeResponse(json_data=[_frame_json("frame1")]),
            _frame_url("frame1"): FakeResponse(body=_fake_png_bytes("blue")),
        }
    )
    cache = EpicTextureFileCache(directory=tmp_path)
    builder = NasaEpicTextureBuilder(session, "key", EPIC_URL, cache)

    await builder.build(DAY)
    assert _frame_url("frame1") in session.requested_urls
    session.requested_urls.clear()

    await builder.build(DAY)

    assert _frame_url("frame1") not in session.requested_urls
    assert f"{EPIC_URL}/date/2024-01-01?api_key=key" in session.requested_urls


async def test_build_returns_none_when_no_frames_for_day(tmp_path):
    session = FakeClientSession({f"{EPIC_URL}/date/2024-01-01?api_key=key": FakeResponse(json_data=[])})
    builder = NasaEpicTextureBuilder(session, "key", EPIC_URL, EpicTextureFileCache(directory=tmp_path))

    texture = await builder.build(DAY)

    assert texture is None
