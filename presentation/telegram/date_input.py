from __future__ import annotations

from datetime import date

from domain.media.value_objects import InvalidMediaDate, ensure_within_bounds

INVALID_FORMAT_MESSAGE = "Неверный формат даты. Используйте ГГГГ-ММ-ДД"
BIRTHDAY_LOWER_BOUND = date(1900, 1, 1)


def _parse_iso_date(text: str | None) -> date:
    """`text` может быть None, если пользователь прислал не текст (фото,
    стикер) вместо даты — это тот же случай, что и неверный формат."""
    if text is None:
        raise InvalidMediaDate(INVALID_FORMAT_MESSAGE)
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise InvalidMediaDate(INVALID_FORMAT_MESSAGE) from error


def parse_requested_date(text: str | None, lower_bound: date, today: date) -> date:
    """Общий разбор даты для сценариев APOD/EPIC «дата медиа» — один формат
    ошибки вместо повторяющегося try/except в каждом хендлере."""
    parsed = _parse_iso_date(text)
    ensure_within_bounds(parsed, lower_bound, today)
    return parsed


def parse_birthday_date(text: str | None) -> date:
    """Дата рождения не привязана к APOD_LOWER_BOUND — она должна
    сохраняться независимо от того, публиковало ли NASA APOD в этот день
    (см. docs/tz/TZ-birthday.md, решение B). Валидация — только «не в
    будущем» и разумная нижняя граница."""
    parsed = _parse_iso_date(text)
    today = date.today()
    if parsed > today:
        raise InvalidMediaDate("Дата рождения не может быть в будущем")
    if parsed < BIRTHDAY_LOWER_BOUND:
        raise InvalidMediaDate(f"Минимальная дата — {BIRTHDAY_LOWER_BOUND.isoformat()}")
    return parsed
