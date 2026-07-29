from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import aiohttp

from domain.digest.value_objects import EarthEventHighlight, EventGeometryPoint, EventSource
from infrastructure.http import fetch_json

EONET_EVENT_LIMIT = 20


def _parse_geometry(raw_geometry: list[dict]) -> list[EventGeometryPoint]:
    points = []
    for point in raw_geometry:
        coordinates = point.get("coordinates")
        if not point.get("date") or not coordinates or len(coordinates) < 2:
            continue
        points.append(
            EventGeometryPoint(
                lon=coordinates[0],
                lat=coordinates[1],
                date=datetime.fromisoformat(point["date"]),
                magnitude_value=point.get("magnitudeValue"),
                magnitude_unit=point.get("magnitudeUnit"),
                magnitude_description=point.get("magnitudeDescription"),
            )
        )
    return sorted(points, key=lambda p: p.date)


class EonetClient:
    """Открытые события EONET — отдельный хост (eonet.gsfc.nasa.gov), не
    принимает и не требует api_key вообще (см. docs/tz/TZ-daily-digest.md) —
    не передаём его, в отличие от остальных NASA-клиентов. Нет фильтра по
    дате на уровне API, поэтому берём N последних открытых событий."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str) -> None:
        self._session = session
        self._base_url = base_url

    async def fetch_recent(self) -> Sequence[EarthEventHighlight]:
        data = await fetch_json(self._session, self._base_url, {"status": "open", "limit": EONET_EVENT_LIMIT})

        highlights = []
        for event in data.get("events", []):
            points = _parse_geometry(event.get("geometry", []))
            if not points:
                continue
            latest = points[-1]

            category_titles = [category["title"] for category in event.get("categories") or []]
            sources = [
                EventSource(label=source.get("id", ""), url=source["url"])
                for source in event.get("sources", [])
                if source.get("url")
            ]
            closed_raw = event.get("closed")

            highlights.append(
                EarthEventHighlight(
                    title=event["title"],
                    category=category_titles[0] if category_titles else "",
                    event_date=latest.date,
                    id=event.get("id", ""),
                    categories=category_titles,
                    description=event.get("description") or None,
                    closed_at=datetime.fromisoformat(closed_raw) if closed_raw else None,
                    link=event.get("link", ""),
                    sources=sources,
                    geometry=points,
                    magnitude_value=latest.magnitude_value,
                    magnitude_unit=latest.magnitude_unit,
                    magnitude_description=latest.magnitude_description,
                )
            )
        return highlights
