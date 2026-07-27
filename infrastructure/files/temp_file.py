from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from io import BytesIO

from PIL import Image

TEMP_DIR = "tmp_media"
DEFAULT_MAX_DIMENSIONS = (1280, 1280)


def _write_resized_image(image_bytes: bytes, file_path: str, max_dimensions: tuple[int, int]) -> None:
    image = Image.open(BytesIO(image_bytes))
    image.thumbnail(max_dimensions)
    image.save(file_path, format="JPEG")


def _write_bytes(data: bytes, file_path: str) -> None:
    with open(file_path, "wb") as file:
        file.write(data)


def _temp_path(suffix: str) -> str:
    os.makedirs(TEMP_DIR, exist_ok=True)
    return os.path.join(TEMP_DIR, f"{uuid.uuid4()}{suffix}")


async def write_temp_image(image_bytes: bytes, max_dimensions: tuple[int, int] = DEFAULT_MAX_DIMENSIONS) -> str:
    """Уникальное (uuid4) имя вместо старого фиксированного temp_image.jpg —
    иначе параллельные запросы затирают файл друг друга. Само изменение
    размера и запись — блокирующий Pillow-вызов, уводим в поток, чтобы не
    задерживать event loop бота."""
    file_path = _temp_path(".jpg")
    await asyncio.to_thread(_write_resized_image, image_bytes, file_path, max_dimensions)
    return file_path


async def write_temp_bytes(data: bytes, suffix: str) -> str:
    """Как write_temp_image, но без ресайза — для уже готового файла
    (например, собранного GIF)."""
    file_path = _temp_path(suffix)
    await asyncio.to_thread(_write_bytes, data, file_path)
    return file_path


def remove_temp_file(file_path: str) -> None:
    if os.path.exists(file_path):
        os.remove(file_path)


@asynccontextmanager
async def temp_image_file(
    image_bytes: bytes, max_dimensions: tuple[int, int] = DEFAULT_MAX_DIMENSIONS
) -> AsyncIterator[str]:
    """Удаление — через try/finally, а не в конце функции-вызывающего:
    гарантированно сработает даже если отправка в Telegram упадёт с исключением."""
    file_path = await write_temp_image(image_bytes, max_dimensions)
    try:
        yield file_path
    finally:
        remove_temp_file(file_path)


@asynccontextmanager
async def temp_file(data: bytes, suffix: str) -> AsyncIterator[str]:
    file_path = await write_temp_bytes(data, suffix)
    try:
        yield file_path
    finally:
        remove_temp_file(file_path)
