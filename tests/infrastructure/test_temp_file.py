import os
from io import BytesIO

import pytest
from PIL import Image

from infrastructure.files.temp_file import temp_image_file


def _fake_jpeg_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buffer, format="JPEG")
    return buffer.getvalue()


async def test_temp_image_file_is_removed_after_use():
    async with temp_image_file(_fake_jpeg_bytes()) as path:
        assert os.path.exists(path)
        captured_path = path
    assert not os.path.exists(captured_path)


async def test_temp_image_file_is_removed_even_if_caller_raises():
    captured_path = None
    with pytest.raises(RuntimeError):
        async with temp_image_file(_fake_jpeg_bytes()) as path:
            captured_path = path
            raise RuntimeError("boom")
    assert not os.path.exists(captured_path)


async def test_concurrent_calls_do_not_collide_on_filename():
    async with temp_image_file(_fake_jpeg_bytes()) as path_a:
        async with temp_image_file(_fake_jpeg_bytes()) as path_b:
            assert path_a != path_b
            assert os.path.exists(path_a)
            assert os.path.exists(path_b)
