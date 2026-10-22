"""Repeating reminders and plan management from chat."""
import asyncio
import unittest
from datetime import date, datetime, time, timedelta, timezone

import instant_skills as s
import plan_skills as ps
import reminders as rem

NOW = datetime(2026, 10, 21, 14, 5, tzinfo=timezone.utc)  # Wednesday 17:05 Istanbul


def run(c):
    return asyncio.run(c)


class Repeat(unittest.TestCase):
    def parse(self, text):
        return rem.parse_reminder(text, NOW)

    def test_rules_and_first_occurrence(self):
        cases = {
            "her gün 9'da ilaç içmeyi hatırlat": ("daily", "2026-10-22 09:00"),
            "hafta içi her gün 08:30'da spora gitmeyi hatırlat": ("weekdays", "2026-10-22 08:30"),
            "her pazartesi 10:00'da raporu hatırlat": ("weekly:0", "2026-10-26 10:00"),
            "her ayın 5'inde saat 10'da kirayı hatırlat": ("monthly:5", "2026-11-05 10:00"),
            "her akşam 7'de yürüyüşü hatırlat": ("daily", "2026-10-21 19:00"),
            "hafta sonu 11'de kahvaltıyı hatırlat": ("weekends", "2026-10-24 11:00"),
        }
        for text, (rule, first) in cases.items():
            p = self.parse(text)
            self.assertEqual((p["repeat"], f"{p['due']:%Y-%m-%d %H:%M}"), (rule, first), text)

    def test_text_is_clean_and_one_off_unchanged(self):
        self.assertEqual(self.parse("her gün 9'da ilaç içmeyi hatırlat")["text"], "ilaç içmeyi")
        one = self.parse("20 dakika sonra su içmeyi hatırlat")
        self.assertIsNone(one["repeat"])
        self.assertEqual(one["text"], "su içmeyi")

    def test_next_occurrence_skips_weekend_and_short_months(self):
        fri = datetime(2026, 10, 23, 12, 0, tzinfo=rem.HOME_TZ)
        self.assertEqual(rem.next_occurrence("weekdays", 9, 0, fri).strftime("%a %d"), "Mon 26")
        jan31 = datetime(2026, 1, 31, 12, 0, tzinfo=rem.HOME_TZ)
        self.assertEqual(rem.next_occurrence("monthly:31", 9, 0, jan31).strftime("%m-%d"), "03-31")

    def test_reschedule_queues_next_same_wall_clock(self):
        inserted = []

        class Pool:
            async def execute(self, sql, *a):
                inserted.append(a)

        due = datetime(2026, 10, 21, 6, 0, tzinfo=timezone.utc)  # 09:00 Istanbul
        row = {"user_id": "u", "text": "ilaç", "due_at": due, "repeat_rule": "daily"}

        class R(dict):
            pass
        made = run(rem.reschedule_repeats(Pool(), [R(row), R({**row, "repeat_rule": None})], NOW))
        self.assertEqual(made, 1)
        self.assertEqual(inserted[0][2].astimezone(rem.HOME_TZ).strftime("%Y-%m-%d %H:%M"), "2026-10-22 09:00")


class PlanPool:
    def __init__(self, plans=()):
        self.plans, self.added, self.updated, self.deleted = list(plans), [], [], []

    async def fetch(self, sql, *a):
        return self.plans

    async def fetchval(self, sql, *a):
        if "INSERT INTO owner_plans" in sql:
            self.added.append(a)
            return len(self.added)
        return None

    async def execute(self, sql, *a):
        (self.deleted if "DELETE" in sql else self.updated).append(a)


class Plans(unittest.TestCase):
    def test_add_plan_with_date_and_time(self):
        pool = PlanPool()
        out = run(s.instant_reply("yarın 15:00 diş randevusu planıma ekle", pool=pool, user_id="u", now=NOW))
        self.assertEqual(out["skill"], "plans")
        user, title, day, clock = pool.added[0]
        self.assertEqual((title, day, clock), ("diş randevusu", date(2026, 10, 22), time(15, 0)))
        self.assertIn("22.10.2026 Perşembe 15:00", out["reply"])

    def test_plan_without_time_is_all_day_and_needs_a_date(self):
        pool = PlanPool()
        run(s.instant_reply("cuma günü takvimime araba bakımı ekle", pool=pool, user_id="u", now=NOW))
        self.assertEqual((pool.added[0][2], pool.added[0][3]), (date(2026, 10, 23), None))
        again = PlanPool()
        out = run(s.instant_reply("takvimime toplantı ekle", pool=again, user_id="u", now=NOW))
        self.assertEqual(again.added, [])
        self.assertIn("hangi gün", out["reply"].lower())

    def test_list_complete_delete_need_a_single_match(self):
        rows = [{"id": 1, "title": "Diş randevusu", "scheduled_date": date(2026, 10, 22), "scheduled_time": time(15, 0)},
                {"id": 2, "title": "Araba bakımı", "scheduled_date": date(2026, 10, 23), "scheduled_time": None},
                {"id": 3, "title": "Araba yıkama", "scheduled_date": date(2026, 10, 24), "scheduled_time": None}]
        pool = PlanPool(rows)
        self.assertIn("• 22.10.2026 Perşembe 15:00 — Diş randevusu", run(s.instant_reply("planlarım", pool=pool, user_id="u", now=NOW))["reply"])
        done = run(s.instant_reply("diş randevusu planını tamamla", pool=pool, user_id="u", now=NOW))["reply"]
        self.assertIn("tamamlandı", done)
        self.assertEqual(pool.updated[0][0], 1)
        many = run(s.instant_reply("araba planını sil", pool=pool, user_id="u", now=NOW))["reply"]
        self.assertIn("2 plan eşleşiyor", many)
        self.assertEqual(pool.deleted, [])
        run(s.instant_reply("araba bakımı planını sil", pool=pool, user_id="u", now=NOW))
        self.assertEqual(pool.deleted[0][0], 2)

    def test_today_plan_questions_still_go_to_agenda(self):
        self.assertEqual(run(s.instant_reply("bugün planlarım ne", pool=PlanPool(), user_id="u", now=NOW))["skill"], "agenda")


if __name__ == "__main__":
    unittest.main()
