"""Context-aware short follow-ups after skill answers."""
import asyncio
import unittest
from datetime import datetime, timezone

import followups as fu
import instant_skills as s

NOW = datetime(2026, 10, 21, 14, 5, tzinfo=timezone.utc)
W, C, N = "golge-skill:weather", "golge-skill:currency", "golge-skill:news"


class Resolve(unittest.TestCase):
    def test_weather_followups(self):
        self.assertEqual(fu.resolve("peki yarın?", W), "yarın hava nasıl")
        self.assertEqual(fu.resolve("yarın?", W), "yarın hava nasıl")
        self.assertEqual(fu.resolve("ya Londra?", W), "Londra'da hava nasıl")
        self.assertEqual(fu.resolve("ya Londra'da?", W), "Londra'da hava nasıl")

    def test_other_skills(self):
        self.assertEqual(fu.resolve("ya euro?", C), "euro kaç tl")
        self.assertEqual(fu.resolve("ya ethereum?", "golge-skill:crypto"), "ethereum fiyatı")
        self.assertEqual(fu.resolve("peki spor?", N), "spor haberleri")
        self.assertEqual(fu.resolve("ya Tokyo?", "golge-skill:clock"), "Tokyo'da saat kaç")
        self.assertEqual(fu.resolve("peki yarın?", "golge-skill:sun_moon"), "yarın gün doğumu kaçta")

    def test_needs_a_skill_reply_and_a_marker(self):
        for prev in (None, "", "cloud-gemini", "laptop-agent", "golge-mission"):
            self.assertIsNone(fu.resolve("peki yarın?", prev), prev)
        for text in ("Londra", "teşekkürler", "tamam", "nasılsın?", "ya sen?", "peki neden böyle oldu?", "evet", "ciddi misin?",
                     "bunu hiç beklemiyordum açıkçası şaşırdım"):
            self.assertIsNone(fu.resolve(text, W), text)

    def test_end_to_end_through_the_router(self):
        async def up(url, key, ttl):
            return {"current": {"temperature_2m": 9, "weather_code": 3, "wind_speed_10m": 3},
                    "daily": {"temperature_2m_max": [11, 12], "temperature_2m_min": [5, 6], "precipitation_probability_max": [10, 20], "weather_code": [3, 3]},
                    "results": [{"name": "Londra", "latitude": 51.5, "longitude": -0.1}]}
        explicit = fu.resolve("ya Londra?", W)
        out = asyncio.run(s.instant_reply(explicit, fetch_json=up, now=NOW))
        self.assertEqual(out["skill"], "weather")
        self.assertIn("Londra'da şu an 9°C", out["reply"])
        tomorrow = asyncio.run(s.instant_reply(fu.resolve("peki yarın?", W), fetch_json=up, now=NOW))
        self.assertIn("yarın", tomorrow["reply"])


if __name__ == "__main__":
    unittest.main()
