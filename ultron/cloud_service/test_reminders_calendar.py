"""No-network tests: reminder parsing, iCal parsing/SSRF guard, agenda & briefing skills."""
import asyncio
import unittest
from datetime import date, datetime, time, timedelta, timezone

import calendar_feed as cal
import instant_skills as s
import reminders as rem

NOW = datetime(2026, 10, 21, 14, 5, tzinfo=timezone.utc)  # Wednesday 17:05 Istanbul


def run(coro):
    return asyncio.run(coro)


class ReminderParsing(unittest.TestCase):
    def parse(self, text):
        return rem.parse_reminder(text, NOW)

    def test_relative_and_absolute_times(self):
        p = self.parse("20 dakika sonra bana su içmeyi hatırlat")
        self.assertEqual((p["due"].hour, p["due"].minute, p["text"]), (17, 25, "su içmeyi"))
        p = self.parse("yarın 09:00'da toplantıyı hatırlat")
        self.assertEqual((p["due"].day, p["due"].hour, p["text"]), (22, 9, "toplantıyı"))
        p = self.parse("hatırlat: yarım saat sonra çamaşırı çıkar")
        self.assertEqual((p["due"].hour, p["due"].minute, p["text"]), (17, 35, "çamaşırı çıkar"))
        p = self.parse("cuma akşam 7'de maça gitmeyi hatırlat")
        self.assertEqual((p["due"].day, p["due"].hour), (23, 19))

    def test_bare_clock_in_the_past_means_tomorrow(self):
        p = self.parse("saat 15'te ilaç içmemi hatırlat")
        self.assertEqual((p["due"].day, p["due"].hour), (22, 15))

    def test_errors_instead_of_guessing(self):
        self.assertEqual(self.parse("bana bir şey hatırlat"), {"error": "no_time"})
        self.assertEqual(self.parse("dün 10'da hatırlat"), {"error": "past"})
        self.assertIsNone(self.parse("hatırlatıcılarım neler"))
        self.assertIsNone(self.parse("merhaba nasılsın"))

    def test_text_keeps_turkish_characters(self):
        self.assertEqual(self.parse("1 saat sonra ekmek almayı hatırlat")["text"], "ekmek almayı")


ICS = """BEGIN:VCALENDAR
BEGIN:VEVENT
SUMMARY:Toplantı\\, Ekip
DTSTART:20261021T150000Z
DTEND:20261021T160000Z
LOCATION:Ofis
END:VEVENT
BEGIN:VEVENT
SUMMARY:Haftalık spor
DTSTART;TZID=Europe/Istanbul:20261012T190000
RRULE:FREQ=WEEKLY;BYDAY=MO,WE
EXDATE;TZID=Europe/Istanbul:20261026T190000
END:VEVENT
BEGIN:VEVENT
SUMMARY:Doğum günü
DTSTART;VALUE=DATE:20261022
DTEND;VALUE=DATE:20261023
RRULE:FREQ=YEARLY
END:VEVENT
BEGIN:VEVENT
SUMMARY:İptal
STATUS:CANCELLED
DTSTART:20261021T100000Z
END:VEVENT
END:VCALENDAR"""


class CalendarFeed(unittest.TestCase):
    def test_parse_timezones_recurrence_exdate_allday_cancelled(self):
        events = cal.parse_ics(ICS, date(2026, 10, 21), date(2026, 10, 28))
        titles = [(e["title"], e["start"][:16]) for e in events]
        self.assertIn(("Toplantı, Ekip", "2026-10-21T18:00"), titles)  # 15:00Z → 18:00 Istanbul
        self.assertEqual(sum(1 for t, _ in titles if t == "Haftalık spor"), 2)  # Wed 21 + Wed 28, Mon 26 excluded
        self.assertTrue(any(e["all_day"] and e["title"] == "Doğum günü" for e in events))
        self.assertFalse(any(e["title"] == "İptal" for e in events))

    def test_feed_url_allowlist_blocks_ssrf(self):
        self.assertTrue(cal.validate_feed_url("webcal://p01-caldav.icloud.com/x/y").startswith("https://"))
        self.assertTrue(cal.validate_feed_url("https://calendar.google.com/calendar/ical/a/private-b/basic.ics"))
        for bad in ("http://calendar.google.com/x", "https://127.0.0.1/x", "https://evil.com/calendar.google.com",
                    "https://calendar.google.com.evil.com/x", "https://u:p@calendar.google.com/x",
                    "https://calendar.google.com:8443/x", "file:///etc/passwd", "", None):
            with self.assertRaises(cal.FeedError, msg=str(bad)):
                cal.validate_feed_url(bad)


class FakePool:
    """Minimal asyncpg stand-in keyed on SQL fragments."""
    def __init__(self, feed_url=None):
        self.feed_url, self.inserted, self.pending = feed_url, [], []

    async def fetchval(self, sql, *a):
        if "FROM owner_calendar_feeds" in sql:
            return self.feed_url
        if "INSERT INTO owner_reminders" in sql:
            self.inserted.append(a)
            return len(self.inserted)
        if "COUNT(*) FROM owner_reminders" in sql:
            return len(self.pending)
        if "device_presence" in sql:
            return True
        return 0

    async def fetch(self, sql, *a):
        if "FROM owner_plans" in sql:
            return [{"title": "İngilizce çalış", "scheduled_date": date(2026, 10, 21), "scheduled_time": time(20, 0)}]
        if "FROM owner_reminders" in sql:
            return [{"id": 1, "text": "su içmeyi", "due_at": datetime(2026, 10, 21, 14, 25, tzinfo=timezone.utc)}]
        return []

    async def fetchrow(self, *a):
        return None


async def fake_fetch(url, key, ttl):
    if "forecast" in url:
        return {"current": {"temperature_2m": 21, "weather_code": 0, "wind_speed_10m": 5},
                "daily": {"temperature_2m_max": [24], "temperature_2m_min": [15], "precipitation_probability_max": [0],
                          "weather_code": [0]}}
    return {"date": "2026-10-21", "rates": {"TRY": 41.5}}


class Skills(unittest.TestCase):
    def test_reminder_is_stored_and_reply_is_honest_about_delivery(self):
        pool = FakePool()
        out = run(s.instant_reply("20 dakika sonra bana su içmeyi hatırlat", pool=pool, user_id="u", now=NOW))
        self.assertEqual(out["skill"], "reminder")
        self.assertEqual(len(pool.inserted), 1)
        self.assertEqual(pool.inserted[0][1], "su içmeyi")
        self.assertIn("açıkken", out["reply"])
        self.assertIn("kilitliyken", out["reply"])

    def test_no_reminder_stored_without_time(self):
        pool = FakePool()
        out = run(s.instant_reply("bana bir şey hatırlat", pool=pool, user_id="u", now=NOW))
        self.assertEqual(pool.inserted, [])
        self.assertIn("Ne zaman", out["reply"])

    def test_agenda_merges_plans_reminders_and_notes_missing_calendar(self):
        out = run(s.instant_reply("bugün programım ne", pool=FakePool(), user_id="u", now=NOW))
        self.assertEqual(out["skill"], "agenda")
        self.assertIn("20:00 — İngilizce çalış (plan)", out["reply"])
        self.assertIn("⏰ su içmeyi", out["reply"])
        self.assertIn("Takvim bağlı değil", out["reply"])

    def test_briefing(self):
        out = run(s.instant_reply("günaydın", pool=FakePool(), user_id="u", fetch_json=fake_fetch, now=NOW))
        self.assertEqual(out["skill"], "briefing")
        for needle in ("21 Ekim 2026 Çarşamba", "🌤", "📅 Bugün", "💻 Bilgisayar: çevrimiçi", "💱"):
            self.assertIn(needle, out["reply"])
        self.assertIsNone(run(s.instant_reply("günaydın dostum bugün çok yorgunum uzun uzun anlatayım",
                                               pool=FakePool(), user_id="u", now=NOW)))

    def test_without_pool_conversation_still_reaches_model(self):
        self.assertIsNone(run(s.instant_reply("20 dakika sonra bana su içmeyi hatırlat", now=NOW)))


if __name__ == "__main__":
    unittest.main()


class MemorySkills(unittest.TestCase):
    def setUp(self):
        import memory_skills
        self.m = memory_skills

    def test_original_characters_are_preserved_in_value(self):
        class Pool:
            rows = []

            def acquire(self):
                raise AssertionError("unexpected")

        saved = {}

        async def fake_upsert(pool, user, device, category, key, value):
            saved.update(category=category, key=key, value=value, device=device)
            return {"version": 1}
        self.m.upsert_owner_memory = fake_upsert
        reply = run(self.m.handle("Hatırla: Annemin doğum günü 3 Mart, hediye olarak çiçek seviyor", object(), "u"))
        self.assertIn("Hafızaya kaydettim", reply)
        self.assertEqual(saved["value"], "Annemin doğum günü 3 Mart, hediye olarak çiçek seviyor")
        self.assertEqual(saved["category"], "NOTE")
        self.assertTrue(saved["key"].startswith("not: Annemin doğum günü 3 Mart"))

    def test_secret_is_refused_and_plain_chat_ignored(self):
        async def reject(*a):
            raise ValueError("sensitive_memory_rejected")
        self.m.upsert_owner_memory = reject
        self.assertIn("kaydetmiyorum", run(self.m.handle("hatırla: wifi şifrem sk-abcdefghijklmnop1234", object(), "u")))
        for text in ("bunu hatırlıyor musun", "hatırlatıcılarım neler", "merhaba", "not alıyorum bence"):
            self.assertIsNone(run(self.m.handle(text, object(), "u")), text)

    def test_forget_deletes_only_a_single_unambiguous_match(self):
        deleted = []

        async def fake_delete(pool, user, key):
            deleted.append(key)
            return True
        self.m.delete_owner_memory = fake_delete

        class Pool:
            def __init__(self, rows):
                self.rows = rows

            async def fetch(self, *a):
                return self.rows
        one = Pool([{"key": "not: a #1", "value": "Annemin doğum günü 3 Mart"}, {"key": "k2", "value": "Kahve sever"}])
        self.assertIn("Unuttum", run(self.m.handle("unut: doğum günü", one, "u")))
        self.assertEqual(deleted, ["not: a #1"])
        many = Pool([{"key": "a", "value": "Kahve sever"}, {"key": "b", "value": "Kahve içmez"}])
        self.assertIn("2 kayıt", run(self.m.handle("unut: kahve", many, "u")))
        self.assertEqual(deleted, ["not: a #1"])  # nothing more deleted
        self.assertIn("bulamadım", run(self.m.handle("unut: zebra", one, "u")))

    def test_list_memories(self):
        class Pool:
            async def fetch(self, *a):
                return [{"category": "NOTE", "key": "not: x #1", "value": "Annemin doğum günü 3 Mart"},
                        {"category": "FACT", "key": "şehir", "value": "Lefkoşa"}]
        reply = run(self.m.handle("neler hatırlıyorsun", Pool(), "u"))
        self.assertIn("• Annemin doğum günü 3 Mart", reply)
        self.assertIn("• şehir: Lefkoşa", reply)
