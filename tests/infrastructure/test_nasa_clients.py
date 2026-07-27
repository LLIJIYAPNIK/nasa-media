from datetime import date
from io import BytesIO

import pytest
from PIL import Image

from domain.media.exceptions import MediaNotAvailable
from infrastructure.nasa.apod_client import ApodProvider
from infrastructure.nasa.epic_availability_client import EpicAvailabilityClient
from infrastructure.nasa.epic_client import EPIC_ARCHIVE_BASE_URL, EpicProvider
from tests.infrastructure.fake_aiohttp import FakeClientSession, FakeResponse


def _fake_png_bytes(color: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


APOD_URL = "https://api.nasa.gov/planetary/apod"
EPIC_URL = "https://api.nasa.gov/EPIC/api/natural"


class FakeTranslator:
    async def translate_to_ru(self, text: str) -> str:
        return f"[ru] {text}"


async def test_apod_provider_builds_payload_with_translated_caption():
    session = FakeClientSession(
        {
            f"{APOD_URL}?date=2024-01-01&api_key=key": FakeResponse(
                json_data={"media_type": "image", "url": "http://img", "title": "Title", "explanation": "Text"}
            )
        }
    )
    provider = ApodProvider(session, "key", APOD_URL, FakeTranslator())

    payload = await provider.fetch(date(2024, 1, 1))

    assert payload.image_url == "http://img"
    assert "[ru] Title" in payload.caption
    assert "[ru] Text" in payload.caption


async def test_apod_provider_appends_copyright_attribution_when_present():
    session = FakeClientSession(
        {
            f"{APOD_URL}?date=2024-01-01&api_key=key": FakeResponse(
                json_data={
                    "media_type": "image",
                    "url": "http://img",
                    "title": "Title",
                    "explanation": "Text",
                    "copyright": "Jane Photographer",
                }
            )
        }
    )
    provider = ApodProvider(session, "key", APOD_URL, FakeTranslator())

    payload = await provider.fetch(date(2024, 1, 1))

    assert payload.caption.endswith("© Jane Photographer")


async def test_apod_provider_prefers_hdurl_when_present():
    session = FakeClientSession(
        {
            f"{APOD_URL}?date=2024-01-01&api_key=key": FakeResponse(
                json_data={
                    "media_type": "image",
                    "url": "http://img",
                    "hdurl": "http://img-hd",
                    "title": "Title",
                    "explanation": "Text",
                }
            )
        }
    )
    provider = ApodProvider(session, "key", APOD_URL, FakeTranslator())

    payload = await provider.fetch(date(2024, 1, 1))

    assert payload.image_url == "http://img-hd"


async def test_apod_provider_raises_when_media_is_not_an_image():
    session = FakeClientSession(
        {
            f"{APOD_URL}?date=2024-01-01&api_key=key": FakeResponse(
                json_data={"media_type": "video", "url": "http://img"}
            )
        }
    )
    provider = ApodProvider(session, "key", APOD_URL, FakeTranslator())

    with pytest.raises(MediaNotAvailable):
        await provider.fetch(date(2024, 1, 1))


async def test_apod_provider_raises_when_nasa_has_no_data_for_date():
    session = FakeClientSession({f"{APOD_URL}?date=2024-01-01&api_key=key": FakeResponse(json_data={"code": 404})})
    provider = ApodProvider(session, "key", APOD_URL, FakeTranslator())

    with pytest.raises(MediaNotAvailable):
        await provider.fetch(date(2024, 1, 1))


async def test_epic_provider_builds_animation_from_every_returned_frame():
    day = date(2024, 1, 1)
    session = FakeClientSession(
        {
            f"{EPIC_URL}/date/2024-01-01?api_key=key": FakeResponse(
                json_data=[{"image": "frame1"}, {"image": "frame2"}]
            ),
            f"{EPIC_ARCHIVE_BASE_URL}/2024/01/01/png/frame1.png?api_key=key": FakeResponse(body=_fake_png_bytes("red")),
            f"{EPIC_ARCHIVE_BASE_URL}/2024/01/01/png/frame2.png?api_key=key": FakeResponse(
                body=_fake_png_bytes("blue")
            ),
        }
    )
    provider = EpicProvider(session, "key", EPIC_URL)

    payload = await provider.fetch(day)

    gif = Image.open(BytesIO(payload.gif_bytes))
    assert gif.format == "GIF"
    assert gif.n_frames == 2


async def test_epic_provider_raises_when_no_frames_returned():
    session = FakeClientSession({f"{EPIC_URL}/date/2024-01-01?api_key=key": FakeResponse(json_data=[])})
    provider = EpicProvider(session, "key", EPIC_URL)

    with pytest.raises(MediaNotAvailable):
        await provider.fetch(date(2024, 1, 1))


async def test_epic_availability_client_parses_and_sorts_dates():
    session = FakeClientSession(
        {
            f"{EPIC_URL}/all?api_key=key": FakeResponse(
                json_data=[{"date": "2024-01-02 00:00:00"}, {"date": "2024-01-01 00:00:00"}]
            )
        }
    )
    client = EpicAvailabilityClient(session, "key", EPIC_URL)

    dates = await client.fetch_known_dates()

    assert dates == [date(2024, 1, 1), date(2024, 1, 2)]
