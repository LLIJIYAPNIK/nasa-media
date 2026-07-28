from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from presentation.web.routers.homepage_router import NAV_ITEMS, PLACEHOLDER_SECTIONS, build_homepage_router
from tests.presentation.asgi_test_client import asgi_get

WEB_DIR = Path(__file__).resolve().parents[2] / "presentation" / "web"


def _build_app() -> FastAPI:
    app = FastAPI()
    templates = Jinja2Templates(directory=WEB_DIR / "templates")
    templates.env.globals["nav_items"] = NAV_ITEMS
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    app.include_router(build_homepage_router(templates))
    return app


async def test_placeholder_routes_return_200_with_in_development_text():
    app = _build_app()

    for path, section_title in PLACEHOLDER_SECTIONS.items():
        response = await asgi_get(app, path)

        assert response.status_code == 200
        assert "в разработке" in response.text
        assert section_title in response.text


async def test_placeholder_route_includes_all_nav_items():
    app = _build_app()

    response = await asgi_get(app, "/apod")

    for item in NAV_ITEMS:
        assert item["label"] in response.text
