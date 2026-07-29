from __future__ import annotations

# TODO: пороги ориентировочные (общеизвестные величины скорости звука,
# винтовочной пули, МКС, второй космической и орбитальной скорости Земли) —
# перед продовым использованием стоит свериться с авторитетным источником
# (см. docs/tz/TZ-asteroid-modal-details.md, «Решения»).
_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (0.34, "звук в воздухе"),
    (1.2, "винтовочную пулю"),
    (7.9, "МКС на орбите"),
    (11.2, "скорость убегания с Земли"),
    (29.8, "орбитальную скорость Земли вокруг Солнца"),
)


def compare_speed_to_familiar_reference(velocity_km_s: float) -> str:
    label = _THRESHOLDS[0][1]
    for threshold, threshold_label in _THRESHOLDS:
        if velocity_km_s < threshold:
            break
        label = threshold_label
    return f"быстрее, чем {label}"
