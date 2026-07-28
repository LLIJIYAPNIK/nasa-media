from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from application.web.homepage_detail_query import GetHomepageDetail
from application.web.homepage_query import GetHomepageSnapshot
from infrastructure.web.snapshot_cache import SnapshotCache
from presentation.web.routers.homepage_router import NAV_ITEMS, PLACEHOLDER_SECTIONS, build_homepage_router
from tests.application.fakes import (
    FakeApodRawClient,
    FakeNaturalEventClient,
    FakeNearEarthObjectClient,
    FakeSpaceWeatherClient,
)
from tests.presentation.asgi_test_client import asgi_get

WEB_DIR = Path(__file__).resolve().parents[2] / "presentation" / "web"


def _build_app(apod_client=None, space_weather_client=None, near_earth_object_client=None, natural_event_client=None):
    space_weather_client = space_weather_client or FakeSpaceWeatherClient()
    near_earth_object_client = near_earth_object_client or FakeNearEarthObjectClient()
    natural_event_client = natural_event_client or FakeNaturalEventClient()
    apod_client = apod_client or FakeApodRawClient(raise_not_available=True)

    get_snapshot = GetHomepageSnapshot(space_weather_client, near_earth_object_client, natural_event_client)
    get_detail = GetHomepageDetail(apod_client, space_weather_client, near_earth_object_client, natural_event_client)
    cache = SnapshotCache()

    app = FastAPI()
    templates = Jinja2Templates(directory=WEB_DIR / "templates")
    templates.env.globals["nav_items"] = NAV_ITEMS
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    app.include_router(build_homepage_router(templates, get_snapshot, get_detail, cache))
    return app


async def test_homepage_returns_200_with_nav_and_hero_text():
    app = _build_app()

    response = await asgi_get(app, "/")

    assert response.status_code == 200
    assert "Данные NASA — ближе, чем кажутся." in response.text
    for item in NAV_ITEMS:
        assert item["label"] in response.text


async def test_snapshot_endpoint_returns_expected_shape():
    app = _build_app()

    response = await asgi_get(app, "/api/homepage/snapshot")

    assert response.status_code == 200
    body = response.json()
    assert "apod_day_number" in body
    assert "asteroid_name" in body
    assert "space_weather_label" in body
    assert "earth_event_title" in body


async def test_detail_endpoint_for_each_known_kind():
    app = _build_app()

    for kind in ("apod", "asteroid", "space-weather", "earth-event"):
        response = await asgi_get(app, f"/api/homepage/details/{kind}")

        assert response.status_code == 200
        body = response.json()
        assert body["kind"] == kind
        assert "available" in body


async def test_detail_endpoint_404_for_unknown_kind():
    app = _build_app()

    response = await asgi_get(app, "/api/homepage/details/weekly-highlights")

    assert response.status_code == 404


async def test_placeholder_routes_return_200_with_in_development_text():
    app = _build_app()

    for path, section_title in PLACEHOLDER_SECTIONS.items():
        response = await asgi_get(app, path)

        assert response.status_code == 200
        assert "в разработке" in response.text
        assert section_title in response.text
