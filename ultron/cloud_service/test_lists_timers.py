"""Lists from chat and timers."""
import asyncio
import unittest
from datetime import datetime, timezone

import instant_skills as s
import reminders as rem

NOW = datetime(2026, 10, 21, 14, 5, tzinfo=timezone.utc)


def run(c):
    return asyncio.run(c)


class ListPool:
    """In-memory stand-in for owner_list_items."""
    def __init__(self):
        self.rows = []      # (id, list, item, key)
        self.n = 0

    async def fetchval(self, sql, *a):
        if "SELECT COUNT(*) FROM owner_list_items WHERE user_id=$1 AND list_name=$2" in sql:
            return sum(1 for r in self.rows if r[1] == a[1])
        if "COUNT(DISTINCT list_name)" in sql:
            return len({r[1] for r in self.rows})
        if "INSERT INTO owner_list_items" in sql:
            if any(r[1] == a[1] and r[3] == a[3] for r in self.rows):
                return None
            self.n += 1
            self.rows.append((self.n, a[1], a[2], a[3], a[4]))
            return self.n
        if "WITH d AS (DELETE" in sql:
            gone = [r for r in self.rows if r[1] == a[1]]
            self.rows = [r for r in self.rows if r[1] != a[1]]
            return len(gone)
        return None

    async def fetch(self, sql, *a):
        if "GROUP BY list_name" in sql:
            names = sorted({r[1] for r in self.rows})
            return [{"list_name": n, "label": next(r[4] for r in self.rows if r[1] == n), "n": sum(1 for r in self.rows if r[1] == n)} for n in names]
        if "item_key LIKE" in sql:
            prefix = a[2].rstrip("%")
            return [{"id": r[0], "item": r[2]} for r in self.rows if r[1] == a[1] and r[3].startswith(prefix)][:3]
        if "SELECT item FROM owner_list_items" in sql:
            return [{"item": r[2]} for r in self.rows if r[1] == a[1]]
        return []

    async def execute(self, sql, *a):
        if "DELETE FROM owner_list_items WHERE id" in sql:
            self.rows = [r for r in self.rows if r[0] != a[0]]


class Lists(unittest.TestCase):
    def say(self, pool, text):
        out = run(s.instant_reply(text, pool=pool, user_id="u", now=NOW))
        return out["reply"] if out else None

    def test_add_show_dedupe_remove_clear(self):
        pool = ListPool()
        self.assertIn("“alışveriş” listesine eklendi: süt, ekmek, yumurta", self.say(pool, "Alışveriş listesine süt, ekmek ve yumurta ekle"))
        self.assertIn("Zaten vardı: Süt", self.say(pool, "alışveriş listesine Süt ekle"))
        shown = self.say(pool, "alışveriş listem")
        self.assertIn("• ekmek", shown)
        self.assertIn("(3)", shown)
        self.assertTrue(shown.startswith("Alışveriş listen"))
        self.assertIn("çıkarıldı: ekmek", self.say(pool, "ekmek alışveriş listesinden çıkar"))
        self.assertIn("• alışveriş: 2 öğe", self.say(pool, "listelerim"))
        self.assertIn("2 öğe", self.say(pool, "alışveriş listesini temizle"))
        self.assertIsNone(self.say(pool, "alışveriş listem"))        # empty / unknown list is ordinary chat

    def test_item_before_list_name_and_original_case(self):
        pool = ListPool()
        self.say(pool, "Çiçek yapılacaklar listesine ekle")
        self.assertEqual([r[2] for r in pool.rows], ["Çiçek"])

    def test_limits(self):
        pool = ListPool()
        for i in range(100):
            pool.rows.append((i, "alisveris", f"x{i}", f"x{i}", "alışveriş"))
        self.assertIn("dolu", self.say(pool, "alışveriş listesine süt ekle"))


class Timers(unittest.TestCase):
    def test_timer_phrases(self):
        p = rem.parse_reminder("10 dakika zamanlayıcı kur", NOW)
        self.assertEqual((p["due"].minute, p["text"]), (15, "Zamanlayıcı süresi doldu ⏲"))
        p = rem.parse_reminder("zamanlayıcı kur 5 dakika makarna", NOW)
        self.assertEqual(p["text"], "makarna")
        self.assertEqual(rem.parse_reminder("yarım saat zamanlayıcı", NOW)["due"].minute, 35)
        self.assertEqual(rem.parse_reminder("1 saat sonra çamaşırı çıkar zamanlayıcı kur", NOW)["text"], "çamaşırı çıkar")

    def test_non_timer_questions_untouched(self):
        self.assertIsNone(rem.parse_reminder("zamanlayıcı nasıl çalışır", NOW))
        self.assertIsNone(rem.parse_reminder("zamanlayıcı uygulaması yaz", NOW))


if __name__ == "__main__":
    unittest.main()
