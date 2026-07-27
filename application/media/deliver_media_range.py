from __future__ import annotations

from datetime import date as date_

from application.media.deliver_media import DeliverMediaForDate
from domain.media.exceptions import MediaNotAvailable
from domain.media.value_objects import DateRange


class DeliverMediaForDateRange:
    """Доставка за диапазон дат (APOD «несколько дат») — тот же принцип
    накопления недоступных дат, что и BroadcastSubscribedUsers, чтобы
    роутер не содержал сам бизнес-цикл по датам."""

    def __init__(self, deliver: DeliverMediaForDate) -> None:
        self._deliver = deliver

    async def execute(self, date_range: DateRange, chat_id: int) -> list[date_]:
        unavailable_dates: list[date_] = []
        for day in date_range.iter_dates():
            try:
                await self._deliver.execute(day, chat_id)
            except MediaNotAvailable:
                unavailable_dates.append(day)
        return unavailable_dates
