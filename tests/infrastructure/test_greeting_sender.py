from unittest.mock import AsyncMock, MagicMock

from infrastructure.telegram.greeting_sender import TelegramGreetingSender


async def test_send_text_sends_message():
    bot = MagicMock()
    bot.send_message = AsyncMock()
    sender = TelegramGreetingSender(bot)

    await sender.send_text(chat_id=1, text="привет")

    bot.send_message.assert_awaited_once_with(chat_id=1, text="привет")


async def test_send_image_sends_photo_with_caption():
    bot = MagicMock()
    bot.send_photo = AsyncMock()
    sender = TelegramGreetingSender(bot)

    await sender.send_image(chat_id=1, image_bytes=b"png-bytes", caption="подпись")

    assert bot.send_photo.await_args.kwargs["chat_id"] == 1
    assert bot.send_photo.await_args.kwargs["caption"] == "подпись"
