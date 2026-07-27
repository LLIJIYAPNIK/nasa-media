from __future__ import annotations

from application.media.ports import UserRepository
from domain.media.value_objects import MediaSourceKind
from domain.users.entities import User


class SetSubscription:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self, chat_id: int, source: MediaSourceKind, value: bool) -> User:
        user = await self._user_repo.get_by_chat_id(chat_id)
        updated = user.with_subscription(source, value)
        await self._user_repo.save(updated)
        return updated
