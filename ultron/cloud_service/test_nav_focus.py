"""Navigation links and pomodoro."""
import asyncio
import unittest
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import focus_skills as fs
import instant_skills as s
import nav_skills as nav

NOW = datetime(2026, 10, 21, 14, 5, tzinfo=timezone.utc)   # 17:05 Istanbul


def run(c):
    return asyncio.run(c)


def links(reply):
    return [l.split(": ", 1)[-1] for l in reply.splitlines() if "http" in l]


class Navigation(unittest.TestCase):
    def test_directions_with_origin_destination_and_mode(self):
        reply = nav.answer("Ankara'dan İstanbul'a yürüyerek yol tarifi")
        apple, google = links(reply)
        q = parse_qs(urlsplit(google).query)
        self.assertEqual((q["origin"], q["destination"], q["travelmode"]), (["Ankara"], ["İstanbul"], ["walking"]))
        self.assertEqual(parse_qs(urlsplit(apple).query)["dirflg"], ["w"])
        self.assertIn("tahmin yürütmüyorum", reply)

    def test_destination_only_uses_phone_location_when_sent(self):
        reply = nav.answer("İzmir'e nasıl giderim", {"lat": 35.12, "lon": 33.43})
        google = links(reply)[1]
        self.assertEqual(parse_qs(urlsplit(google).query)["origin"], ["35.12,33.43"])
        self.assertIn("bulunduğun konum → İzmir", reply)
        self.assertNotIn("origin", links(nav.answer("İzmir'e nasıl giderim"))[1])

    def test_nearby_and_traffic(self):
        reply = nav.answer("yakınımda eczane", {"lat": 35.1, "lon": 33.4})
        apple = links(reply)[0]
        self.assertEqual(parse_qs(urlsplit(apple).query)["sll"], ["35.1,33.4"])
        self.assertEqual(parse_qs(urlsplit(links(reply)[1]).query)["query"], ["eczane"])
        self.assertIn("layer=traffic", nav.answer("trafik durumu", {"lat": 41.0, "lon": 29.0}))

    def test_chat_is_not_navigation(self):
        for text in ("yol tarifi nasıl alınır", "yakın arkadaşım geldi", "yakınımda biri var mı", "en yakın zamanda görüşelim",
                     "rota planlama uygulaması yaz", "trafik cezası nasıl ödenir", "trafikte sıkıştım çok sinirliyim"):
            self.assertFalse(nav.wants_navigation(text), text)

    def test_special_characters_are_url_encoded(self):
        google = links(nav.answer("Şanlıurfa'dan Çanakkale'ye yol tarifi"))[1]
        self.assertNotIn("Ş", google)
        self.assertEqual(parse_qs(urlsplit(google).query)["destination"], ["Çanakkale"])


class Pool:
    def __init__(self, running=0):
        self.inserted, self.running = [], running

    async def fetchval(self, sql, *a):
        return self.running

    async def execute(self, sql, *a):
        self.inserted.append(a)


def say(pool, text):
    out = run(s.instant_reply(text, pool=pool, user_id="u", now=NOW))
    return out["reply"] if out else None


class Focus(unittest.TestCase):
    def test_default_and_custom_sessions(self):
        pool = Pool()
        reply = say(pool, "pomodoro başlat")
        self.assertIn("25 dk çalış, sonra 5 dk mola", reply)
        (_, t1, d1), (_, t2, d2) = pool.inserted
        self.assertEqual((d1.strftime("%H:%M"), d2.strftime("%H:%M")), ("17:30", "17:35"))
        self.assertTrue(t1.startswith("🍅 Mola") and t2.startswith("🍅 Mola bitti"))
        pool = Pool()
        self.assertIn("50 dk çalış, sonra 10 dk mola", say(pool, "50 dakika odaklan"))
        pool = Pool()
        self.assertIn("40 dk çalış, sonra 8 dk mola", say(pool, "pomodoro 40 8"))

    def test_guards(self):
        self.assertIn("Zaten çalışan", say(Pool(running=1), "pomodoro başlat"))
        self.assertIn("5–180", say(Pool(), "pomodoro 500 5"))
        self.assertIn("iptal ettim", say(Pool(running=1), "pomodoro durdur"))
        for text in ("odaklanamıyorum", "pomodoro tekniği nedir", "odaklanmak için ne yapmalıyım"):
            self.assertFalse(fs.wants_focus(text), text)


if __name__ == "__main__":
    unittest.main()
