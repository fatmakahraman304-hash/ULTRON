"""No-network tests for GÖLGE instant skills."""
import asyncio
import unittest
from datetime import datetime, timezone

import instant_skills as s

NOW = datetime(2026, 10, 21, 14, 5, tzinfo=timezone.utc)  # 17:05 Istanbul, Wednesday


def run(coro):
    return asyncio.run(coro)


async def fake_fetch(url, key, ttl):
    if "geocoding" in url:
        if "Nowhereville" in url:
            return {}
        return {"results": [{"name": "Londra", "country": "UK", "latitude": 51.5, "longitude": -0.12}]}
    if "forecast" in url:
        return {"current": {"temperature_2m": 14.2, "apparent_temperature": 12.0, "weather_code": 61,
                            "wind_speed_10m": 18},
                "daily": {"temperature_2m_max": [16, 15], "temperature_2m_min": [9, 8],
                          "precipitation_probability_max": [70, 20], "weather_code": [61, 3]}}
    return {"date": "2026-10-21", "rates": {"TRY": 41.5, "USD": 1.16}}


async def failing_fetch(url, key, ttl):
    raise RuntimeError("down")


def ask(text, fetch=fake_fetch):
    return run(s.instant_reply(text, fetch_json=fetch, now=NOW))


class InstantSkills(unittest.TestCase):
    def test_clock_uses_istanbul_and_world_cities(self):
        self.assertIn("17:05", ask("saat kaç")["reply"])
        tokyo = ask("Tokyo'da saat kaç")["reply"]
        self.assertIn("23:05", tokyo)
        self.assertIn("6 saat ileri", tokyo)
        self.assertIn("21 Ekim 2026 Çarşamba", ask("bugün günlerden ne")["reply"])

    def test_countdown(self):
        self.assertIn("72 gün", ask("yılbaşına kaç gün var")["reply"])
        self.assertIn("216 gün", ask("25 mayıs 2027'ye kaç gün var")["reply"])
        self.assertIn("bugün", ask("21.10.2026 kaç gün var")["reply"])

    def test_math(self):
        self.assertEqual(ask("15 x 4 + 2 kaç eder")["reply"], "15 × 4 + 2 = 62")
        self.assertIn("1.254", ask("1.250,5 + 3,5 hesapla")["reply"])
        self.assertIn("= 12", ask("karekök 144")["reply"])
        self.assertIn("= 30", ask("200'ün %15'i kaç")["reply"])
        self.assertIn("Sıfıra bölme", ask("5/0")["reply"])

    def test_math_never_executes_code_or_huge_powers(self):
        for hostile in ("__import__('os').system('id')", "9 ** 9 ** 9", "10 ** 400", "2 üzeri 100000"):
            self.assertIsNone(ask(hostile), hostile)

    def test_units(self):
        self.assertEqual(ask("100 km kaç mil")["reply"], "100 km = 62,14 mil")
        self.assertIn("22,22 °C", ask("72 f kaç c")["reply"])
        self.assertIn("3.072 MB", ask("3 gb kaç mb")["reply"])
        self.assertIsNone(ask("5 kg kaç km"))
        self.assertIn("mutlak sıfır", ask("-300 c kaç k")["reply"])

    def test_weather_named_default_and_tomorrow(self):
        london = ask("Londra'da hava nasıl")
        self.assertEqual(london["skill"], "weather")
        self.assertIn("Londra'da şu an 14°C", london["reply"])
        self.assertIn("Şemsiye", london["reply"])
        self.assertIn("Lefkoşa", ask("hava durumu")["reply"])
        self.assertIn("yarın", ask("yarın hava nasıl")["reply"])

    def test_weather_failure_is_honest(self):
        reply = ask("hava durumu", failing_fetch)["reply"]
        self.assertIn("ulaşamadım", reply)
        self.assertNotIn("°C", reply)

    def test_currency(self):
        reply = ask("100 dolar kaç tl")["reply"]
        self.assertIn("100 USD = 4.150 TRY", reply)
        self.assertIn("ulaşamadım", ask("euro kaç tl", failing_fetch)["reply"])

    def test_ordinary_conversation_goes_to_the_model(self):
        for text in ("merhaba nasılsın", "python nedir", "bana 3 öneri ver", "1 2 3",
                     "iklim değişikliği neden olur", "dolar neden yükseldi",
                     "uzun bir hikaye yaz 5 + 5 hakkında", "kaç yaşındayım"):
            self.assertIsNone(ask(text), text)

    def test_status_report_uses_only_real_rows(self):
        class Pool:
            async def fetchrow(self, *_):
                return {"last_seen": NOW, "online": True}

            async def fetchval(self, sql, *_):
                return 2 if "device_commands" in sql else 7

            async def fetch(self, *_):
                return [{"title": "Toplantı", "scheduled_time": datetime(2026, 1, 1, 18, 30).time(), "is_done": False}]

        reply = run(s.instant_reply("durum raporu", pool=Pool(), user_id="u", now=NOW))["reply"]
        self.assertIn("çevrimiçi", reply)
        self.assertIn("18:30 Toplantı", reply)
        broken = type("P", (), {"fetchrow": lambda *a: (_ for _ in ()).throw(RuntimeError())})()
        self.assertIn("tahmin etmiyorum", run(s.instant_reply("durum raporu", pool=broken, user_id="u"))["reply"])

    def test_clock_context_for_model(self):
        line = s.clock_context(NOW)
        self.assertIn("21 Ekim 2026 Çarşamba", line)
        self.assertIn("17:05", line)


if __name__ == "__main__":
    unittest.main()


class HelpSkill(unittest.TestCase):
    def test_help_lists_real_skills_and_limits(self):
        for q in ("neler yapabilirsin", "yardım", "ne yapabilirsin?", "komutların"):
            out = run(s.instant_reply(q, now=NOW))
            self.assertEqual(out["skill"], "help", q)
        reply = run(s.instant_reply("neler yapabilirsin", now=NOW))["reply"]
        for needle in ("hatırlat", "görev:", "laptop:", "Sınırlarım", "kapı kilidini açmam"):
            self.assertIn(needle, reply)

    def test_long_messages_are_not_hijacked(self):
        self.assertIsNone(run(s.instant_reply("bu uygulamanın komutlarını kullanarak bana uzun bir şiir yazar mısın lütfen güzel olsun", now=NOW)))
