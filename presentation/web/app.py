from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from presentation.web.routers.homepage_router import NAV_ITEMS, build_homepage_router

BASE_DIR = Path(__file__).resolve().parent


def create_app() -> FastAPI:
    app = FastAPI(title="nasa-media")

    templates = Jinja2Templates(directory=BASE_DIR / "templates")
    templates.env.globals["nav_items"] = NAV_ITEMS

    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    app.include_router(build_homepage_router(templates))

    return app


app = create_app()
