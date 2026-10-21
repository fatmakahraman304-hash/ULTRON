"""Free-time finder, clash warnings and severe-weather alerts."""
import asyncio
import unittest
from datetime import date, datetime, time, timedelta, timezone

import instant_skills as s
import plan_skills as ps
import proactive as pro

NOW = datetime(2026, 10, 21, 14, 5, tzinfo=timezone.utc)   # Wed 21 Oct 2026, 17:05 Istanbul


def run(c):
    return asyncio.run(c)


class Pool:
    def __init__(self, plans=()):
        self.plans, self.added = list(plans), []

    async def fetch(self, sql, *a):
        if "FROM owner_plans" in sql and "scheduled_date=$2" in sql:
            return [p for p in self.plans if p["scheduled_date"] == a[1]]
        return []

    async def fetchval(self, sql, *a):
        if "INSERT INTO owner_plans" in sql:
            self.added.append(a)
            return len(self.added)
        return None

    async def execute(self, *a):
        pass


def plan(title, day, hh, mm=0):
    return {"title": title, "scheduled_date": day, "scheduled_time": time(hh, mm)}


def say(pool, text):
    out = run(s.instant_reply(text, pool=pool, user_id="u", now=NOW))
    return out["reply"] if out else None


class FreeSlots(unittest.TestCase):
    def test_math(self):
        self.assertEqual(ps.free_slots([]), [(540, 1080)])
        self.assertEqual(ps.free_slots([(600, 660), (840, 900)]), [(540, 600), (660, 840), (900, 1080)])
        self.assertEqual(ps.free_slots([(540, 1080)]), [])
        self.assertEqual(ps.free_slots([(540, 570), (570, 620)], minimum=30), [(620, 1080)])           # touching intervals
        self.assertEqual(ps.free_slots([(500, 560), (550, 700)]), [(700, 1080)])                       # overlap and early start
        self.assertEqual(ps.free_slots([(560, 580)]), [(580, 1080)])                                   # 20 min gap is too short

    def test_chat(self):
        tomorrow = date(2026, 10, 22)
        pool = Pool([plan("Toplantı", tomorrow, 10), plan("Diş", tomorrow, 14, 30)])
        reply = say(pool, "yarın ne zaman boşum")
        self.assertIn("Yarın (22.10.2026 Perşembe)", reply)
        for line in ("• 09:00–10:00 (1 sa 0 dk)", "• 11:00–14:30 (3 sa 30 dk)", "• 15:30–18:00 (2 sa 30 dk)"):
            self.assertIn(line, reply)
        self.assertIn("1 saat sürer", reply)
        self.assertIn("bütün gün müsaitsin", say(Pool(), "cuma müsait saatlerim"))
        self.assertIsNone(say(Pool(), "boş zamanlarımda ne yapabilirim"))
        self.assertIsNone(say(Pool(), "yarın boş vaktim olursa sinemaya gidelim"))


class Conflicts(unittest.TestCase):
    def test_warns_about_a_nearby_plan_but_still_adds(self):
        pool = Pool([plan("Toplantı", date(2026, 10, 22), 15, 30)])
        reply = say(pool, "yarın 15:00 diş randevusu planıma ekle")
        self.assertIn("Planına ekledim", reply)
        self.assertIn("⚠ Dikkat, bu saate yakın başka kayıt var: 15:30 — Toplantı", reply)
        self.assertEqual(len(pool.added), 1)

    def test_no_warning_when_far_apart(self):
        pool = Pool([plan("Toplantı", date(2026, 10, 22), 10)])
        self.assertNotIn("⚠", say(pool, "yarın 15:00 diş randevusu planıma ekle"))


def hourly(day, **series):
    hours = [f"{day}T{h:02d}:00" for h in range(24)]
    return {"hourly": {"time": hours, **{k: v for k, v in series.items()}}}


class Weather(unittest.TestCase):
    def alerts(self, **series):
        async def fake(url, key, ttl):
            return hourly("2026-10-21", **series)
        local = datetime(2026, 10, 21, 15, 0, tzinfo=pro.HOME_TZ)
        return {a["key"].split(":")[0]: a for a in run(pro.weather_alerts(fake, local))}

    def test_each_hazard_once_per_kind(self):
        calm = [0] * 24
        got = self.alerts(precipitation_probability=[80] * 24, temperature_2m=[38] * 24, weather_code=[95] * 24, wind_gusts_10m=[75] * 24)
        self.assertEqual(sorted(got), ["heat", "rain", "storm", "wind"])
        self.assertIn("%80", got["rain"]["body"])
        self.assertIn("75 km/sa", got["wind"]["body"])
        self.assertEqual(self.alerts(precipitation_probability=calm, temperature_2m=[20] * 24, weather_code=calm, wind_gusts_10m=[20] * 24), {})
        self.assertEqual(sorted(self.alerts(temperature_2m=[-5] * 24)), ["cold"])

    def test_missing_fields_do_not_break_rain(self):
        got = self.alerts(precipitation_probability=[90] * 24)       # older response shape
        self.assertEqual(sorted(got), ["rain"])

    def test_only_the_next_three_hours_count(self):
        far = [0] * 24
        far[22] = 100          # 22:00 is outside 15:00 + 3 h
        self.assertEqual(self.alerts(precipitation_probability=far), {})


if __name__ == "__main__":
    unittest.main()
