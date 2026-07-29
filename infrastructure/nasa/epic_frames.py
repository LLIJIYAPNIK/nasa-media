from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date as date_

import aiohttp

from infrastructure.http import fetch_bytes, fetch_json

# Общее между ботом (EpicProvider — собирает GIF) и веб-страницей /epic
# (берёт один кадр + centroid_coordinates, см. docs/tz/TZ-web-epic.md) —
# вынесено сюда, а не продублировано, при добавлении второго потребителя
# этого же ответа NASA.
EPIC_ARCHIVE_BASE_URL = "https://api.nasa.gov/EPIC/archive/natural"


@dataclass(frozen=True, slots=True)
class EpicFrameMeta:
    """Один кадр из ответа `.../date/{day}` — только то, что реально
    используется хотя бы одним потребителем (image — бот и веб,
    centroid_lat/lon — только веб для ориентации 3D-модели)."""

    image: str
    centroid_lat: float
    centroid_lon: float


async def fetch_day_frames(
    session: aiohttp.ClientSession, api_key: str, api_base_url: str, day: date_
) -> Sequence[EpicFrameMeta]:
    frames_meta = await fetch_json(session, f"{api_base_url}/date/{day.isoformat()}", {"api_key": api_key})
    return [
        EpicFrameMeta(
            image=frame["image"],
            centroid_lat=frame["centroid_coordinates"]["lat"],
            centroid_lon=frame["centroid_coordinates"]["lon"],
        )
        for frame in frames_meta
    ]


async def fetch_frame_bytes(session: aiohttp.ClientSession, api_key: str, day: date_, image_name: str) -> bytes:
    url = f"{EPIC_ARCHIVE_BASE_URL}/{day:%Y}/{day:%m}/{day:%d}/png/{image_name}.png"
    return await fetch_bytes(session, url, {"api_key": api_key})
