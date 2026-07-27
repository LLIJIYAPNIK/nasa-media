from __future__ import annotations

from datetime import date as date_

from application.media.deliver_media import DeliverMediaForDate
from application.media.ports import GreetingSender, UserRepository
from domain.media.exceptions import MediaNotAvailable
from domain.users.birthday import is_birthday_today

GREETING_TEXT = (
    "🎉 С днём рождения! Вот такое небо видела NASA сегодня — в твой день.\n\n"
    "Перешли этот пост другу, если понравилось — вдруг у него тоже скоро день рождения 🎂"
)


class SendBirthdayGreetings:
    """Раз в сутки в periodic_broadcast (main.py) — независимо от подписки на
    APOD-рассылку: день рождения вводится отдельно один раз, а не через
    apod_subscribed."""

    def __init__(
        self, deliver: DeliverMediaForDate, user_repo: UserRepository, greeting_sender: GreetingSender
    ) -> None:
        self._deliver = deliver
        self._user_repo = user_repo
        self._greeting_sender = greeting_sender

    async def execute(self, today: date_) -> None:
        candidates = await self._user_repo.list_with_birthday_set()
        for user in candidates:
            if user.birthday is None or not is_birthday_today(user.birthday, today):
                continue
            try:
                await self._deliver.execute(today, user.chat_id)
            except MediaNotAvailable:
                continue
            await self._greeting_sender.send_text(user.chat_id, GREETING_TEXT)
