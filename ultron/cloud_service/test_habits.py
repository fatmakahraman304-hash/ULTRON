"""Habit & health log."""
import asyncio
import unittest
from datetime import date, datetime, timezone

import habit_skills as hs
import instant_skills as s

NOW = datetime(2026, 10, 21, 14, 5, tzinfo=timezone.utc)   # Wed 21 Oct 2026


def run(c):
    return asyncio.run(c)


class Parse(unittest.TestCase):
    def test_logging_sentences(self):
        cases = {
            "2 bardak su içtim": ("water", 2.0), "su içtim": ("water", 1.0), "1 litre su içtim": ("water", 4.0), "yarım litre su içtim": ("water", 2.0),
            "7 saat uyudum": ("sleep", 7.0), "uyudum 7,5 saat": ("sleep", 7.5), "30 dakika yürüdüm": ("exercise", 30.0), "yürüdüm 45 dakika": ("exercise", 45.0),
            "1 saat koştum": ("exercise", 60.0), "8000 adım attım": ("steps", 8000.0), "kilom 72,5": ("weight", 72.5), "72,5 kilo oldum": ("weight", 72.5),
            "modum 4": ("mood", 4.0), "bugün modum 5/5": ("mood", 5.0),
        }
        for text, (habit, amount) in cases.items():
            got = hs.parse_log(text)
            self.assertEqual((got[0], got[1]), (habit, amount), text)

    def test_sports_are_named_in_turkish(self):
        self.assertEqual(hs.parse_log("30 dakika yürüdüm")[2], "yürüyüş")
        self.assertEqual(hs.parse_log("45 dakika yoga yaptım")[2], "yoga")

    def test_not_a_log(self):
        for text in ("çok su içtim", "su içmek sağlıklı mı", "dün gece kötü uyudum", "kilom çok fazla", "modum 9", "7 saat uyudum ama yine yorgunum bugün çok", "kilom 5"):
            self.assertIsNone(hs.parse_log(text), text)


class Pool:
    def __init__(self, total=3.0, rows=(), prev_weight=None):
        self.inserted, self.total, self.rows, self.prev = [], total, list(rows), prev_weight

    async def execute(self, sql, *a):
        self.inserted.append(a)

    async def fetchval(self, sql, *a):
        if "habit='weight'" in sql:
            return self.prev
        return self.total

    async def fetch(self, sql, *a):
        self.query = a
        return self.rows

    async def fetchrow(self, sql, *a):
        return {"habit": "water", "amount": 2.0}


def say(pool, text):
    out = run(s.instant_reply(text, pool=pool, user_id="u", now=NOW))
    return out["reply"] if out else None


class Flow(unittest.TestCase):
    def test_water_progress_and_goal(self):
        pool = Pool(total=5)
        reply = say(pool, "2 bardak su içtim")
        self.assertIn("+2 bardak", reply)
        self.assertIn("5/8 bardak", reply)
        self.assertIn("%62", reply)
        self.assertEqual(pool.inserted[0][1:4], ("water", 2.0, "bardak"))
        self.assertIn("Hedefe ulaştın", say(Pool(total=8), "su içtim"))

    def test_yesterday_and_sleep_tip_and_weight_diff(self):
        pool = Pool()
        say(pool, "dün 7 saat uyudum")
        self.assertEqual(pool.inserted[0][4], date(2026, 10, 20))
        self.assertIn("erken yatmayı", say(Pool(total=5), "5 saat uyudum"))
        self.assertIn("(öncekine göre -1,5 kg)", say(Pool(prev_weight=74.0), "kilom 72,5"))

    def test_summaries(self):
        rows = [{"habit": "water", "total": 22, "avg": 3.7, "days": 6}, {"habit": "sleep", "total": 40, "avg": 6.7, "days": 6},
                {"habit": "exercise", "total": 150, "avg": 30, "days": 5}, {"habit": "mood", "total": 20, "avg": 3.8, "days": 5}]
        pool = Pool(rows=rows)
        reply = say(pool, "bu hafta ne kadar spor yaptım")
        self.assertIn("Bu hafta özeti", reply)
        self.assertIn("💧 Su: 22 bardak", reply)
        self.assertIn("😴 Uyku: ortalama 6,7 saat", reply)
        self.assertEqual(pool.query[1], date(2026, 10, 19))
        self.assertIn("kayıt yok", say(Pool(), "bugün kaç bardak su içtim"))

    def test_undo(self):
        self.assertIn("Son kaydı sildim: 💧 Su 2", say(Pool(), "son su kaydını sil"))


if __name__ == "__main__":
    unittest.main()
