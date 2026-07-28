from __future__ import annotations

from aiogram import Bot
from aiogram.types import FSInputFile

from infrastructure.files.temp_file import temp_file


class TelegramGreetingSender:
    """Личное сообщение пользователю напрямую, в обход admin-чата — не
    кешируется и не переиспользуется другими получателями (см.
    application/media/ports.py:GreetingSender)."""

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_text(self, chat_id: int, text: str) -> None:
        await self._bot.send_message(chat_id=chat_id, text=text)

    async def send_image(self, chat_id: int, image_bytes: bytes, caption: str | None = None) -> None:
        async with temp_file(image_bytes, ".png") as file_path:
            await self._bot.send_photo(chat_id=chat_id, photo=FSInputFile(file_path), caption=caption)
