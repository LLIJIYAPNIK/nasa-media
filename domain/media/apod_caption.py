from __future__ import annotations

from datetime import date as date_


def build_apod_caption(day: date_, title: str, description: str, copyright_holder: str | None = None) -> str:
    """Собирает подпись APOD. Если NASA прислали `copyright` — картинка не
    public domain, а работа стороннего автора, показанная с разрешения:
    добавляем атрибуцию отдельной строкой (см. docs/tz/TZ-copyright.md)."""
    caption = f"{day}\n\n{title}\n{description}"

    normalized_copyright = " ".join(copyright_holder.split()) if copyright_holder else ""
    if normalized_copyright:
        caption += f"\n\n© {normalized_copyright}"

    return caption
