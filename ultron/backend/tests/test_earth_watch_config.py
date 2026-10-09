"""Earth Watch state validation: no external models, display, network or tokens."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from earth_watch import (
    EARTH_DEFAULTS, add_earth_marker, earth_boolean, earth_color,
    earth_longitude, earth_number, normalize_earth_state, remove_earth_marker,
)


class EarthWatchConfigTests(unittest.TestCase):
    def test_boolean_strings_are_not_truthy_by_accident(self):
        for value in ("false", "False", "0", "off", "NO", "disabled", 0):
            self.assertFalse(earth_boolean(value, True))
        for value in ("true", "TRUE", "1", "on", "yes", 1):
            self.assertTrue(earth_boolean(value, False))
        self.assertTrue(earth_boolean("nonsense", True))
        self.assertFalse(earth_boolean("nonsense", False))

    def test_invalid_numeric_input_never_leaks_nonfinite_values(self):
        for value in ("nan", "inf", float("nan"), float("inf"), None, [], {}):
            self.assertEqual(earth_number(value, 23, -90, 90), 23)
        self.assertEqual(earth_number(1000, 0, -90, 90), 90)
        self.assertEqual(earth_number(-1000, 0, -90, 90), -90)
        self.assertEqual(earth_longitude(190), -170)
        self.assertEqual(earth_longitude(-540), -180)

    def test_invalid_or_oversized_persisted_markers_get_sanitized(self):
        raw = {
            "auto_rotate": "false",
            "night": "true",
            "focus_lat": "nan",
            "focus_lon": 190,
            "markers": [
                None, {"id": "../bad", "lat": 1, "lon": 2},
                {"id": "a", "lat": float("inf"), "lon": 390, "label": "City\x00Name", "color": "url(secret)"},
                {"id": "a", "lat": 10, "lon": 20},
                {"id": "b", "lat": -1000, "lon": -181, "color": "#abcdef"},
            ],
            "unauthorized_extra": "ignore",
        }
        result = normalize_earth_state(raw)
        self.assertFalse(result["auto_rotate"])
        self.assertTrue(result["night"])
        self.assertEqual(result["focus_lat"], 20)
        self.assertEqual(result["focus_lon"], -170)
        self.assertNotIn("unauthorized_extra", result)
        self.assertEqual([m["id"] for m in result["markers"]], ["a", "b"])
        self.assertEqual(result["markers"][0]["lat"], 0)
        self.assertEqual(result["markers"][0]["lon"], 30)
        self.assertEqual(result["markers"][0]["label"], "CityName")
        self.assertEqual(result["markers"][0]["color"], "#ff334d")
        self.assertEqual(result["markers"][1]["lat"], -90)
        self.assertEqual(result["markers"][1]["lon"], 179)

    def test_limit_64_markers_and_mutations(self):
        state = normalize_earth_state({"markers": [{"id": str(i), "lat": 1, "lon": 2} for i in range(80)]})
        self.assertEqual(len(state["markers"]), 64)
        self.assertEqual(state["markers"][0]["id"], "16")
        marker = add_earth_marker(state, {"lat": "bad", "lon": 540, "color": "red"}, "fresh")
        self.assertEqual(marker["lat"], 0)
        self.assertEqual(marker["lon"], -180)
        self.assertEqual(marker["color"], "#ff334d")
        self.assertEqual(len(state["markers"]), 64)
        self.assertTrue(remove_earth_marker(state, "fresh"))
        self.assertFalse(remove_earth_marker(state, "fresh"))
        with self.assertRaises(ValueError):
            add_earth_marker(state, {}, "../outside")

    def test_defaults_are_stable(self):
        result = normalize_earth_state(None)
        self.assertEqual(set(result), set(EARTH_DEFAULTS))
        self.assertEqual(result["markers"], [])
        self.assertEqual(result["focus_label"], "GLOBAL")
        self.assertTrue(math.isfinite(result["rotation_speed"]))


if __name__ == "__main__":
    unittest.main()
