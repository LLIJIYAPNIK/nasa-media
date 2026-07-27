from io import BytesIO

from PIL import Image

from infrastructure.files.gif_builder import build_gif


def _fake_png_bytes(color: str, size: tuple[int, int] = (100, 100)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color=color).save(buffer, format="PNG")
    return buffer.getvalue()


async def test_build_gif_produces_animation_with_all_frames_in_order():
    frames = [_fake_png_bytes("red"), _fake_png_bytes("green"), _fake_png_bytes("blue")]

    gif_bytes = await build_gif(frames)

    gif = Image.open(BytesIO(gif_bytes))
    assert gif.format == "GIF"
    assert gif.n_frames == 3

    colors = []
    for frame_index in range(gif.n_frames):
        gif.seek(frame_index)
        colors.append(gif.convert("RGB").getpixel((0, 0)))
    assert colors == [(255, 0, 0), (0, 128, 0), (0, 0, 255)]


async def test_build_gif_resizes_frames_down_to_max_dimensions():
    frames = [_fake_png_bytes("red", size=(2000, 2000))]

    gif_bytes = await build_gif(frames, max_dimensions=(100, 100))

    gif = Image.open(BytesIO(gif_bytes))
    assert gif.size == (100, 100)
