from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_
from typing import Protocol

from application.media.ports import EpicRepository


class EpicAvailabilityIndex(Protocol):
    async def fetch_known_dates(self) -> Sequence[date_]: ...


class RefreshEpicAvailability:
    """Замена handlers/EPIC/fill_db.py — источник правды теперь только БД, без dates.txt."""

    def __init__(self, index: EpicAvailabilityIndex, repo: EpicRepository) -> None:
        self._index = index
        self._repo = repo

    async def execute(self) -> None:
        known_dates = await self._index.fetch_known_dates()
        await self._repo.ensure_known_dates(known_dates)
