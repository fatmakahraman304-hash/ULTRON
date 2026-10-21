"""Wikipedia, prayer times, earthquakes, sun/moon, crypto — with fake upstreams."""
import asyncio
import unittest
from datetime import datetime, timezone

import instant_skills as s
import knowledge_skills as k

NOW = datetime(2026, 10, 21, 14, 5, tzinfo=timezone.utc)  # 17:05 Istanbul


def run(c):
    return asyncio.run(c)


async def upstream(url, key, ttl):
    if "rest.php/v1/search/title" in url:
        return {"pages": [{"title": "Mustafa Kemal Atatürk"}]} if "Atat" in url else {"pages": []}
    if "page/summary" in url:
        if "Disamb" in url:
            return {"type": "disambiguation", "extract": "x"}
        return {"type": "standard", "extract": "Mustafa Kemal Atatürk, Türk asker ve devlet adamı. Türkiye Cumhuriyeti'nin kurucusudur. " + "Uzun cümle. " * 80,
                "content_urls": {"desktop": {"page": "https://tr.wikipedia.org/wiki/Mustafa_Kemal_Atat%C3%BCrk"}}}
    if "aladhan" in url:
        return {"data": {"timings": {"Fajr": "05:10", "Sunrise": "06:35", "Dhuhr": "12:20", "Asr": "15:25", "Maghrib": "17:55", "Isha": "19:15"},
                         "meta": {"timezone": "Europe/Istanbul"}}}
    if "earthquake.usgs.gov" in url:
        return {"features": [{"properties": {"mag": 4.6, "place": "5 km S of Malatya, Turkey", "time": 1792580000000}}]}
    if "geocoding" in url:
        return {"results": [{"name": "Ankara", "latitude": 39.9, "longitude": 32.8}]}
    if "daily=sunrise" in url:
        return {"daily": {"sunrise": ["2026-10-21T07:12", "2026-10-22T07:13"], "sunset": ["2026-10-21T18:05", "2026-10-22T18:04"]}}
    if "coingecko" in url:
        return {"bitcoin": {"usd": 67000.5, "try": 2780000.0, "usd_24h_change": -1.234}}
    raise AssertionError(url)


def ask(text, fetch=upstream, location=None):
    return run(s.instant_reply(text, fetch_json=fetch, now=NOW, location=location))


class Wiki(unittest.TestCase):
    def test_summary_is_short_sourced_and_linked(self):
        out = ask("Atatürk kimdir")
        self.assertEqual(out["skill"], "wiki")
        self.assertIn("Mustafa Kemal Atatürk: Mustafa Kemal Atatürk, Türk asker", out["reply"])
        self.assertIn("Kaynak: Vikipedi https://tr.wikipedia.org/wiki/", out["reply"])
        self.assertLess(len(out["reply"]), 700)

    def test_not_found_and_ordinary_questions(self):
        self.assertIn("bulamadım", ask("vikipedi Zzzzqx")["reply"])
        for text in ("python nedir", "Ben kimdir", "bugün ne yapsam"):
            self.assertIsNone(ask(text), text)

    def test_failure_is_honest(self):
        async def down(*a):
            raise RuntimeError()
        self.assertIn("ulaşamadım", ask("Atatürk kimdir", down)["reply"])


class Prayer(unittest.TestCase):
    def test_times_next_prayer_and_specific_questions(self):
        out = ask("namaz vakitleri")
        self.assertEqual(out["skill"], "prayer")
        self.assertIn("• Akşam: 17:55", out["reply"])
        self.assertIn("Sıradaki: Akşam — 50 dk sonra", out["reply"])
        self.assertIn("İftar 17:55", ask("iftar saat kaçta")["reply"])
        self.assertIn("Ankara namaz vakitleri", ask("Ankara'da namaz vakitleri")["reply"])


class Quake(unittest.TestCase):
    def test_recent_quakes_and_knowledge_questions_ignored(self):
        out = ask("son depremler")
        self.assertIn("M4.6 — 5 km S of Malatya, Turkey", out["reply"])
        self.assertIn("USGS", out["reply"])
        self.assertIsNone(ask("deprem çantasında neler olmalı"))


class SunMoon(unittest.TestCase):
    def test_sun_times(self):
        self.assertIn("gün doğumu 07:12, gün batımı 18:05 (gün uzunluğu 10 sa 53 dk)", ask("gün batımı saat kaçta")["reply"])
        self.assertIn("07:13", ask("yarın gün doğumu kaçta")["reply"])

    def test_moon_phase_math(self):
        full = datetime(2026, 10, 26, 4, 12, tzinfo=timezone.utc)  # real full moon
        m = k.moon_phase(full)
        self.assertEqual(m["name"], "Dolunay")
        self.assertGreaterEqual(m["illumination"], 97)
        new = k.moon_phase(datetime(2026, 11, 9, 21, 2, tzinfo=timezone.utc))
        self.assertEqual(new["name"], "Yeni ay")
        self.assertIn("Sonraki dolunay", ask("ay evresi nedir")["reply"])


class Crypto(unittest.TestCase):
    def test_price_and_ignored_opinions(self):
        out = ask("bitcoin kaç dolar")
        self.assertIn("67.000,5 $", out["reply"])
        self.assertIn("-1,2%", out["reply"])
        self.assertIn("yatırım tavsiyesi değildir", out["reply"])
        for text in ("bitcoin neden düştü", "bitcoin alayım mı", "bitcoin nedir"):
            self.assertIsNone(ask(text), text)


class Fallback(unittest.TestCase):
    def test_routes_leave_local_model(self):
        for text in ("Atatürk kimdir", "namaz vakitleri", "son depremler", "ay evresi", "bitcoin fiyatı"):
            self.assertTrue(s.wants_cloud_skill(text), text)


if __name__ == "__main__":
    unittest.main()
