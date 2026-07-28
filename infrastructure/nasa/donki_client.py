from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_
from datetime import datetime

import aiohttp

from domain.digest.value_objects import SpaceWeatherHighlight
from infrastructure.http import fetch_json


class DonkiClient:
    """DONKI notifications за конкретный день — `messageType` +
    `messageIssueTime` только, без парсинга messageBody (см.
    docs/tz/TZ-daily-digest.md, «Решения»)."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str, base_url: str) -> None:
        self._session = session
        self._api_key = api_key
        self._base_url = base_url

    async def fetch_for_day(self, day: date_) -> Sequence[SpaceWeatherHighlight]:
        data = await fetch_json(
            self._session,
            self._base_url,
            {
                "startDate": day.isoformat(),
                "endDate": day.isoformat(),
                "type": "all",
                "api_key": self._api_key,
            },
        )

        highlights = []
        for item in data:
            message_type = item.get("messageType")
            issued_at_raw = item.get("messageIssueTime")
            if not message_type or not issued_at_raw:
                continue
            highlights.append(
                SpaceWeatherHighlight(message_type=message_type, issued_at=datetime.fromisoformat(issued_at_raw))
            )
        return highlights
