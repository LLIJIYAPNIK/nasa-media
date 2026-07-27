from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock


class FakeMessage:
    def __init__(self, chat_id: int, text: str | None = None) -> None:
        self.chat = MagicMock(id=chat_id)
        self.text = text
        self.bot = MagicMock()
        self.delete = AsyncMock()
        self.answer = AsyncMock()
        self.reply = AsyncMock()


class FakeCallbackQuery:
    def __init__(self, data: str, chat_id: int) -> None:
        self.data = data
        self.message = FakeMessage(chat_id)
