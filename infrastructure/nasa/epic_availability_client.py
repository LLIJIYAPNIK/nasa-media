from __future__ import annotations

from datetime import date as date_
from typing import Sequence

import aiohttp

from infrastructure.http import fetch_json


class EpicAvailabilityClient:
    """Заменяет handlers/EPIC/fill_db.py:fetch_dates_from_api(). Старый код
    обращался к отдельному захардкоженному URL вместо NASA_EPIC_URL из
    конфига — здесь один и тот же базовый URL для обоих запросов EPIC API."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str, api_base_url: str) -> None:
        self._session = session
        self._api_key = api_key
        self._api_base_url = api_base_url

    async def fetch_known_dates(self) -> Sequence[date_]:
        data = await fetch_json(self._session, f"{self._api_base_url}/all", {"api_key": self._api_key})

        dates = set()
        for item in data:
            raw_date = item.get("date")
            if not raw_date:
                continue
            dates.add(date_.fromisoformat(raw_date.split()[0]))
        return sorted(dates)
