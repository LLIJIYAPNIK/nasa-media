from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiohttp
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config
from application.web.homepage_detail_query import GetHomepageDetail
from application.web.homepage_query import GetHomepageSnapshot
from infrastructure.nasa.apod_client import ApodClient
from infrastructure.nasa.donki_client import DonkiClient
from infrastructure.nasa.eonet_client import EonetClient
from infrastructure.nasa.neows_client import NeoWsClient
from infrastructure.translation.ru_translator import GoogleRuTranslator
from infrastructure.web.event_map_builder import OsmEventMapBuilder
from infrastructure.web.event_map_cache import EventMapFileCache
from infrastructure.web.snapshot_cache import SnapshotCache
from presentation.web.routers.homepage_router import NAV_ITEMS, build_homepage_router

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with aiohttp.ClientSession() as session:
        translator = GoogleRuTranslator()
        apod_client = ApodClient(session, config.NASA_API_KEY, config.NASA_APOD_URL, translator)
        donki_client = DonkiClient(session, config.NASA_API_KEY, config.NASA_DONKI_URL)
        neows_client = NeoWsClient(session, config.NASA_API_KEY, config.NASA_NEOWS_URL)
        eonet_client = EonetClient(session, config.NASA_EONET_URL)

        templates = Jinja2Templates(directory=BASE_DIR / "templates")
        templates.env.globals["nav_items"] = NAV_ITEMS

        event_map_cache = EventMapFileCache()
        event_map_builder = OsmEventMapBuilder(session, event_map_cache)

        get_snapshot = GetHomepageSnapshot(donki_client, neows_client, eonet_client)
        get_detail = GetHomepageDetail(apod_client, donki_client, neows_client, eonet_client, event_map_builder)
        cache = SnapshotCache()

        app.include_router(build_homepage_router(templates, get_snapshot, get_detail, cache, event_map_cache))

        yield


def create_app() -> FastAPI:
    app = FastAPI(title="nasa-media", lifespan=_lifespan)
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    return app


app = create_app()
