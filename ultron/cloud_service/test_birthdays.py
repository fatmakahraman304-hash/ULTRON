"""Yearly reminders and birthdays."""
import asyncio
import unittest
from datetime import datetime, timezone

import birthday_skills as bd
import instant_skills as s
import reminders as rem

NOW = datetime(2026, 10, 21, 14, 5, tzinfo=timezone.utc)   # 21 Oct 2026, 17:05 Istanbul


def run(c):
    return asyncio.run(c)


class Yearly(unittest.TestCase):
    def test_rule_and_next_occurrence(self):
        p = rem.parse_reminder("her yıl 14 şubat sevgililer gününü hatırlat", NOW)
        self.assertEqual(p["repeat"], "yearly:02-14")
        self.assertEqual(f"{p['due']:%Y-%m-%d %H:%M}", "2027-02-14 09:00")
        self.assertEqual(p["text"], "sevgililer gününü")
        self.assertIn("her yıl 14 Şubat", p["when"])

    def test_leap_day_waits_for_a_leap_year(self):
        due = rem.next_occurrence("yearly:02-29", 9, 0, NOW)
        self.assertEqual((due.year, due.month, due.day), (2028, 2, 29))

    def test_yearly_requeue_keeps_the_date(self):
        inserted = []

        class Pool:
            async def execute(self, sql, *a):
                inserted.append(a)
        due = datetime(2027, 2, 14, 6, 0, tzinfo=timezone.utc)
        run(rem.reschedule_repeats(Pool(), [{"user_id": "u", "text": "x", "due_at": due, "repeat_rule": "yearly:02-14"}], datetime(2027, 2, 14, 7, tzinfo=timezone.utc)))
        self.assertEqual(inserted[0][2].astimezone(rem.HOME_TZ).strftime("%Y-%m-%d %H:%M"), "2028-02-14 09:00")


class Birthdays(unittest.TestCase):
    def test_genitive_vowel_harmony(self):
        cases = {"Ahmet": "Ahmet'in", "Murat": "Murat'ın", "Ayşe": "Ayşe'nin", "Ali": "Ali'nin", "Ömer": "Ömer'in", "Okan": "Okan'ın",
                 "Ufuk": "Ufuk'un", "Selma": "Selma'nın", "Güler": "Güler'in", "Duygu": "Duygu'nun"}
        for name, want in cases.items():
            self.assertEqual(bd.genitive(name), want)

    def test_detection_does_not_steal_chat(self):
        for text in ("doğum günü hediyesi öner", "doğum günü partisi nasıl planlanır", "bugün benim doğum günüm", "doğum günün kutlu olsun"):
            self.assertFalse(bd.wants_birthdays(text), text)
        for text in ("Ahmet'in doğum günü 3 Mart", "Ayşe'nin doğum günü 15.06", "doğum günü ekle: Ali 20 Aralık", "doğum günüm 5 mayıs", "doğum günlerim"):
            self.assertTrue(bd.wants_birthdays(text), text)


class Pool:
    def __init__(self, existing=0, rows=()):
        self.inserted, self.existing, self.rows = [], existing, list(rows)

    async def fetchval(self, sql, *a):
        return self.existing

    async def execute(self, sql, *a):
        self.inserted.append(a)

    async def fetch(self, sql, *a):
        return self.rows


def say(pool, text):
    out = run(s.instant_reply(text, pool=pool, user_id="u", now=NOW))
    return out["reply"] if out else None


class Flow(unittest.TestCase):
    def test_creates_day_of_and_eve_yearly_reminders(self):
        pool = Pool()
        reply = say(pool, "Murat'ın doğum günü 3 Mart")
        self.assertIn("Murat'ın doğum günü: 3 Mart", reply)
        self.assertEqual(len(pool.inserted), 2)
        (_, t1, d1, r1), (_, t2, d2, r2) = pool.inserted
        self.assertEqual((t1, r1, d1.astimezone(rem.HOME_TZ).strftime("%m-%d %H:%M")), ("🎂 Murat'ın doğum günü bugün!", "yearly:03-03", "03-03 09:00"))
        self.assertEqual((t2, r2, d2.astimezone(rem.HOME_TZ).strftime("%m-%d %H:%M")), ("🎂 Yarın Murat'ın doğum günü.", "yearly:03-02", "03-02 19:00"))

    def test_duplicate_invalid_and_mine(self):
        self.assertIn("zaten kayıtlı", say(Pool(existing=1), "Ali'nin doğum günü 20 aralık"))
        self.assertIn("geçerli görünmüyor", say(Pool(), "Ali'nin doğum günü 31 nisan"))
        pool = Pool()
        self.assertIn("Senin doğum günü: 5 Mayıs", say(pool, "doğum günüm 5 mayıs"))

    def test_list(self):
        rows = [{"text": "🎂 Murat'ın doğum günü bugün!", "due_at": datetime(2027, 3, 3, 6, 0, tzinfo=timezone.utc), "repeat_rule": "yearly:03-03"}]
        reply = say(Pool(rows=rows), "doğum günlerim")
        self.assertIn("• 3 Mart — Murat'ın (133 gün sonra)", reply)


if __name__ == "__main__":
    unittest.main()
