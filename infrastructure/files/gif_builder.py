from __future__ import annotations

import asyncio
from collections.abc import Sequence
from io import BytesIO

from PIL import Image

# Меньше, чем DEFAULT_MAX_DIMENSIONS для одиночного фото (temp_file.py) —
# анимация из N кадров при 1280x1280 весит непрактично много.
GIF_MAX_DIMENSIONS = (640, 640)
GIF_FRAME_DURATION_MS = 200


def _build_gif(frames: Sequence[bytes], max_dimensions: tuple[int, int]) -> bytes:
    images = []
    for frame_bytes in frames:
        image = Image.open(BytesIO(frame_bytes)).convert("RGB")
        image.thumbnail(max_dimensions)
        images.append(image)

    buffer = BytesIO()
    images[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=images[1:],
        duration=GIF_FRAME_DURATION_MS,
        loop=0,
    )
    return buffer.getvalue()


async def build_gif(frames: Sequence[bytes], max_dimensions: tuple[int, int] = GIF_MAX_DIMENSIONS) -> bytes:
    """Собирает кадры EPIC за сутки в анимированный GIF (см.
    TZ-gif-timelapse.md) — блокирующая Pillow-сборка уведена в поток, как и
    ресайз одиночных фото в temp_file.py."""
    return await asyncio.to_thread(_build_gif, frames, max_dimensions)
