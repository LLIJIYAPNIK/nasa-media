from __future__ import annotations

_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (10, "с городской автобус"),
    (30, "с синего кита"),
    (50, "с половину футбольного поля"),
    (110, "с футбольное поле"),
    (330, "с Эйфелеву башню"),
    (830, "с Останкинскую башню в три раза"),
)


def compare_to_familiar_object(diameter_m: float) -> str:
    for threshold, label in _THRESHOLDS:
        if diameter_m <= threshold:
            return f"примерно {label}"
    _, largest_label = _THRESHOLDS[-1]
    return f"крупнее, чем {largest_label}"
