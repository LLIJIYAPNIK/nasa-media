from datetime import datetime
from io import BytesIO

import aiohttp
from PIL import Image

from domain.digest.value_objects import EventGeometryPoint
from infrastructure.web.event_map import MAP_HEIGHT, MAP_WIDTH, TILE_USER_AGENT, render_event_map
from tests.infrastructure.fake_aiohttp import AnyUrlClientSession, FailingClientSession


def fake_tile_bytes(color: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (256, 256), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


def _point(lon: float = -80.0, lat: float = 25.0) -> EventGeometryPoint:
    return EventGeometryPoint(lon=lon, lat=lat, date=datetime(2024, 1, 1))


async def test_render_event_map_returns_correctly_sized_png_with_marker():
    session = AnyUrlClientSession(fake_tile_bytes((10, 20, 30)))

    image_bytes = await render_event_map(session, _point())

    assert image_bytes is not None
    image = Image.open(BytesIO(image_bytes))
    assert image.format == "PNG"
    assert image.size == (MAP_WIDTH, MAP_HEIGHT)
    center_pixel = image.convert("RGB").getpixel((MAP_WIDTH // 2, MAP_HEIGHT // 2))
    assert center_pixel != (10, 20, 30)


async def test_render_event_map_sends_identifying_user_agent():
    session = AnyUrlClientSession(fake_tile_bytes((10, 20, 30)))

    await render_event_map(session, _point())

    assert session.last_headers == {"User-Agent": TILE_USER_AGENT}
    assert session.requested_urls


async def test_render_event_map_returns_none_when_all_tiles_fail():
    session = FailingClientSession(aiohttp.ClientConnectionError("boom"))

    image_bytes = await render_event_map(session, _point())

    assert image_bytes is None
