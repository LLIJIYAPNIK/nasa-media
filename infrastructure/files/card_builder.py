from __future__ import annotations

import asyncio
from collections.abc import Sequence
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

CARD_SIZE = (1080, 1080)
# Глубокий тёмно-синий, не чёрный — facts-first дизайн без брендинга/логотипа
# (см. docs/tz/TZ-share-cards.md).
BACKGROUND_COLOR = (10, 14, 30)
TEXT_COLOR = (235, 235, 245)
MARGIN = 80
TITLE_FONT_SIZE = 56
BODY_FONT_SIZE = 40
LINE_SPACING = 24


def _build_card(title: str, lines: Sequence[str]) -> bytes:
    image = Image.new("RGB", CARD_SIZE, color=BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)

    title_font = ImageFont.load_default(size=TITLE_FONT_SIZE)
    body_font = ImageFont.load_default(size=BODY_FONT_SIZE)

    y = MARGIN
    draw.text((MARGIN, y), title, font=title_font, fill=TEXT_COLOR)
    y += TITLE_FONT_SIZE + LINE_SPACING * 2

    for line in lines:
        draw.text((MARGIN, y), line, font=body_font, fill=TEXT_COLOR)
        y += BODY_FONT_SIZE + LINE_SPACING

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


async def build_card(title: str, lines: Sequence[str]) -> bytes:
    """Рендерит карточку 1080x1080 PNG — заголовок + короткие строки-факты,
    без переноса по ширине (вызывающий код обязан передавать уже короткие
    строки, см. TZ-share-cards.md). Блокирующая Pillow-отрисовка уведена в
    поток, тот же приём, что gif_builder.py/temp_file.py."""
    return await asyncio.to_thread(_build_card, title, lines)
