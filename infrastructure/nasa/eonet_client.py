from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import aiohttp

from domain.digest.value_objects import EarthEventHighlight
from infrastructure.http import fetch_json

EONET_EVENT_LIMIT = 20


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
            dates = [datetime.fromisoformat(point["date"]) for point in event.get("geometry", []) if point.get("date")]
            if not dates:
                continue
            categories = event.get("categories") or []
            category = categories[0]["title"] if categories else ""
            highlights.append(EarthEventHighlight(title=event["title"], category=category, event_date=max(dates)))
        return highlights
