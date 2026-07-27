from __future__ import annotations

from datetime import date as date_

from application.media.ports import UserRepository
from application.users.register_user import GetOrCreateUser
from domain.users.entities import User


class SetBirthday:
    def __init__(self, user_repo: UserRepository, get_or_create_user: GetOrCreateUser) -> None:
        self._user_repo = user_repo
        self._get_or_create_user = get_or_create_user

    async def execute(self, chat_id: int, birthday: date_) -> User:
        user = await self._get_or_create_user.execute(chat_id)
        updated = user.with_birthday(birthday)
        await self._user_repo.save(updated)
        return updated
