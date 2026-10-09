"""No-provider unit tests for ten JARVIS capability readiness claims."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from capability_readiness import readiness


class TestReadiness(unittest.TestCase):
    def test_all_ten_features_have_distinct_ids(self):
        items = readiness()["capabilities"]
        self.assertEqual(len(items), 10)
        self.assertEqual(len({x["id"] for x in items}), 10)

    def test_offline_computer_is_never_marked_available(self):
        for online in (False, True):
            result = readiness(online)
            item = next(x for x in result["capabilities"] if x["id"] == "offline_computer")
            self.assertEqual(item["status"], "blocked_hardware")
            self.assertEqual(result["desktop_online"], online)

    def test_no_false_ios_hologram_consciousness_claims(self):
        items = {x["id"]: x for x in readiness()["capabilities"]}
        self.assertEqual(items["native_iphone"]["status"], "requires_native_setup")
        self.assertEqual(items["physical_hologram"]["status"], "blocked_hardware")
        self.assertIn("bilinci", items["expressive_persona"]["detail"])

    def test_connector_and_smart_home_are_not_claimed_active(self):
        items = {x["id"]: x for x in readiness()["capabilities"]}
        self.assertEqual(items["calendar_email"]["status"], "requires_provider")
        self.assertEqual(items["smart_devices"]["status"], "requires_devices")
        self.assertFalse(readiness()["verified_device_test"])

    def test_api_is_authenticated_and_read_only(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('app.router.add_get("/api/capability-readiness", capability_readiness_api)', app)
        self.assertIn('request.get("auth_kind") not in ("web", "device")', app)
        self.assertIn("FROM device_presence WHERE user_id=$1 AND device='desktop'", app)
        self.assertIn("return web.json_response(readiness(bool(desktop_online)))", app)


if __name__ == "__main__":
    unittest.main()
