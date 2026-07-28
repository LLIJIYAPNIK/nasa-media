from __future__ import annotations

from datetime import date as date_

# Первый выпуск APOD, "Neutron Star Earth" — apod.nasa.gov/apod/ap950616.html.
# NASA публикует APOD ежедневно без перерыва с этой даты (см. docs/tz/TZ-web.md,
# «Ежедневная статистика»).
APOD_LAUNCH_DATE = date_(1995, 6, 16)


def days_since_apod_launch(today: date_) -> int:
    return (today - APOD_LAUNCH_DATE).days
