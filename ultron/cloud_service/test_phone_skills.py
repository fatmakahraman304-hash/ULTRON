"""Phone skills: news, flight links, YouTube summaries, location weather, local-model fallback."""
import asyncio
import unittest
from datetime import datetime, timezone
from unittest import mock

import instant_skills as s
import phone_skills as p

NOW = datetime(2026, 10, 21, 14, 5, tzinfo=timezone.utc)
RSS = """<rss><channel>
<item><title>İlk haber - Habertürk</title><source url="x">Habertürk</source></item>
<item><title>İkinci haber</title></item>
<item><title>Üçüncü</title><source>BBC</source></item></channel></rss>"""


def run(c):
    return asyncio.run(c)


async def fake_text(url, key, ttl):
    assert url.startswith("https://news.google.com/rss")
    return RSS


async def fake_json(url, key, ttl):
    if "forecast" in url:
        return {"current": {"temperature_2m": 9, "weather_code": 3, "wind_speed_10m": 3},
                "daily": {"temperature_2m_max": [11], "temperature_2m_min": [5], "precipitation_probability_max": [10],
                          "weather_code": [3]}}
    return {"rates": {"TRY": 41.5}, "date": "2026-10-21"}


class News(unittest.TestCase):
    def test_headlines_topics_and_sources(self):
        out = run(s.instant_reply("teknoloji haberleri", fetch_text=fake_text))
        self.assertEqual(out["skill"], "news")
        self.assertIn("Teknoloji haberleri:", out["reply"])
        self.assertIn("• İlk haber (Habertürk)", out["reply"])
        self.assertIn("• Üçüncü (BBC)", out["reply"])

    def test_not_every_message_with_haber_is_news(self):
        for text in ("haberin var mı", "bu haber doğru mu", "bu haberi yorumla", "sana bir haberim var"):
            self.assertIsNone(run(s.instant_reply(text, fetch_text=fake_text)), text)

    def test_failure_is_honest_and_xml_bombs_rejected(self):
        async def down(*a):
            raise RuntimeError("x")
        self.assertIn("ulaşamadım", run(s.instant_reply("haberler", fetch_text=down))["reply"])
        with self.assertRaises(ValueError):
            p.parse_rss('<!DOCTYPE x [<!ENTITY a "b">]><rss/>')

    def test_news_host_allowlist(self):
        with self.assertRaises(ValueError):
            run(p.fetch_news_xml("https://evil.example/rss", "k"))


class Flights(unittest.TestCase):
    def test_link_has_route_and_date_and_no_prices(self):
        out = run(s.instant_reply("İstanbul'dan Londra'ya 25 aralık uçuş bak", now=NOW))
        self.assertEqual(out["skill"], "flight")
        self.assertIn("İstanbul → Londra, 25.12.2026", out["reply"])
        self.assertIn("google.com/travel/flights", out["reply"])
        self.assertIn("2026-12-25", out["reply"])
        self.assertIn("uydurmamak", out["reply"])

    def test_tomorrow_and_no_route(self):
        self.assertIn("Ankara → İzmir, 22.10.2026", p.answer_flight("yarın Ankara'dan İzmir'e uçak bileti", NOW))
        self.assertIsNone(p.answer_flight("uçuş", NOW))
        self.assertIsNone(p.answer_flight("Londra'ya uçuş", NOW))


class YouTube(unittest.TestCase):
    def test_detects_links_with_summary_intent_only(self):
        req = p.youtube_request("bu videoyu özetle https://youtu.be/dQw4w9WgXcQ?t=5")
        self.assertEqual(req["url"], "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertIsNotNone(p.youtube_request("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=9 ne anlatıyor"))
        self.assertIsNone(p.youtube_request("https://youtu.be/dQw4w9WgXcQ"))
        self.assertIsNone(p.youtube_request("bu videoyu özetle"))
        self.assertIsNone(p.youtube_request("özetle https://evil.com/watch?v=dQw4w9WgXcQ"))

    def test_gemini_call_uses_the_video_url(self):
        import app
        seen = {}

        class Models:
            def generate_content(self, model, contents, config):
                seen["uri"] = contents.parts[0].file_data.file_uri
                return mock.Mock(text="Özet: ...")

        with mock.patch.object(app, "genai") as g, mock.patch.dict("os.environ", {"GEMINI_API_KEY": "k"}):
            g.Client.return_value.models = Models()
            self.assertEqual(app._gemini_youtube_reply("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "özetle", "sys"), "Özet: ...")
        self.assertEqual(seen["uri"], "https://www.youtube.com/watch?v=dQw4w9WgXcQ")


class Location(unittest.TestCase):
    def test_phone_location_used_when_no_city_named(self):
        out = run(s.instant_reply("hava nasıl", fetch_json=fake_json, location={"lat": 35.1, "lon": 33.4}, now=NOW))
        self.assertIn("Bulunduğun konumda şu an 9°C", out["reply"])
        self.assertNotIn("Varsayılan konum", out["reply"])
        home = run(s.instant_reply("hava nasıl", fetch_json=fake_json, now=NOW))
        self.assertIn("Varsayılan konum", home["reply"])

    def test_location_validation(self):
        import app
        self.assertEqual(app._valid_location({"lat": "35.1234", "lon": 33.4999}), {"lat": 35.12, "lon": 33.5})
        for bad in (None, {}, {"lat": 95, "lon": 0}, {"lat": "x", "lon": 1}, {"lat": float("nan"), "lon": 1}, "35,33"):
            self.assertIsNone(app._valid_location(bad), bad)


class LocalFallback(unittest.TestCase):
    def test_skill_messages_leave_the_local_model(self):
        for text in ("saat kaç", "hava nasıl", "20 dakika sonra su içmeyi hatırlat", "haberler", "durum raporu",
                     "hatırla: annemin doğum günü 3 mart", "100 dolar kaç tl", "15 x 4 + 2 kaç eder", "günaydın",
                     "istanbul'dan londra'ya uçuş", "özetle https://youtu.be/dQw4w9WgXcQ", "bugün programım ne"):
            self.assertTrue(s.wants_cloud_skill(text), text)

    def test_ordinary_chat_stays_local(self):
        for text in ("merhaba nasılsın", "bana bir şiir yaz", "python'da liste nasıl sıralanır", "haberin var mı"):
            self.assertFalse(s.wants_cloud_skill(text), text)


if __name__ == "__main__":
    unittest.main()
