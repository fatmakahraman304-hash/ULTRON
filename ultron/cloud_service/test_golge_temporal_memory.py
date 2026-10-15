"""GÖLGE temporal saved-plan retrieval; no network, no model, no writes."""
from __future__ import annotations

import datetime
import unittest

from personal_context_focus import (
    _historical_plan_request,
    select_personal_context,
)


TODAY = datetime.date(2026, 10, 13)


def _plans():
    past = [
        {"title": f"Old unfinished task {i}",
         "scheduled_date": TODAY - datetime.timedelta(days=i),
         "scheduled_time": None,
         "note": "never send private note"}
        for i in range(1, 21)
    ]
    future = [
        {"title": "Mimarlık sınavı (owner-entered)",
         "scheduled_date": TODAY + datetime.timedelta(days=2),
         "scheduled_time": datetime.time(9, 30)},
        {"title": "Upcoming design review",
         "scheduled_date": TODAY + datetime.timedelta(days=3),
         "scheduled_time": None},
    ]
    # Historical first simulates the former DB ORDER BY ASC behavior.
    return list(reversed(past)) + future


class TemporalSavedPlanTests(unittest.TestCase):
    def test_future_date_beats_twenty_overdue_plans(self):
        rendered = select_personal_context([], _plans(), "Yarın planlarım?",
                                            max_chars=2800, today=TODAY)
        self.assertIn("Mimarlık sınavı (owner-entered)", rendered)
        self.assertIn("Upcoming design review", rendered)
        self.assertIn("2026-10-15 09:30", rendered)
        self.assertLess(rendered.index("Mimarlık sınavı"),
                        rendered.index("Old unfinished task"))
        self.assertIn("future date", rendered)
        self.assertNotIn("never send private note", rendered)

    def test_history_query_prefers_recent_past_and_does_not_rebrand_dates(self):
        self.assertTrue(_historical_plan_request("Geçmiş planlarımı göster"))
        self.assertTrue(_historical_plan_request("My past appointments"))
        rendered = select_personal_context([], _plans(),
                                            "Geçmiş planlarımı göster",
                                            max_chars=3000, today=TODAY)
        self.assertIn("Old unfinished task 1", rendered)
        self.assertIn("past date, not upcoming", rendered)
        self.assertNotIn("Old unfinished task 20", rendered)
        self.assertNotIn("Mimarlık sınavı", rendered)
        self.assertIn("no notification", rendered)

    def test_small_local_chat_context_prefers_only_next_two_dates(self):
        rendered = select_personal_context([], _plans(), "Merhaba",
                                            max_chars=1000, today=TODAY)
        self.assertIn("Mimarlık sınavı", rendered)
        self.assertIn("Upcoming design review", rendered)
        self.assertNotIn("Old unfinished task", rendered)
        self.assertLessEqual(len(rendered), 1000)

    def test_today_is_not_claimed_as_tomorrow_or_a_notification(self):
        plans = [{"title": "Today's appointment", "scheduled_date": TODAY,
                  "scheduled_time": None}]
        rendered = select_personal_context([], plans, "Bugün takvimim",
                                            today=TODAY)
        self.assertIn("OWNER PLAN - today", rendered)
        self.assertNotIn("future date", rendered)
        self.assertIn("no notification", rendered)

    def test_no_saved_data_uses_visible_golge_identity(self):
        self.assertEqual(select_personal_context([], [], "Merhaba",
                                                  today=TODAY),
                         "No saved GÖLGE memory or personal plans yet.")

    def test_explicit_preference_stays_despite_plan_backlog(self):
        memories = [{"category": "PREFERENCE", "key": "language",
                     "value": "Kısa Türkçe cevaplar"}]
        rendered = select_personal_context(memories, _plans(),
                                            "Yarın planım ne?", today=TODAY)
        self.assertIn("Kısa Türkçe cevaplar", rendered)
        self.assertIn("Mimarlık sınavı", rendered)

    def test_caps_and_inputs_are_not_mutated(self):
        plans = _plans()
        before = repr(plans)
        for cap in (0, 64, 140, 340, 950, 3400):
            rendered = select_personal_context([], plans,
                                                "Eski planlarım", today=TODAY,
                                                max_chars=cap)
            self.assertLessEqual(len(rendered), cap)
        self.assertEqual(repr(plans), before)


if __name__ == "__main__":
    unittest.main()
