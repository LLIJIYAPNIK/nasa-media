from __future__ import annotations

from datetime import date

from domain.media.value_objects import InvalidMediaDate, ensure_within_bounds


def parse_requested_date(text: str | None, lower_bound: date, today: date) -> date:
    """Общий разбор даты для всех FSM-сценариев APOD/EPIC — один формат
    ошибки вместо повторяющегося try/except в каждом хендлере. `text` может
    быть None, если пользователь прислал не текст (фото, стикер) вместо
    даты — это тот же случай, что и неверный формат."""
    if text is None:
        raise InvalidMediaDate("Неверный формат даты. Используйте ГГГГ-ММ-ДД")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as error:
        raise InvalidMediaDate("Неверный формат даты. Используйте ГГГГ-ММ-ДД") from error
    ensure_within_bounds(parsed, lower_bound, today)
    return parsed
