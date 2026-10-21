"""Expense log from chat."""
import asyncio
import unittest
from datetime import date, datetime, timezone

import expense_skills as ex
import instant_skills as s

NOW = datetime(2026, 10, 21, 14, 5, tzinfo=timezone.utc)   # Wed 21 Oct 2026, 17:05 Istanbul


def run(c):
    return asyncio.run(c)


class Pool:
    def __init__(self, rows=()):
        self.inserted, self.rows, self.deleted = [], list(rows), False

    async def execute(self, sql, *a):
        self.inserted.append(a)

    async def fetch(self, sql, *a):
        self.query = a
        return self.rows

    async def fetchval(self, sql, *a):
        return None          # no budget configured

    async def fetchrow(self, sql, *a):
        self.deleted = True
        return {"amount": 80, "category": "kahve"}


def say(pool, text):
    out = run(s.instant_reply(text, pool=pool, user_id="u", now=NOW))
    return out["reply"] if out else None


class Expenses(unittest.TestCase):
    def test_add_variants(self):
        pool = Pool()
        self.assertIn("Kaydettim: 150 ₺ — market", say(pool, "150 lira market harcaması ekle"))
        self.assertEqual(pool.inserted[-1][1:4], (150.0, "market", ""))
        self.assertIn("80 ₺ — kahve", say(pool, "bugün kahveye 80 tl harcadım"))
        self.assertIn("1.250,5 ₺ — benzin", say(pool, "dün 1.250,50 lira benzin harcadım"))
        self.assertEqual(pool.inserted[-1][4], date(2026, 10, 20))      # "dün"
        self.assertIn("150 ₺ — market", say(pool, "harcama ekle 150 market"))
        self.assertIn("— fatura", say(pool, "faturaya 420 lira harcadım"))

    def test_turkish_characters_survive_in_category(self):
        pool = Pool()
        say(pool, "75 tl çiçek harcadım")
        self.assertEqual(pool.inserted[-1][2], "çiçek")

    def test_summary_periods(self):
        rows = [{"category": "market", "total": 900, "n": 3}, {"category": "kahve", "total": 240.5, "n": 4}]
        pool = Pool(rows)
        reply = say(pool, "bu ay ne kadar harcadım")
        self.assertIn("Bu ay toplam harcama: 1.140,5 ₺", reply)
        self.assertIn("• market: 900 ₺ (3 kayıt)", reply)
        self.assertEqual(pool.query[1:], (date(2026, 10, 1), date(2026, 10, 21)))
        say(pool, "bu hafta harcamalarım")
        self.assertEqual(pool.query[1], date(2026, 10, 19))             # Monday
        say(pool, "geçen ay ne kadar harcadım")
        self.assertEqual(pool.query[1:], (date(2026, 9, 1), date(2026, 9, 30)))
        self.assertIn("kayıtlı harcama yok", say(Pool(), "bugün ne kadar harcadım"))

    def test_undo_and_non_matches(self):
        pool = Pool()
        self.assertIn("Son harcamayı sildim: 80 ₺ (kahve)", say(pool, "son harcamayı sil"))
        for text in ("çok harcadım bugün", "bugün ne kadar harcayabilirim", "maaşım 25.000 tl", "100 dolar kaç tl"):
            self.assertFalse(ex.wants_expenses(text), text)


if __name__ == "__main__":
    unittest.main()
