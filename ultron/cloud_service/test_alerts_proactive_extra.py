"""Price alerts, urgent quake notices, evening preview."""
import asyncio
import json
import unittest
from datetime import date, datetime, time, timezone

import alert_skills as al
import instant_skills as s
import proactive as pro

NOW = datetime(2026, 10, 21, 14, 5, tzinfo=timezone.utc)  # 17:05 Istanbul
UTC = timezone.utc


def run(c):
    return asyncio.run(c)


async def prices(url, key, ttl):
    if "coingecko" in url:
        return {"bitcoin": {"usd": 67000.0, "try": 2780000.0}, "ethereum": {"usd": 3200.0}}
    return {"rates": {"TRY": 41.5}}


class AlertPool:
    def __init__(self, rows=()):
        self.rows, self.inserted, self.deactivated = list(rows), [], []

    async def fetchval(self, sql, *a):
        if "COUNT(*) FROM owner_alerts" in sql:
            return len(self.rows)
        if "UPDATE owner_alerts SET active=FALSE,fired_at" in sql:
            self.deactivated.append(a[0])
            return a[0]
        if "WITH c AS (UPDATE owner_alerts" in sql:
            n, self.rows = len(self.rows), []
            return n
        return None

    async def fetch(self, sql, *a):
        return self.rows

    async def execute(self, sql, *a):
        self.inserted.append(a)


class Parse(unittest.TestCase):
    def test_amounts_directions_and_units(self):
        p = al.parse_alert("bitcoin 70 bin dolara çıkarsa haber ver")
        self.assertEqual((p["asset"], p["vs"], p["direction"], p["threshold"]), ("bitcoin", "usd", "above", 70000.0))
        self.assertEqual(al.parse_alert("bitcoin 60000 doların altına düşerse haber ver")["direction"], "below")
        self.assertEqual(al.parse_alert("bitcoin 1,5 milyon liraya çıkarsa haber ver")["vs"], "try")
        fx = al.parse_alert("euro 50,5 tl'yi geçerse uyar")
        self.assertEqual((fx["asset"], fx["kind"], fx["threshold"]), ("EUR", "fx", 50.5))
        for text in ("bitcoin nedir", "yarın hava ne olursa haber ver", "alarmlarım", "dolar kaç tl"):
            self.assertIsNone(al.parse_alert(text), text)


class Create(unittest.TestCase):
    def test_creates_with_direction_inferred_from_current_price(self):
        pool = AlertPool()
        out = run(s.instant_reply("dolar 45 TL olunca haber ver", pool=pool, user_id="u", fetch_json=prices, now=NOW))
        self.assertEqual(out["skill"], "alerts")
        self.assertEqual(pool.inserted[0][4], "above")      # 45 > 41.5
        self.assertIn("şu an 41,5 ₺", out["reply"])

    def test_already_crossed_target_is_not_stored(self):
        pool = AlertPool()
        out = run(s.instant_reply("bitcoin 60 bin dolara çıkarsa haber ver", pool=pool, user_id="u", fetch_json=prices, now=NOW))
        self.assertEqual(pool.inserted, [])
        self.assertIn("aşılmış", out["reply"])

    def test_price_source_down_does_not_create_blind_alert(self):
        async def down(*a):
            raise RuntimeError()
        pool = AlertPool()
        out = run(s.instant_reply("bitcoin 70 bin dolara çıkarsa haber ver", pool=pool, user_id="u", fetch_json=down, now=NOW))
        self.assertEqual(pool.inserted, [])
        self.assertIn("kurmadım", out["reply"])

    def test_list_and_cancel(self):
        rows = [{"asset": "bitcoin", "vs": "usd", "direction": "above", "threshold": 70000.0}]
        self.assertIn("bitcoin ≥ 70.000 $", run(s.instant_reply("alarmlarım", pool=AlertPool(rows), user_id="u", now=NOW))["reply"])
        self.assertIn("1 fiyat alarmını iptal", run(s.instant_reply("fiyat alarmlarımı iptal et", pool=AlertPool(rows), user_id="u", now=NOW))["reply"])

    def test_limit(self):
        pool = AlertPool([{}] * al.MAX_ACTIVE)
        out = run(s.instant_reply("bitcoin 70 bin dolara çıkarsa haber ver", pool=pool, user_id="u", fetch_json=prices, now=NOW))
        self.assertIn("En fazla", out["reply"])


class Check(unittest.TestCase):
    def test_fires_once_and_only_when_crossed(self):
        rows = [{"id": 1, "user_id": "u", "asset": "bitcoin", "kind": "coin", "vs": "usd", "direction": "above", "threshold": 65000.0},
                {"id": 2, "user_id": "u", "asset": "bitcoin", "kind": "coin", "vs": "usd", "direction": "above", "threshold": 90000.0},
                {"id": 3, "user_id": "u", "asset": "ethereum", "kind": "coin", "vs": "usd", "direction": "below", "threshold": 3300.0}]
        pool = AlertPool(rows)
        fired = run(al.check_all(pool, prices))
        self.assertEqual([n["key"] for _, n in fired], ["alert:1", "alert:3"])
        self.assertEqual(pool.deactivated, [1, 3])
        self.assertIn("67.000", fired[0][1]["body"])


class Plans:
    def __init__(self, tomorrow_rows=()):
        self.rows = list(tomorrow_rows)

    async def fetch(self, sql, *a):
        return self.rows if "FROM owner_plans" in sql else []

    async def fetchval(self, sql, *a):
        return json.dumps({"evening_preview": True}) if "FROM owner_prefs" in sql else None


async def quake_feed(url, key, ttl):
    return {"features": [{"id": "us1", "properties": {"mag": 5.8, "place": "10 km E of Malatya, Turkey", "time": int(NOW.timestamp() * 1000) - 600_000}},
                         {"id": "us0", "properties": {"mag": 5.2, "place": "old one", "time": int(NOW.timestamp() * 1000) - 7_200_000}}]}


class Urgent(unittest.TestCase):
    def test_big_quake_ignores_quiet_hours_other_rules_do_not(self):
        night = datetime(2026, 10, 21, 22, 0, tzinfo=UTC)  # 01:00 Istanbul
        async def feed(url, key, ttl):
            f = await quake_feed(url, key, ttl)
            for ft in f["features"]:
                ft["properties"]["time"] = int(night.timestamp() * 1000) - (600_000 if ft["id"] == "us1" else 7_200_000)
            return f
        items = run(pro.evaluate(Plans(), "u", night, feed))
        self.assertEqual([i["key"] for i in items], ["quake:us1"])
        self.assertIn("M5.8", items[0]["title"])

    def test_evening_preview_opt_in(self):
        evening = datetime(2026, 10, 21, 18, 30, tzinfo=UTC)  # 21:30 Istanbul
        rows = [{"id": 1, "title": "Toplantı", "scheduled_date": date(2026, 10, 22), "scheduled_time": time(10, 0)}]
        async def none(url, key, ttl):
            raise RuntimeError()
        items = run(pro.evaluate(Plans(rows), "u", evening, none))
        self.assertEqual([i["key"] for i in items], ["evening:2026-10-22"])
        self.assertIn("Yarın 1 kayıt", items[0]["body"])


if __name__ == "__main__":
    unittest.main()
