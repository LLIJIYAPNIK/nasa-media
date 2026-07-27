from __future__ import annotations

from aiogram import Bot


class TelegramGreetingSender:
    """Личное сообщение пользователю напрямую, в обход admin-чата — не
    кешируется и не переиспользуется другими получателями (см.
    application/media/ports.py:GreetingSender)."""

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_text(self, chat_id: int, text: str) -> None:
        await self._bot.send_message(chat_id=chat_id, text=text)
