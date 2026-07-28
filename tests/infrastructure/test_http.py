from infrastructure.http import fetch_json
from tests.infrastructure.fake_aiohttp import FakeClientSession, FakeResponse

URL = "https://example.com/data"


async def test_fetch_json_tolerates_a_mislabeled_content_type():
    """Некоторые NASA-эндпоинты (EONET) иногда отдают валидный JSON с
    заголовком Content-Type: application/rss+xml — aiohttp по умолчанию
    кидает ContentTypeError на такой ответ, даже если тело корректное."""
    session = FakeClientSession({URL: FakeResponse(json_data={"ok": True})})

    result = await fetch_json(session, URL)

    assert result == {"ok": True}


async def test_fetch_json_skips_content_type_validation():
    response = FakeResponse(json_data={"ok": True})
    session = FakeClientSession({URL: response})

    await fetch_json(session, URL)

    assert response.json_content_type_args == [None]
