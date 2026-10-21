"""Measures the skill router on a labelled corpus; guards against hijacking ordinary chat."""
import asyncio
import unittest
from collections import Counter
from datetime import datetime, timezone

import instant_skills as s
import laptop_bridge
import missions
from skill_routing_corpus import CASES

NOW = datetime(2026, 10, 21, 14, 5, tzinfo=timezone.utc)


class AnyPool:
    """Tolerates every query the skills run; returns empty data and records nothing."""
    async def fetch(self, *a):
        return []

    async def fetchval(self, *a):
        return None

    async def fetchrow(self, sql, *a):
        return {"version": 1} if sql.lstrip().upper().startswith(("INSERT", "UPDATE")) else None

    async def execute(self, *a):
        return "OK"

    def acquire(self):
        return _Ctx(self)

    def transaction(self):
        return _Ctx(self)


class _Ctx:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *exc):
        return False


async def json_up(url, key, ttl):
    if "forecast" in url:
        return {"current": {"temperature_2m": 20, "weather_code": 0, "wind_speed_10m": 3},
                "daily": {"temperature_2m_max": [24], "temperature_2m_min": [15], "precipitation_probability_max": [0], "weather_code": [0]}}
    if "geocoding" in url:
        return {"results": [{"name": "X", "latitude": 41.0, "longitude": 29.0}]}
    if "rest.php" in url:
        return {"pages": [{"title": "Konu"}]}
    if "page/summary" in url:
        return {"type": "standard", "extract": "Özet.", "content_urls": {"desktop": {"page": "https://tr.wikipedia.org/x"}}}
    if "aladhan" in url:
        return {"data": {"timings": {k: "12:00" for k in ("Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha")}, "meta": {"timezone": "Europe/Istanbul"}}}
    if "usgs" in url:
        return {"features": []}
    if "coingecko" in url:
        return {"bitcoin": {"usd": 67000.0, "try": 2780000.0, "usd_24h_change": 1.0}, "ethereum": {"usd": 3000.0, "try": 120000.0}}
    if "daily=sunrise" in url:
        return {"daily": {"sunrise": ["2026-10-21T07:00"] * 2, "sunset": ["2026-10-21T18:00"] * 2}}
    return {"rates": {"TRY": 41.5}, "date": "2026-10-21"}


async def news_up(url, key, ttl):
    return "<rss><channel><item><title>Haber</title></item></channel></rss>"


async def ha(method, path, body=None):
    if path == "/api/states":
        return 200, [{"entity_id": "light.salon", "state": "on", "attributes": {"friendly_name": "Salon Işığı"}},
                     {"entity_id": "climate.salon", "state": "cool", "attributes": {"friendly_name": "Salon Klima"}},
                     {"entity_id": "cover.perde", "state": "closed", "attributes": {"friendly_name": "Salon Perde", "device_class": "curtain"}},
                     {"entity_id": "lock.kapi", "state": "unlocked", "attributes": {"friendly_name": "Ön Kapı Kilidi"}}]
    return 200, []


def route(text: str):
    if laptop_bridge.classify(text) is not None:
        return "laptop"
    if missions.mission_goal(text) is not None:
        return "mission"
    smart_home_cache_clear()
    out = asyncio.run(s.instant_reply(text, pool=AnyPool(), user_id="u", fetch_json=json_up, fetch_text=news_up, ha=ha, now=NOW))
    return out["skill"] if out else None


def smart_home_cache_clear():
    import smart_home
    smart_home._CACHE.clear()


class RoutingQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = [(text, expected, route(text)) for text, expected in CASES]

    def test_report_and_thresholds(self):
        wrong = [(t, e, g) for t, e, g in self.results if e != g]
        negatives = [(t, g) for t, e, g in self.results if e is None]
        hijacked = [(t, g) for t, g in negatives if g is not None]
        missed = [(t, e) for t, e, g in self.results if e is not None and g is None]
        confused = [(t, e, g) for t, e, g in self.results if e is not None and g is not None and e != g]
        total, correct = len(self.results), len(self.results) - len(wrong)
        print(f"\nrouting: {correct}/{total} correct ({100 * correct / total:.1f}%), "
              f"hijacked chat {len(hijacked)}/{len(negatives)}, missed {len(missed)}, confused {len(confused)}")
        for item in wrong:
            print("  MISROUTE", item)
        # Ordinary conversation must never be intercepted; every skill must be reachable; no skill steals another's request.
        self.assertEqual(hijacked, [], "ordinary chat was intercepted by a skill")
        self.assertEqual(confused, [], "a request went to the wrong skill")
        self.assertEqual(missed, [], "a skill request fell through to the model")

    def test_every_skill_has_positive_and_negative_coverage(self):
        labels = Counter(e for _, e in CASES if e)
        self.assertGreaterEqual(len(labels), 24)
        self.assertGreaterEqual(sum(1 for _, e in CASES if e is None), 60)


if __name__ == "__main__":
    unittest.main()
