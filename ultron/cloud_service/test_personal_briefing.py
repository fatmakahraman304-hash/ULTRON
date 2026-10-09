"""Unit contracts for explicit owner-memory daily briefing."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from personal_briefing import build_briefing


class TestPersonalBriefing(unittest.TestCase):
    def test_no_memory_does_not_invent_appointments(self):
        result = build_briefing([])
        self.assertEqual(result["items"], [])
        self.assertFalse(result["calendar_connected"])
        self.assertFalse(result["reminders_created"])
        self.assertFalse(result["actions_executed"])

    def test_only_supplied_memories_and_explicit_source(self):
        rows = [
            {"category": "GOAL", "key": "english", "value": "B2 çalış"},
            {"category": "PROJECT", "key": "ultron", "value": "Ses gecikmesini ölç"},
        ]
        r = build_briefing(rows)
        self.assertEqual(len(r["items"]), 2)
        self.assertEqual(r["items"][0]["source"], "owner_saved_memory")
        self.assertEqual(r["items"][1]["value"], "Ses gecikmesini ölç")

    def test_deduplicate_and_bounded(self):
        rows = [{"category": "GOAL", "key": "X", "value": "Önemli"}] * 30
        rows += [{"category": "GOAL", "key": str(i), "value": "v" * 1000} for i in range(30)]
        result = build_briefing(rows, max_items=8)
        self.assertEqual(len(result["items"]), 8)
        self.assertLessEqual(len(result["items"][-1]["value"]), 300)

    def test_api_is_user_scoped_and_read_only(self):
        app = (HERE / "app.py").read_text(encoding="utf-8")
        self.assertIn('app.router.add_get("/api/personal-briefing", personal_briefing_api)', app)
        self.assertIn('"ORDER BY updated_at DESC LIMIT 40", request["user_id"]', app)
        self.assertIn('return web.json_response(build_briefing(rows, plan_rows=plans))', app)
        self.assertIn("FROM owner_plans WHERE user_id=$1 AND is_done=FALSE", app)


if __name__ == "__main__":
    unittest.main()
