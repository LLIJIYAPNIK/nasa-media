from datetime import date, datetime

import pytest

from domain.digest.digest_text import (
    build_digest_lines,
    build_digest_text,
    build_weekly_highlights_lines,
    pick_closest_asteroid,
    pick_largest_asteroid,
    pick_latest_earth_event,
    pick_significant_space_weather,
)
from domain.digest.value_objects import AsteroidHighlight, EarthEventHighlight, SpaceWeatherHighlight

DAY = date(2026, 7, 27)


def _space_weather(message_type: str, issued_at: datetime) -> SpaceWeatherHighlight:
    return SpaceWeatherHighlight(message_type=message_type, issued_at=issued_at)


def _asteroid(
    name: str, miss_distance_km: float, hazardous: bool = False, diameter_max_m: float = 20.0
) -> AsteroidHighlight:
    return AsteroidHighlight(
        name=name,
        diameter_min_m=10.0,
        diameter_max_m=diameter_max_m,
        miss_distance_km=miss_distance_km,
        miss_distance_lunar=miss_distance_km / 384_400,
        is_hazardous=hazardous,
    )


def _earth_event(title: str, event_date: datetime) -> EarthEventHighlight:
    return EarthEventHighlight(title=title, category="Wildfires", event_date=event_date)


# --- pick_significant_space_weather ---


def test_pick_space_weather_returns_none_when_empty():
    assert pick_significant_space_weather([]) is None


def test_pick_space_weather_ignores_report_type():
    events = [_space_weather("Report", datetime(2026, 7, 27, 12))]
    assert pick_significant_space_weather(events) is None


def test_pick_space_weather_respects_priority_order():
    events = [
        _space_weather("RBE", datetime(2026, 7, 27, 1)),
        _space_weather("GST", datetime(2026, 7, 27, 2)),
        _space_weather("FLR", datetime(2026, 7, 27, 3)),
    ]
    result = pick_significant_space_weather(events)
    assert result is not None
    assert result.message_type == "GST"


def test_pick_space_weather_takes_latest_among_same_type():
    events = [
        _space_weather("FLR", datetime(2026, 7, 27, 1)),
        _space_weather("FLR", datetime(2026, 7, 27, 23)),
        _space_weather("FLR", datetime(2026, 7, 27, 12)),
    ]
    result = pick_significant_space_weather(events)
    assert result is not None
    assert result.issued_at == datetime(2026, 7, 27, 23)


# --- pick_closest_asteroid ---


def test_pick_closest_asteroid_returns_none_when_empty():
    assert pick_closest_asteroid([]) is None


def test_pick_closest_asteroid_picks_minimal_distance():
    asteroids = [_asteroid("Far", 500_000), _asteroid("Near", 100_000), _asteroid("Mid", 300_000)]
    result = pick_closest_asteroid(asteroids)
    assert result is not None
    assert result.name == "Near"


# --- pick_largest_asteroid ---


def test_pick_largest_asteroid_returns_none_when_empty():
    assert pick_largest_asteroid([]) is None


def test_pick_largest_asteroid_picks_maximal_diameter_not_closest():
    asteroids = [
        _asteroid("Small", 100_000, diameter_max_m=10),
        _asteroid("Huge", 500_000, diameter_max_m=900),
        _asteroid("Medium", 300_000, diameter_max_m=100),
    ]
    result = pick_largest_asteroid(asteroids)
    assert result is not None
    assert result.name == "Huge"


# --- pick_latest_earth_event ---


def test_pick_latest_earth_event_returns_none_when_empty():
    assert pick_latest_earth_event([]) is None


def test_pick_latest_earth_event_picks_max_date():
    events = [
        _earth_event("Old storm", datetime(2026, 7, 20)),
        _earth_event("New storm", datetime(2026, 7, 27)),
    ]
    result = pick_latest_earth_event(events)
    assert result is not None
    assert result.title == "New storm"


# --- build_digest_text: 8 combinations of space/asteroid/earth presence ---


@pytest.mark.parametrize("has_space_weather", [True, False])
@pytest.mark.parametrize("has_asteroid", [True, False])
@pytest.mark.parametrize("has_earth_event", [True, False])
def test_build_digest_text_combinations(has_space_weather: bool, has_asteroid: bool, has_earth_event: bool):
    space_weather = _space_weather("GST", datetime(2026, 7, 27, 10)) if has_space_weather else None
    asteroid = _asteroid("Test", 200_000) if has_asteroid else None
    earth_event = _earth_event("Test event", datetime(2026, 7, 27)) if has_earth_event else None

    text = build_digest_text(DAY, space_weather, asteroid, earth_event, apod_cached=False)

    assert ("Геомагнитная буря" in text) is has_space_weather
    assert ("сегодня спокоен" in text) is not has_space_weather
    assert ("Ближайший астероид" in text) is has_asteroid
    assert ("астероидов сегодня нет" in text) is not has_asteroid
    assert ("примерно с синего кита" in text) is has_asteroid
    assert ("Test event" in text) is has_earth_event
    assert ("событий на Земле сегодня нет" in text) is not has_earth_event


def test_build_digest_text_includes_apod_line_when_cached():
    text = build_digest_text(DAY, None, None, None, apod_cached=True)

    assert "APOD" in text


def test_build_digest_text_omits_apod_line_when_not_cached():
    text = build_digest_text(DAY, None, None, None, apod_cached=False)

    assert "APOD" not in text


def test_build_digest_text_marks_hazardous_asteroid():
    text = build_digest_text(DAY, None, _asteroid("Dangerous", 100_000, hazardous=True), None, apod_cached=False)

    assert "потенциально опасен" in text


# --- build_digest_lines / build_digest_text regression ---


def test_build_digest_text_equals_joined_lines():
    args = (DAY, _space_weather("GST", datetime(2026, 7, 27, 10)), _asteroid("Test", 200_000), None)

    lines = build_digest_lines(*args, apod_cached=True)
    text = build_digest_text(*args, apod_cached=True)

    assert text == "\n".join(lines)


def test_build_digest_lines_returns_list_of_strings():
    lines = build_digest_lines(DAY, None, None, None, apod_cached=False)

    assert isinstance(lines, list)
    assert all(isinstance(line, str) for line in lines)


# --- build_weekly_highlights_lines ---

WEEK_START = date(2026, 7, 27)
WEEK_END = date(2026, 8, 2)


def test_build_weekly_highlights_lines_uses_largest_asteroid_wording():
    text = "\n".join(
        build_weekly_highlights_lines(
            WEEK_START, WEEK_END, None, _asteroid("Huge", 200_000, diameter_max_m=900), None
        )
    )

    assert "Самый крупный астероид недели" in text
    assert "Huge" in text


def test_build_weekly_highlights_lines_reports_no_notable_events_when_all_empty():
    text = "\n".join(build_weekly_highlights_lines(WEEK_START, WEEK_END, None, None, None))

    assert "этой неделе космос был спокоен" in text
    assert "астероидов на этой неделе не было" in text
    assert "событий на Земле на этой неделе не было" in text


def test_build_weekly_highlights_lines_includes_week_range_in_title():
    lines = build_weekly_highlights_lines(WEEK_START, WEEK_END, None, None, None)

    assert WEEK_START.isoformat() in lines[0]
    assert WEEK_END.isoformat() in lines[0]
