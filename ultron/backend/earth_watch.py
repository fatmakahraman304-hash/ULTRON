"""Pure, dependency-free validation for persistent Earth Watch state.

Never trust JSON saved in center_stage.json or arbitrary stage command input.
This module intentionally imports no backend runtime components, so it can be
regression-tested without starting ULTRON, loading models or accessing devices.
"""
from __future__ import annotations

import math
import re
from typing import Any

EARTH_DEFAULTS = {
    "auto_rotate": True,
    "rotation_speed": 0.08,
    "clouds": True,
    "atmosphere": True,
    "stars": True,
    "grid": False,
    "night": False,
    "live_iss": False,
    "focus_lat": 20.0,
    "focus_lon": 0.0,
    "focus_label": "GLOBAL",
    "markers": [],
}
EARTH_BOOLEAN_KEYS = (
    "auto_rotate", "clouds", "atmosphere", "stars", "grid", "night", "live_iss",
)
_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,48}$")


def earth_boolean(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and math.isfinite(value):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on", "enabled"}:
            return True
        if normalized in {"false", "0", "no", "off", "disabled"}:
            return False
    return default


def earth_number(value: Any, default: float, lower: float, upper: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return float(default)
    if not math.isfinite(number):
        return float(default)
    return max(lower, min(upper, number))


def earth_longitude(value: Any, default: float = 0.0) -> float:
    number = earth_number(value, default, -10**10, 10**10)
    longitude = ((number + 180) % 360 + 360) % 360 - 180
    return 0.0 if longitude == 0 else longitude


def earth_text(value: Any, default: str, length: int = 80) -> str:
    if not isinstance(value, str):
        return default
    clean = "".join(c for c in value.strip() if c.isprintable())
    return clean[:length] or default


def earth_color(value: Any) -> str:
    if isinstance(value, str) and _COLOR_PATTERN.fullmatch(value):
        return value
    return "#ff334d"


def normalize_earth_state(raw: Any) -> dict:
    """Normalize state loaded from disk, including at most 64 safe markers."""
    source = raw if isinstance(raw, dict) else {}
    state = dict(EARTH_DEFAULTS)
    for key in EARTH_BOOLEAN_KEYS:
        state[key] = earth_boolean(source.get(key), bool(EARTH_DEFAULTS[key]))
    state["rotation_speed"] = earth_number(source.get("rotation_speed"), 0.08, 0, 1.5)
    state["focus_lat"] = earth_number(source.get("focus_lat"), 20.0, -90, 90)
    state["focus_lon"] = earth_longitude(source.get("focus_lon"), 0.0)
    state["focus_label"] = earth_text(source.get("focus_label"), "GLOBAL")
    raw_markers = source.get("markers")
    markers: list[dict] = []
    ids: set[str] = set()
    if isinstance(raw_markers, list):
        for item in raw_markers[-64:]:
            if not isinstance(item, dict):
                continue
            marker_id = item.get("id")
            if not isinstance(marker_id, str) or not _ID_PATTERN.fullmatch(marker_id) or marker_id in ids:
                continue
            ids.add(marker_id)
            markers.append({
                "id": marker_id,
                "lat": earth_number(item.get("lat"), 0.0, -90, 90),
                "lon": earth_longitude(item.get("lon"), 0.0),
                "label": earth_text(item.get("label"), "MARKER"),
                "color": earth_color(item.get("color")),
            })
    state["markers"] = markers
    return state


def add_earth_marker(state: dict, values: dict, marker_id: str) -> dict:
    if not isinstance(marker_id, str) or not _ID_PATTERN.fullmatch(marker_id):
        raise ValueError("invalid marker ID")
    marker = {
        "id": marker_id,
        "lat": earth_number(values.get("lat"), 0.0, -90, 90),
        "lon": earth_longitude(values.get("lon"), 0.0),
        "label": earth_text(values.get("label"), "MARKER"),
        "color": earth_color(values.get("color")),
    }
    current = [dict(m) for m in state.get("markers", []) if isinstance(m, dict) and m.get("id") != marker_id]
    state["markers"] = (current + [marker])[-64:]
    return marker


def remove_earth_marker(state: dict, marker_id: str) -> bool:
    before = len(state.get("markers", []))
    state["markers"] = [m for m in state.get("markers", []) if m.get("id") != marker_id]
    return len(state["markers"]) < before
