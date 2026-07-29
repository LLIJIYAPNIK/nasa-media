from __future__ import annotations

import asyncio
import math
from io import BytesIO

import aiohttp
from PIL import Image, ImageDraw

from domain.digest.value_objects import EventGeometryPoint
from infrastructure.http import fetch_bytes

TILE_SIZE = 256
MAP_WIDTH = 640
MAP_HEIGHT = 400
# Фиксированный масштаб на всю карту (не зависит от типа события) — см.
# docs/tz/TZ_karta_sobytiya_EONET.md, «Решения по неоднозначностям»:
# per-категорийный масштаб — осознанно вне рамок MVP.
BBOX_HALF_SPAN_DEG = 4.0
MAX_ZOOM = 9
MARKER_RADIUS = 9
MARKER_COLOR = (235, 87, 87)
MARKER_OUTLINE = (255, 255, 255)
MARKER_OUTLINE_WIDTH = 2
TILE_FALLBACK_COLOR = (30, 34, 46)

# OpenStreetMap выбран вместо GIBS для MVP — см. TZ, «Решения по
# неоднозначностям»: GIBS требует второй API-вызов (Categories → Layers)
# и per-категорийное согласование WMS/WMTS-параметров, которое нельзя
# проверить визуально без живой отладки. OSM — фиксированная XYZ-схема,
# один детерминированный запрос на тайл.
TILE_URL_TEMPLATE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
# Tile Usage Policy OSM требует идентифицирующий User-Agent — без него
# запросы могут блокироваться.
TILE_USER_AGENT = "nasa-media/1.0 (+https://github.com/LLIJIYAPNIK/nasa-media)"


def _lonlat_to_global_pixel(lon: float, lat: float, zoom: int) -> tuple[float, float]:
    n = 2**zoom
    x = (lon + 180.0) / 360.0 * n * TILE_SIZE
    lat_rad = math.radians(max(min(lat, 85.05), -85.05))
    y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n * TILE_SIZE
    return x, y


def _pick_zoom() -> int:
    for zoom in range(MAX_ZOOM, 0, -1):
        n = 2**zoom
        px_per_deg = n * TILE_SIZE / 360.0
        span_px = BBOX_HALF_SPAN_DEG * 2 * px_per_deg
        if span_px <= MAP_WIDTH * 1.4:
            return zoom
    return 1


async def _fetch_tile(session: aiohttp.ClientSession, zoom: int, tile_x: int, tile_y: int) -> bytes | None:
    n = 2**zoom
    if not (0 <= tile_x < n and 0 <= tile_y < n):
        return None
    url = TILE_URL_TEMPLATE.format(z=zoom, x=tile_x, y=tile_y)
    try:
        return await fetch_bytes(session, url, headers={"User-Agent": TILE_USER_AGENT})
    except (aiohttp.ClientError, TimeoutError):
        return None


def _compose_map(
    tiles: dict[tuple[int, int], bytes | None],
    tile_x_min: int,
    tile_y_min: int,
    crop_offset: tuple[float, float],
    marker_px: tuple[float, float],
) -> bytes:
    tile_x_max = max(tx for tx, _ in tiles)
    tile_y_max = max(ty for _, ty in tiles)
    composite = Image.new(
        "RGB",
        ((tile_x_max - tile_x_min + 1) * TILE_SIZE, (tile_y_max - tile_y_min + 1) * TILE_SIZE),
        color=TILE_FALLBACK_COLOR,
    )
    for (tile_x, tile_y), data in tiles.items():
        if data is None:
            continue
        tile_image = Image.open(BytesIO(data)).convert("RGB")
        composite.paste(tile_image, ((tile_x - tile_x_min) * TILE_SIZE, (tile_y - tile_y_min) * TILE_SIZE))

    offset_x, offset_y = crop_offset
    left, top = int(offset_x), int(offset_y)
    cropped = composite.crop((left, top, left + MAP_WIDTH, top + MAP_HEIGHT))

    draw = ImageDraw.Draw(cropped)
    marker_x, marker_y = marker_px
    draw.ellipse(
        (marker_x - MARKER_RADIUS, marker_y - MARKER_RADIUS, marker_x + MARKER_RADIUS, marker_y + MARKER_RADIUS),
        fill=MARKER_COLOR,
        outline=MARKER_OUTLINE,
        width=MARKER_OUTLINE_WIDTH,
    )

    buffer = BytesIO()
    cropped.save(buffer, format="PNG")
    return buffer.getvalue()


async def render_event_map(session: aiohttp.ClientSession, point: EventGeometryPoint) -> bytes | None:
    """Рендерит PNG MAP_WIDTH×MAP_HEIGHT с меткой в центре — только
    последняя точка события, без полного трека (см. TZ, «Что осознанно
    вне рамок»). Тайлы OSM стягиваются в композит и обрезаются по bbox
    вокруг точки; при полном отказе сети возвращает None (карта в модалке
    просто не рендерится, без пустого/битого блока)."""
    zoom = _pick_zoom()
    center_x, center_y = _lonlat_to_global_pixel(point.lon, point.lat, zoom)
    left, top = center_x - MAP_WIDTH / 2, center_y - MAP_HEIGHT / 2

    tile_x_min, tile_x_max = int(left // TILE_SIZE), int((left + MAP_WIDTH - 1) // TILE_SIZE)
    tile_y_min, tile_y_max = int(top // TILE_SIZE), int((top + MAP_HEIGHT - 1) // TILE_SIZE)

    coords = [(tx, ty) for tx in range(tile_x_min, tile_x_max + 1) for ty in range(tile_y_min, tile_y_max + 1)]
    fetched = await asyncio.gather(*[_fetch_tile(session, zoom, tx, ty) for tx, ty in coords])
    tiles = dict(zip(coords, fetched, strict=True))

    if not any(data is not None for data in tiles.values()):
        return None

    crop_offset = (left - tile_x_min * TILE_SIZE, top - tile_y_min * TILE_SIZE)
    marker_px = (MAP_WIDTH / 2, MAP_HEIGHT / 2)
    return await asyncio.to_thread(_compose_map, tiles, tile_x_min, tile_y_min, crop_offset, marker_px)
