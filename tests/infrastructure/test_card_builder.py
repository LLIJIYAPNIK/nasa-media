from io import BytesIO

from PIL import Image

from infrastructure.files.card_builder import CARD_SIZE, build_card


async def test_build_card_produces_png_of_expected_size():
    card_bytes = await build_card("Заголовок", ["Строка первая", "Строка вторая"])

    image = Image.open(BytesIO(card_bytes))
    assert image.format == "PNG"
    assert image.size == CARD_SIZE


async def test_build_card_works_with_no_body_lines():
    card_bytes = await build_card("Только заголовок", [])

    image = Image.open(BytesIO(card_bytes))
    assert image.format == "PNG"
    assert image.size == CARD_SIZE
