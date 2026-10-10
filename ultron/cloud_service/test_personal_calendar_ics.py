"""No-network iCalendar compliance, privacy and timezone tests."""
import unittest
from datetime import date, datetime, time, timezone

from personal_calendar_ics import export_ics


def plan(*, title="İngilizce, B2; Ders", day=date(2026, 10, 10),
         clock=time(12, 30), done=False, note="PRIVATE_NOTE_NEVER_EXPORT"):
    return {"id": 17, "title": title, "scheduled_date": day,
            "scheduled_time": clock, "note": note, "is_done": done}


class CalendarExportTests(unittest.TestCase):
    def make(self, plans=None, zone="Europe/Istanbul", owner="test-owner"):
        return export_ics(plans if plans is not None else [plan()],
                          owner_id=owner, timezone_name=zone,
                          now=datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc))

    def test_utc_conversion_and_crlf_and_notes_exclusion(self):
        raw = self.make()
        text = raw.decode("utf-8")
        self.assertIn("BEGIN:VCALENDAR\r\n", text)
        self.assertIn("DTSTART:20261010T093000Z\r\n", text)
        self.assertIn("SUMMARY:İngilizce\\, B2\\; Ders\r\n", text)
        self.assertIn("DTSTAMP:20261010T080000Z\r\n", text)
        self.assertNotIn("PRIVATE_NOTE_NEVER_EXPORT", text)
        self.assertNotIn("VALARM", text)
        self.assertNotIn("test-owner", text)
        self.assertTrue(text.endswith("END:VCALENDAR\r\n"))
        self.assertNotIn("\n\n", text)
        self.assertTrue(all(len(line.encode("utf-8")) <= 75
                            for line in text.split("\r\n") if line))

    def test_explicit_nicosia_winter_offset_differs_from_istanbul(self):
        winter = [plan(day=date(2026, 1, 15), clock=time(12, 0))]
        self.assertIn("DTSTART:20260115T090000Z", self.make(winter, "Europe/Istanbul").decode())
        self.assertIn("DTSTART:20260115T100000Z", self.make(winter, "Asia/Nicosia").decode())

    def test_all_day_event_has_no_fake_time_or_alarm(self):
        text = self.make([plan(clock=None)]).decode("utf-8")
        self.assertIn("DTSTART;VALUE=DATE:20261010\r\n", text)
        self.assertNotIn("DTEND", text)
        self.assertNotIn("DURATION:", text)
        self.assertNotIn("VALARM", text)

    def test_completed_plans_not_included(self):
        text = self.make([plan(done=True)]).decode("utf-8")
        self.assertNotIn("BEGIN:VEVENT", text)
        self.assertIn("END:VCALENDAR", text)

    def test_repeat_export_stable_uid_and_owner_isolation(self):
        a = self.make().decode()
        b = self.make().decode()
        c = self.make(owner="different-account").decode()
        self.assertEqual(a, b)
        uid_a = next(line for line in a.splitlines() if line.startswith("UID:"))
        uid_c = next(line for line in c.splitlines() if line.startswith("UID:"))
        self.assertNotEqual(uid_a, uid_c)

    def test_ics_injection_and_multibyte_folding(self):
        dangerous = "Ö" * 100 + "\r\nBEGIN:VALARM\r\nACTION:DISPLAY"
        result = self.make([plan(title=dangerous)]).decode()
        self.assertNotIn("\r\nBEGIN:VALARM\r\n", result)
        self.assertIn("\\nBEGIN:VALARM\\n", result.replace("\r\n ", ""))
        for line in result.split("\r\n"):
            if line:
                self.assertLessEqual(len(line.encode("utf-8")), 75)

    def test_reject_invalid_zone_and_dst_boundary(self):
        with self.assertRaisesRegex(ValueError, "unsupported_timezone"):
            self.make(zone="America/Unknown")
        for day in (date(2026, 3, 29), date(2026, 10, 25)):
            with self.subTest(day=day), self.assertRaisesRegex(ValueError, "ambiguous_or_nonexistent"):
                self.make([plan(day=day, clock=time(3, 30))], "Asia/Nicosia")


if __name__ == "__main__":
    unittest.main()
