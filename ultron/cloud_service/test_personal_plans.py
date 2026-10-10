"""Fast validations and truthful manual-calendar contracts."""
import sys
import unittest
from datetime import date, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from personal_plans import validate_plan, plan_dict
from personal_briefing import build_briefing


class PlanValidationTests(unittest.TestCase):
    def test_date_time_and_provenance(self):
        title, day, clock, note = validate_plan({
            "title": " İngilizce B2 ", "date": "2026-10-10",
            "time": "15:30", "note": "  Çalış  ",
        })
        self.assertEqual((title, day, clock, note),
                         ("İngilizce B2", date(2026, 10, 10), time(15, 30), "Çalış"))
        result = plan_dict({
            "id": 5, "title": title, "scheduled_date": day,
            "scheduled_time": clock, "is_done": False, "note": note,
        })
        self.assertEqual(result["scheduled_date"], "2026-10-10")
        self.assertEqual(result["scheduled_time"], "15:30")
        self.assertEqual(result["source"], "owner_created_plan")

    def test_optional_time_and_empty_note(self):
        _, _, clock, note = validate_plan({"title": "Proje", "date": "2026-10-11"})
        self.assertIsNone(clock)
        self.assertEqual(note, "")

    def test_rejects_bad_dates_and_times(self):
        for when, clock in [
            ("2026-02-30", ""), ("2026-3-1", ""), ("2026-10-11", "24:30"),
            ("2026-10-11", "10:66"), ("2026-10-11", "10:00Z"),
            ("2026-10-11", "12:34:56"),
        ]:
            with self.subTest(when=when, clock=clock), self.assertRaises(ValueError):
                validate_plan({"title": "Plan", "date": when, "time": clock})

    def test_rejects_injected_nul_and_long_fields(self):
        for payload in [
            {}, [], {"title": "", "date": "2026-10-11"},
            {"title": "a" * 141, "date": "2026-10-11"},
            {"title": "a" + chr(0) + "b", "date": "2026-10-11"},
            {"title": "Plan", "date": "2026-10-11", "note": "z" * 501},
            {"title": "Plan", "date": "2026-10-11", "note": {"fake": True}},
        ]:
            with self.subTest(payload=str(payload)[:30]), self.assertRaises(ValueError):
                validate_plan(payload)

    def test_briefing_includes_only_manual_pending_plans(self):
        plans = [
            {"id": 11, "title": "Yarın ders", "scheduled_date": date(2026, 10, 11),
             "scheduled_time": time(10, 0), "is_done": False},
            {"id": 12, "title": "Bitti", "scheduled_date": date(2026, 10, 12),
             "scheduled_time": None, "is_done": True},
        ]
        result = build_briefing([], plan_rows=plans)
        self.assertEqual(len(result["plans"]), 1)
        self.assertEqual(result["plans"][0]["source"], "owner_created_plan")
        self.assertFalse(result["calendar_connected"])
        self.assertFalse(result["reminders_created"])

    def test_model_context_excludes_private_notes(self):
        app = (HERE / "app.py").read_text(encoding="utf-8")
        from_pos = app.index("async def _memory_context(")
        until_pos = app.index("async def _recent_context(")
        helper = app[from_pos:until_pos]
        self.assertIn("load_focused_owner_context(pool, user_id, query)", helper)
        focused = (HERE / "personal_context_focus.py").read_text(encoding="utf-8")
        self.assertIn("SELECT title,scheduled_date,scheduled_time FROM owner_plans", focused)
        self.assertIn("WHERE user_id=$1 AND is_done=FALSE", focused)
        self.assertIn("OWNER PLAN - no notification", focused)
        self.assertNotIn("SELECT title,note", focused)

    def test_routes_use_scoped_user_and_browser_write(self):
        app = (HERE / "app.py").read_text(encoding="utf-8")
        code = (HERE / "personal_plans.py").read_text(encoding="utf-8")
        self.assertIn("register_personal_plan_routes(app)", app)
        self.assertIn("WHERE id=$1 AND user_id=$2", code)
        self.assertIn('request["user_id"]', code)
        self.assertIn('request.get("auth_kind") != "web"', code)
        self.assertIn('"external_calendar_connected": False', code)
        self.assertIn('"notification_sent": False', code)
        self.assertIn('request.method in ("POST", "PUT", "PATCH", "DELETE")', code)
        self.assertIn('request.method in ("POST", "PUT", "PATCH")', code)
        self.assertIn('app.router.add_put("/api/owner-plans/{id}", update_plan)', code)
        self.assertIn("UPDATE owner_plans SET title=$3,scheduled_date=$4,scheduled_time=$5,", code)


if __name__ == "__main__":
    unittest.main()
