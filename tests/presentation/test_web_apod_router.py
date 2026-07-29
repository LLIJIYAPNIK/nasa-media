from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from application.web.apod_gallery_query import GetApodGalleryPage
from domain.media.apod_day_count import APOD_LAUNCH_DATE
from presentation.web.routers.apod_router import build_apod_router
from presentation.web.routers.homepage_router import NAV_ITEMS
from tests.application.fakes import FakeApodRangeClient, FakeApodWebCacheRepository
from tests.presentation.asgi_test_client import asgi_get

WEB_DIR = Path(__file__).resolve().parents[2] / "presentation" / "web"


def _build_app(range_client=None, repository=None, page_size=30):
    range_client = range_client or FakeApodRangeClient()
    repository = repository or FakeApodWebCacheRepository()
    get_gallery_page = GetApodGalleryPage(range_client, repository, page_size)

    app = FastAPI()
    templates = Jinja2Templates(directory=WEB_DIR / "templates")
    templates.env.globals["nav_items"] = NAV_ITEMS
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    app.include_router(build_apod_router(templates, get_gallery_page))
    return app


async def test_apod_page_returns_200_with_grid_and_sentinel():
    app = _build_app()

    response = await asgi_get(app, "/apod")

    assert response.status_code == 200
    assert 'id="apod-grid"' in response.text
    assert 'id="apod-grid-sentinel"' in response.text


async def test_apod_entries_endpoint_without_params_returns_items_and_next_cursor_shape():
    app = _build_app()

    response = await asgi_get(app, "/api/apod/entries")

    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "next_cursor" in body


async def test_apod_entries_endpoint_before_equal_to_launch_date_returns_empty_page():
    app = _build_app()

    response = await asgi_get(app, f"/api/apod/entries?before={APOD_LAUNCH_DATE.isoformat()}")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["next_cursor"] is None
