from datetime import date

import pytest

from domain.media.exceptions import MediaNotAvailable
from infrastructure.nasa.apod_client import ApodClient
from tests.infrastructure.fake_aiohttp import FakeClientSession, FakeResponse

APOD_URL = "https://api.nasa.gov/planetary/apod"


class FakeTranslator:
    async def translate_to_ru(self, text: str) -> str:
        return f"[ru] {text}"


async def test_fetch_raw_returns_translated_fields():
    session = FakeClientSession(
        {
            f"{APOD_URL}?date=2024-01-01&api_key=key": FakeResponse(
                json_data={"media_type": "image", "url": "http://img", "title": "Title", "explanation": "Text"}
            )
        }
    )
    client = ApodClient(session, "key", APOD_URL, FakeTranslator())

    data = await client.fetch_raw(date(2024, 1, 1))

    assert data.title == "[ru] Title"
    assert data.explanation == "[ru] Text"
    assert data.copyright is None
    assert data.image_url == "http://img"


async def test_fetch_raw_prefers_hdurl_when_present():
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
    client = ApodClient(session, "key", APOD_URL, FakeTranslator())

    data = await client.fetch_raw(date(2024, 1, 1))

    assert data.image_url == "http://img-hd"


async def test_fetch_raw_returns_copyright_when_present():
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
    client = ApodClient(session, "key", APOD_URL, FakeTranslator())

    data = await client.fetch_raw(date(2024, 1, 1))

    assert data.copyright == "Jane Photographer"


async def test_fetch_raw_raises_when_media_is_not_an_image():
    session = FakeClientSession(
        {
            f"{APOD_URL}?date=2024-01-01&api_key=key": FakeResponse(
                json_data={"media_type": "video", "url": "http://img"}
            )
        }
    )
    client = ApodClient(session, "key", APOD_URL, FakeTranslator())

    with pytest.raises(MediaNotAvailable):
        await client.fetch_raw(date(2024, 1, 1))


async def test_fetch_raw_raises_when_nasa_has_no_data_for_date():
    session = FakeClientSession({f"{APOD_URL}?date=2024-01-01&api_key=key": FakeResponse(json_data={"code": 404})})
    client = ApodClient(session, "key", APOD_URL, FakeTranslator())

    with pytest.raises(MediaNotAvailable):
        await client.fetch_raw(date(2024, 1, 1))
