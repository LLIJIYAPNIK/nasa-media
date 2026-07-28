from __future__ import annotations

import aiohttp
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, Message

from application.media.ports import (
    AnimationPayload,
    CachedMessageRef,
    GeneratedImagePayload,
    MediaPayload,
    SinglePhotoPayload,
)
from infrastructure.files.temp_file import temp_file, temp_image_file
from infrastructure.http import fetch_bytes


def _largest_photo_file_id(message: Message) -> str:
    """Telegram отдаёт несколько размеров одного фото — берём самый крупный
    (последний в списке), как и раньше игнорируя (см. TZ-inline-mode.md)."""
    assert message.photo is not None
    return message.photo[-1].file_id


class TelegramAdminChatGateway:
    """Общая реализация AdminChatGateway для APOD и EPIC — заменяет
    продублированные handlers/APOD/tools/sender.py и
    handlers/EPIC/tools/send_photo.py+await_message.py."""

    def __init__(self, session: aiohttp.ClientSession, bot: Bot, admin_chat_id: int) -> None:
        self._session = session
        self._bot = bot
        self._admin_chat_id = admin_chat_id

    async def publish(self, payload: MediaPayload) -> CachedMessageRef:
        if isinstance(payload, SinglePhotoPayload):
            return await self._publish_single(payload)
        if isinstance(payload, GeneratedImagePayload):
            return await self._publish_generated_image(payload)
        return await self._publish_animation(payload)

    async def forward_single(self, message_id: int, chat_id: int) -> None:
        await self._bot.copy_message(chat_id=chat_id, from_chat_id=self._admin_chat_id, message_id=message_id)

    async def _publish_single(self, payload: SinglePhotoPayload) -> CachedMessageRef:
        try:
            # Сначала пробуем отправить по прямой ссылке — Telegram сам её
            # скачает, не тратим свой трафик и время без необходимости.
            message = await self._bot.send_photo(
                chat_id=self._admin_chat_id, photo=payload.image_url, caption=payload.caption
            )
        except TelegramBadRequest:
            # Telegram не смог сам обратиться по ссылке — скачиваем и грузим файлом.
            message = await self._send_photo_via_download(payload.image_url, payload.caption)
        return CachedMessageRef(message_id=message.message_id, file_id=_largest_photo_file_id(message))

    async def _send_photo_via_download(self, image_url: str, caption: str) -> Message:
        raw_bytes = await fetch_bytes(self._session, image_url)
        async with temp_image_file(raw_bytes) as file_path:
            return await self._bot.send_photo(
                chat_id=self._admin_chat_id, photo=FSInputFile(file_path), caption=caption
            )

    async def _publish_animation(self, payload: AnimationPayload) -> CachedMessageRef:
        async with temp_file(payload.gif_bytes, ".gif") as file_path:
            message = await self._bot.send_animation(chat_id=self._admin_chat_id, animation=FSInputFile(file_path))
        assert message.animation is not None
        return CachedMessageRef(message_id=message.message_id, file_id=message.animation.file_id)

    async def _publish_generated_image(self, payload: GeneratedImagePayload) -> CachedMessageRef:
        async with temp_file(payload.image_bytes, ".png") as file_path:
            message = await self._bot.send_photo(
                chat_id=self._admin_chat_id, photo=FSInputFile(file_path), caption=payload.caption
            )
        return CachedMessageRef(message_id=message.message_id, file_id=_largest_photo_file_id(message))
