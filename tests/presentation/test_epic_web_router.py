from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from application.web.epic_page_query import EpicTexture, GetEpicPageSnapshot
from infrastructure.web.epic_snapshot_cache import EpicPageSnapshotCache
from infrastructure.web.epic_texture_cache import EpicTextureFileCache
from presentation.web.routers.epic_router import build_epic_router
from presentation.web.routers.homepage_router import NAV_ITEMS
from tests.application.fakes import FakeEpicAvailability, FakeEpicTextureBuilder
from tests.presentation.asgi_test_client import asgi_get

WEB_DIR = Path(__file__).resolve().parents[2] / "presentation" / "web"


def _build_app(availability=None, texture_builder=None, texture_cache=None):
    availability = availability or FakeEpicAvailability([date(2024, 1, 1)])
    texture_builder = texture_builder or FakeEpicTextureBuilder(
        EpicTexture(cache_key="2024-01-01", centroid_lat=12.5, centroid_lon=-45.25)
    )
    texture_cache = texture_cache or EpicTextureFileCache()

    get_snapshot = GetEpicPageSnapshot(availability, texture_builder)
    snapshot_cache = EpicPageSnapshotCache()

    app = FastAPI()
    templates = Jinja2Templates(directory=WEB_DIR / "templates")
    templates.env.globals["nav_items"] = NAV_ITEMS
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    app.include_router(build_epic_router(templates, get_snapshot, snapshot_cache, texture_cache))
    return app


async def test_epic_page_returns_200_with_centroid_and_texture_attributes():
    app = _build_app()

    response = await asgi_get(app, "/epic")

    assert response.status_code == 200
    assert 'id="epic-mount"' in response.text
    assert 'data-centroid-lat="12.5"' in response.text
    assert 'data-centroid-lon="-45.25"' in response.text
    assert 'data-texture-url="/api/epic/textures/2024-01-01.jpg"' in response.text


async def test_epic_page_renders_placeholder_when_no_known_dates():
    app = _build_app(availability=FakeEpicAvailability([]))

    response = await asgi_get(app, "/epic")

    assert response.status_code == 200
    assert "в разработке" in response.text
    assert "EPIC" in response.text
    assert 'id="epic-mount"' not in response.text


async def test_epic_page_renders_placeholder_when_texture_builder_returns_none():
    app = _build_app(texture_builder=FakeEpicTextureBuilder(None))

    response = await asgi_get(app, "/epic")

    assert response.status_code == 200
    assert "в разработке" in response.text


async def test_epic_texture_route_serves_cached_bytes(tmp_path):
    texture_cache = EpicTextureFileCache(directory=tmp_path)
    await texture_cache.set("2024-01-01", b"fake-jpeg-bytes")
    app = _build_app(texture_cache=texture_cache)

    response = await asgi_get(app, "/api/epic/textures/2024-01-01.jpg")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.body == b"fake-jpeg-bytes"


async def test_epic_texture_route_404_when_not_cached(tmp_path):
    app = _build_app(texture_cache=EpicTextureFileCache(directory=tmp_path))

    response = await asgi_get(app, "/api/epic/textures/2099-01-01.jpg")

    assert response.status_code == 404
