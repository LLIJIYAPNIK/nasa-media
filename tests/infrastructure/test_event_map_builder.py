from datetime import datetime

import aiohttp

from domain.digest.value_objects import EarthEventHighlight, EventGeometryPoint
from infrastructure.web.event_map_builder import OsmEventMapBuilder
from infrastructure.web.event_map_cache import EventMapFileCache
from tests.infrastructure.fake_aiohttp import AnyUrlClientSession, FailingClientSession
from tests.infrastructure.test_event_map import fake_tile_bytes


def _event(id: str = "EONET_1", geometry=None) -> EarthEventHighlight:
    if geometry is None:
        geometry = [EventGeometryPoint(lon=-80.0, lat=25.0, date=datetime(2024, 1, 3))]
    return EarthEventHighlight(
        title="Wildfire", category="Wildfires", event_date=datetime(2024, 1, 3), id=id, geometry=geometry
    )


async def test_builder_generates_and_caches_by_event_id_and_latest_date(tmp_path):
    session = AnyUrlClientSession(fake_tile_bytes((10, 20, 30)))
    cache = EventMapFileCache(directory=tmp_path)
    builder = OsmEventMapBuilder(session, cache)
    event = _event()

    cache_key = await builder.build(event)

    assert cache_key == "EONET_1_2024-01-03"
    assert await cache.exists(cache_key)


async def test_builder_reuses_cache_without_refetching_tiles(tmp_path):
    session = AnyUrlClientSession(fake_tile_bytes((10, 20, 30)))
    cache = EventMapFileCache(directory=tmp_path)
    builder = OsmEventMapBuilder(session, cache)
    event = _event()

    first_key = await builder.build(event)
    request_count_after_first = len(session.requested_urls)
    second_key = await builder.build(event)

    assert first_key == second_key
    assert len(session.requested_urls) == request_count_after_first


async def test_builder_returns_none_without_id():
    session = AnyUrlClientSession(fake_tile_bytes((10, 20, 30)))
    cache = EventMapFileCache()
    builder = OsmEventMapBuilder(session, cache)
    event = _event(id="")

    assert await builder.build(event) is None


async def test_builder_returns_none_without_geometry():
    session = AnyUrlClientSession(fake_tile_bytes((10, 20, 30)))
    cache = EventMapFileCache()
    builder = OsmEventMapBuilder(session, cache)
    event = _event(geometry=())

    assert await builder.build(event) is None


async def test_builder_returns_none_when_tiles_unavailable(tmp_path):
    session = FailingClientSession(aiohttp.ClientConnectionError("boom"))
    cache = EventMapFileCache(directory=tmp_path)
    builder = OsmEventMapBuilder(session, cache)
    event = _event()

    assert await builder.build(event) is None
    assert not await cache.exists("EONET_1_2024-01-03")
