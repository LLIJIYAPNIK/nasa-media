from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_

from domain.digest.value_objects import AsteroidHighlight, EarthEventHighlight, SpaceWeatherHighlight

# GST > FLR > CME > IPS > RBE — приоритет «главного» события за день. Report
# (еженедельный сводный мета-документ, не событие дня) сознательно не входит
# в список и никогда не выбирается (см. docs/tz/TZ-daily-digest.md).
SPACE_WEATHER_PRIORITY = ("GST", "FLR", "CME", "IPS", "RBE")
_SPACE_WEATHER_RANK = {message_type: rank for rank, message_type in enumerate(SPACE_WEATHER_PRIORITY)}

_SPACE_WEATHER_LABELS = {
    "GST": "🧲 Геомагнитная буря",
    "FLR": "☀️ Солнечная вспышка",
    "CME": "💨 Выброс корональной массы",
    "IPS": "🌊 Межпланетная ударная волна",
    "RBE": "⚡ Всплеск релятивистских электронов",
}


def pick_significant_space_weather(events: Sequence[SpaceWeatherHighlight]) -> SpaceWeatherHighlight | None:
    relevant = [event for event in events if event.message_type in _SPACE_WEATHER_RANK]
    if not relevant:
        return None
    # Приоритет типа важнее свежести (первый ключ), при равном типе — самое
    # позднее уведомление (второй ключ, со знаком минус — min ищет наименьшее).
    return min(relevant, key=lambda event: (_SPACE_WEATHER_RANK[event.message_type], -event.issued_at.timestamp()))


def pick_closest_asteroid(asteroids: Sequence[AsteroidHighlight]) -> AsteroidHighlight | None:
    if not asteroids:
        return None
    return min(asteroids, key=lambda asteroid: asteroid.miss_distance_km)


def pick_latest_earth_event(events: Sequence[EarthEventHighlight]) -> EarthEventHighlight | None:
    if not events:
        return None
    return max(events, key=lambda event: event.event_date)


def _format_space_weather(highlight: SpaceWeatherHighlight | None) -> str:
    if highlight is None:
        return "🌤 Космос сегодня спокоен."
    label = _SPACE_WEATHER_LABELS.get(highlight.message_type, highlight.message_type)
    return f"{label} (NASA DONKI)."


def _format_asteroid(highlight: AsteroidHighlight | None) -> str:
    if highlight is None:
        return "☄️ Заметных астероидов сегодня нет."
    size = f"{round(highlight.diameter_min_m)}–{round(highlight.diameter_max_m)} м"
    hazard = " ⚠️ потенциально опасен" if highlight.is_hazardous else ""
    return (
        f"☄️ Ближайший астероид: {highlight.name}, {size}, "
        f"пролетит на {highlight.miss_distance_lunar:.1f} лунных расстояниях{hazard}."
    )


def _format_earth_event(highlight: EarthEventHighlight | None) -> str:
    if highlight is None:
        return "🌍 Заметных событий на Земле сегодня нет."
    return f"🌍 {highlight.title} ({highlight.category})."


def build_digest_text(
    day: date_,
    space_weather: SpaceWeatherHighlight | None,
    asteroid: AsteroidHighlight | None,
    earth_event: EarthEventHighlight | None,
    apod_cached: bool,
) -> str:
    lines = [
        f"🌌 Сводка за {day.isoformat()}",
        "",
        _format_space_weather(space_weather),
        _format_asteroid(asteroid),
        _format_earth_event(earth_event),
    ]
    if apod_cached:
        lines.append("")
        lines.append("🖼 Картинка дня APOD уже готова — загляни в раздел APOD!")
    return "\n".join(lines)
