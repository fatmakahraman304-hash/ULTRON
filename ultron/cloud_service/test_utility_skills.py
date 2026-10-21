import random
import unittest
from datetime import datetime, timezone

import utility_skills as u

NOW = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)


class UtilityTests(unittest.TestCase):
    def a(self, text):
        return u.answer(text, NOW, random.Random(3))

    def test_dates(self):
        self.assertIn("5 Aralık 2026 Cumartesi", self.a("45 gün sonra hangi gün"))
        self.assertIn("11 Kasım 2026", self.a("3 hafta sonra ne zaman"))
        self.assertIn("45 gün", self.a("1 mart 2026 ile 15 nisan 2026 arasında kaç gün"))
        self.assertIn("Çarşamba", self.a("5 mayıs 2027 hangi gün"))
        self.assertEqual(u._add_months(datetime(2026, 1, 31).date(), 1).day, 28)  # month-end clamp
        self.assertIn("36 yaşında", self.a("15.03.1990 doğumluyum kaç yaşındayım"))
        self.assertIsNone(self.a("15.03.2090 doğumluyum kaç yaşındayım"))

    def test_money_and_body(self):
        self.assertIn("212,50", self.a("850 lira 4 kişi böl"))
        self.assertIn("935,00", self.a("850 tl %10 bahşiş hesapla"))
        self.assertIn("233,75", self.a("hesap 850 4 kişi %10 bahşiş böl"))
        self.assertIn("23.1", self.a("boyum 180 kilom 75"))
        self.assertIsNone(self.a("boyum 20 kilom 75"))

    def test_random_is_bounded(self):
        self.assertRegex(self.a("yazı tura at"), r"(Yazı|Tura) geldi\.")
        self.assertIn("En fazla", self.a("50 zar at"))
        self.assertIn("🎯", self.a("seç: a, b, c"))
        self.assertIn("2–12", self.a("seç: sadece biri"))

    def test_ordinary_chat_is_not_intercepted(self):
        for t in ("zar atmak istiyorum", "yazı yazmak zor", "bana bir hikaye seç", "kilom çok arttı", "yarın hava nasıl", "merhaba"):
            self.assertIsNone(self.a(t), t)


if __name__ == "__main__":
    unittest.main()
