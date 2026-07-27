from __future__ import annotations

from application.media.ports import UserRepository
from application.users.register_user import GetOrCreateUser
from domain.media.value_objects import MediaSourceKind
from domain.users.entities import User


class SetSubscription:
    def __init__(self, user_repo: UserRepository, get_or_create_user: GetOrCreateUser) -> None:
        self._user_repo = user_repo
        self._get_or_create_user = get_or_create_user

    async def execute(self, chat_id: int, source: MediaSourceKind, value: bool) -> User:
        # Реализация через get-or-create, а не голый get_by_chat_id: подписка
        # приходит из callback_data кнопки в уже показанном меню, так что
        # пользователь почти всегда уже зарегистрирован через /start, но на
        # случай гонки/пересланной клавиатуры не должно падать на None.
        user = await self._get_or_create_user.execute(chat_id)
        updated = user.with_subscription(source, value)
        await self._user_repo.save(updated)
        return updated
