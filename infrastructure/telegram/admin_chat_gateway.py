from __future__ import annotations

import asyncio
from typing import Sequence

import aiohttp
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, InputMediaPhoto, Message

from application.media.ports import CachedMessageRef, MediaPayload, PhotoGroupPayload, SinglePhotoPayload
from infrastructure.files.temp_file import remove_temp_file, temp_image_file, write_temp_image
from infrastructure.http import fetch_bytes


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
        return await self._publish_group(payload)

    async def forward_single(self, message_id: int, chat_id: int) -> None:
        await self._bot.copy_message(chat_id=chat_id, from_chat_id=self._admin_chat_id, message_id=message_id)

    async def forward_group(self, frame_file_ids: Sequence[str], chat_id: int) -> None:
        media = [InputMediaPhoto(media=file_id) for file_id in frame_file_ids]
        await self._bot.send_media_group(chat_id=chat_id, media=media)

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
        return CachedMessageRef(message_id=message.message_id)

    async def _send_photo_via_download(self, image_url: str, caption: str) -> Message:
        raw_bytes = await fetch_bytes(self._session, image_url)
        async with temp_image_file(raw_bytes) as file_path:
            return await self._bot.send_photo(
                chat_id=self._admin_chat_id, photo=FSInputFile(file_path), caption=caption
            )

    async def _publish_group(self, payload: PhotoGroupPayload) -> CachedMessageRef:
        file_paths = await asyncio.gather(*(write_temp_image(image_bytes) for image_bytes in payload.images))
        try:
            media = [InputMediaPhoto(media=FSInputFile(path)) for path in file_paths]
            messages = await self._bot.send_media_group(chat_id=self._admin_chat_id, media=media)
        finally:
            for path in file_paths:
                remove_temp_file(path)
        frame_ids = tuple(message.photo[-1].file_id for message in messages)
        return CachedMessageRef(frame_file_ids=frame_ids)
