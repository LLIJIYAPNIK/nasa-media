from datetime import date

from domain.media.apod_caption import build_apod_caption

DAY = date(2024, 1, 1)


def test_caption_without_copyright_has_no_attribution_line():
    caption = build_apod_caption(DAY, "Title", "Description")

    assert caption == "2024-01-01\n\nTitle\nDescription"


def test_caption_with_copyright_appends_attribution_line():
    caption = build_apod_caption(DAY, "Title", "Description", "Jane Photographer")

    assert caption == "2024-01-01\n\nTitle\nDescription\n\n© Jane Photographer"


def test_caption_normalizes_whitespace_in_copyright():
    caption = build_apod_caption(DAY, "Title", "Description", "  Jane\nPhotographer  ")

    assert caption.endswith("© Jane Photographer")


def test_empty_copyright_string_is_treated_as_absent():
    caption = build_apod_caption(DAY, "Title", "Description", "")

    assert "©" not in caption


def test_whitespace_only_copyright_is_treated_as_absent():
    caption = build_apod_caption(DAY, "Title", "Description", "   ")

    assert "©" not in caption
