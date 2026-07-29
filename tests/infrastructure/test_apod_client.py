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


class FailingOnTextTranslator:
    def __init__(self, failing_text: str) -> None:
        self._failing_text = failing_text

    async def translate_to_ru(self, text: str) -> str:
        if text == self._failing_text:
            raise RuntimeError("перевод недоступен")
        return f"[ru] {text}"


async def test_fetch_for_range_returns_translated_items_for_each_date():
    session = FakeClientSession(
        {
            f"{APOD_URL}?start_date=2024-01-01&end_date=2024-01-02&api_key=key": FakeResponse(
                json_data=[
                    {
                        "date": "2024-01-01",
                        "media_type": "image",
                        "url": "http://img1",
                        "title": "Title1",
                        "explanation": "Text1",
                    },
                    {
                        "date": "2024-01-02",
                        "media_type": "image",
                        "url": "http://img2",
                        "hdurl": "http://img2-hd",
                        "title": "Title2",
                        "explanation": "Text2",
                        "copyright": "Jane",
                    },
                ]
            )
        }
    )
    client = ApodClient(session, "key", APOD_URL, FakeTranslator())

    items = await client.fetch_for_range(date(2024, 1, 1), date(2024, 1, 2))

    by_date = {item.date: item for item in items}
    assert by_date[date(2024, 1, 1)].title == "[ru] Title1"
    assert by_date[date(2024, 1, 1)].explanation == "[ru] Text1"
    assert by_date[date(2024, 1, 1)].copyright is None
    assert by_date[date(2024, 1, 1)].hdurl is None
    assert by_date[date(2024, 1, 2)].copyright == "Jane"
    assert by_date[date(2024, 1, 2)].hdurl == "http://img2-hd"


async def test_fetch_for_range_skips_video_days():
    session = FakeClientSession(
        {
            f"{APOD_URL}?start_date=2024-01-01&end_date=2024-01-02&api_key=key": FakeResponse(
                json_data=[
                    {"date": "2024-01-01", "media_type": "video", "url": "http://vid"},
                    {
                        "date": "2024-01-02",
                        "media_type": "image",
                        "url": "http://img2",
                        "title": "Title2",
                        "explanation": "Text2",
                    },
                ]
            )
        }
    )
    client = ApodClient(session, "key", APOD_URL, FakeTranslator())

    items = await client.fetch_for_range(date(2024, 1, 1), date(2024, 1, 2))

    assert [item.date for item in items] == [date(2024, 1, 2)]


async def test_fetch_for_range_skips_dates_missing_from_nasa_response():
    session = FakeClientSession(
        {
            f"{APOD_URL}?start_date=2024-01-01&end_date=2024-01-03&api_key=key": FakeResponse(
                json_data=[
                    {
                        "date": "2024-01-01",
                        "media_type": "image",
                        "url": "http://img1",
                        "title": "Title1",
                        "explanation": "Text1",
                    },
                    {
                        "date": "2024-01-03",
                        "media_type": "image",
                        "url": "http://img3",
                        "title": "Title3",
                        "explanation": "Text3",
                    },
                ]
            )
        }
    )
    client = ApodClient(session, "key", APOD_URL, FakeTranslator())

    items = await client.fetch_for_range(date(2024, 1, 1), date(2024, 1, 3))

    assert {item.date for item in items} == {date(2024, 1, 1), date(2024, 1, 3)}


async def test_fetch_for_range_skips_date_when_translation_fails():
    session = FakeClientSession(
        {
            f"{APOD_URL}?start_date=2024-01-01&end_date=2024-01-02&api_key=key": FakeResponse(
                json_data=[
                    {
                        "date": "2024-01-01",
                        "media_type": "image",
                        "url": "http://img1",
                        "title": "Broken",
                        "explanation": "Text1",
                    },
                    {
                        "date": "2024-01-02",
                        "media_type": "image",
                        "url": "http://img2",
                        "title": "Title2",
                        "explanation": "Text2",
                    },
                ]
            )
        }
    )
    client = ApodClient(session, "key", APOD_URL, FailingOnTextTranslator("Broken"))

    items = await client.fetch_for_range(date(2024, 1, 1), date(2024, 1, 2))

    assert [item.date for item in items] == [date(2024, 1, 2)]
