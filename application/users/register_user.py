from __future__ import annotations

from application.media.ports import UserRepository
from domain.users.entities import User


class GetOrCreateUser:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self, chat_id: int) -> User:
        existing = await self._user_repo.get_by_chat_id(chat_id)
        if existing is not None:
            return existing
        return await self._user_repo.add(chat_id)
