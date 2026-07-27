from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

from aiogram.exceptions import TelegramBadRequest
from PIL import Image

from application.media.ports import PhotoGroupPayload, SinglePhotoPayload
from infrastructure.telegram.admin_chat_gateway import TelegramAdminChatGateway
from tests.infrastructure.fake_aiohttp import FakeClientSession, FakeResponse

ADMIN_CHAT_ID = 999


def _fake_jpeg_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buffer, format="JPEG")
    return buffer.getvalue()


async def test_publish_single_sends_by_direct_url_when_telegram_accepts_it():
    bot = MagicMock()
    bot.send_photo = AsyncMock(return_value=MagicMock(message_id=42))
    gateway = TelegramAdminChatGateway(FakeClientSession({}), bot, ADMIN_CHAT_ID)
    payload = SinglePhotoPayload(image_url="http://example.com/img.jpg", caption="caption")

    ref = await gateway.publish(payload)

    assert ref.message_id == 42
    bot.send_photo.assert_awaited_once_with(chat_id=ADMIN_CHAT_ID, photo=payload.image_url, caption=payload.caption)


async def test_publish_single_falls_back_to_download_when_telegram_rejects_direct_url():
    bot = MagicMock()
    bot.send_photo = AsyncMock(
        side_effect=[TelegramBadRequest(MagicMock(), "bad url"), MagicMock(message_id=7)]
    )
    session = FakeClientSession({"http://example.com/img.jpg": FakeResponse(body=_fake_jpeg_bytes())})
    gateway = TelegramAdminChatGateway(session, bot, ADMIN_CHAT_ID)
    payload = SinglePhotoPayload(image_url="http://example.com/img.jpg", caption="caption")

    ref = await gateway.publish(payload)

    assert ref.message_id == 7
    assert bot.send_photo.await_count == 2


async def test_publish_group_sends_media_group_and_returns_frame_file_ids():
    fake_messages = [MagicMock(photo=[MagicMock(file_id="file-a")]), MagicMock(photo=[MagicMock(file_id="file-b")])]
    bot = MagicMock()
    bot.send_media_group = AsyncMock(return_value=fake_messages)
    gateway = TelegramAdminChatGateway(FakeClientSession({}), bot, ADMIN_CHAT_ID)
    payload = PhotoGroupPayload(images=[_fake_jpeg_bytes(), _fake_jpeg_bytes()])

    ref = await gateway.publish(payload)

    assert ref.frame_file_ids == ("file-a", "file-b")


async def test_forward_single_copies_message_from_admin_chat():
    bot = MagicMock()
    bot.copy_message = AsyncMock()
    gateway = TelegramAdminChatGateway(FakeClientSession({}), bot, ADMIN_CHAT_ID)

    await gateway.forward_single(message_id=5, chat_id=123)

    bot.copy_message.assert_awaited_once_with(chat_id=123, from_chat_id=ADMIN_CHAT_ID, message_id=5)


async def test_forward_group_resends_media_group_by_file_id():
    bot = MagicMock()
    bot.send_media_group = AsyncMock()
    gateway = TelegramAdminChatGateway(FakeClientSession({}), bot, ADMIN_CHAT_ID)

    await gateway.forward_group(("file-a", "file-b"), chat_id=123)

    _, kwargs = bot.send_media_group.await_args
    assert kwargs["chat_id"] == 123
    assert [media.media for media in kwargs["media"]] == ["file-a", "file-b"]
