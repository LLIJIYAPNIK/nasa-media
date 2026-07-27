from __future__ import annotations

from datetime import date as date_

from application.media.deliver_media import DeliverMediaForDate
from application.media.ports import UserRepository
from domain.media.exceptions import MediaNotAvailable
from domain.media.value_objects import MediaSourceKind


class BroadcastSubscribedUsers:
    def __init__(self, source: MediaSourceKind, deliver: DeliverMediaForDate, user_repo: UserRepository) -> None:
        self._source = source
        self._deliver = deliver
        self._user_repo = user_repo

    async def execute(self, today: date_) -> None:
        users = await self._user_repo.list_subscribed(self._source)
        for user in users:
            try:
                await self._deliver.execute(today, user.chat_id)
            except MediaNotAvailable:
                continue
