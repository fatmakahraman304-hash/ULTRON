import unittest
from datetime import datetime, timezone

import calc_skills as c

NOW = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)


class CalcTests(unittest.TestCase):
    def a(self, text):
        return c.answer(text, NOW)

    def test_money(self):
        self.assertIn("10.046,21 ₺", self.a("kredi taksiti: 100000 tl 12 ay aylık %3"))
        self.assertIn("yıllık %45 bileşik", self.a("kredi 250.000 tl 24 ay yıllık %45 faiz"))
        self.assertIn("27.440 ₺", self.a("10000 tl yıllık %40 faizle 3 yıl"))
        self.assertIn("1.200 ₺ (KDV 200 ₺)", self.a("1000 tl kdv ekle"))
        self.assertIn("1.090,91 ₺", self.a("1200 tl kdv dahil kdv ayır %10"))
        self.assertIn("ödenecek 350 ₺", self.a("500 tl %30 indirim"))
        self.assertIn("%50 artış", self.a("100'den 150'ye yüzde kaç artış"))
        self.assertIn("%25 azalış", self.a("200'den 150'ye yüzde kaç azalış"))
        self.assertIn("3,15 ₺", self.a("yakıt maliyeti: 100 km 7 litre 45 tl"))
        self.assertIsNone(self.a("kredi taksiti: 100000 tl 0 ay aylık %3"))
        self.assertIsNone(self.a("0'dan 5'e yüzde kaç artış"))          # division by zero never raises

    def test_numbers(self):
        self.assertIn("10,75", self.a("ortalama: 4 8 15 16"))
        self.assertIn("medyan: 6", self.a("medyan: 9 1 6"))
        self.assertEqual(self.a("97 asal mı"), "97 asal bir sayı.")
        self.assertIn("en küçük böleni 3", self.a("9 asal mı"))
        self.assertIn("2 × 2 × 2 × 3 × 3 × 5", self.a("360 asal çarpan"))
        self.assertIn("3.628.800", self.a("10 faktöriyel"))
        self.assertIn("EKOK = 36", self.a("12 ile 18 ekok"))
        self.assertIn("55", self.a("fibonacci 10"))
        self.assertIn("bin iki yüz otuz dört", self.a("1234 yazıyla"))
        self.assertIn("bin bir", self.a("1001 yazıyla"))
        self.assertIn("milyon", self.a("2500000 yazıyla"))
        self.assertIn("XIV", self.a("14 roma rakamı"))
        self.assertIn("= 14", self.a("roma rakamı XIV"))
        self.assertIn("geçerli bir Roma", self.a("roma rakamı IIII"))
        self.assertIn("FF", self.a("255 onaltılık"))
        self.assertIn("= 10", self.a("ikilik 1010 kaç"))
        self.assertIn("bir sayı değil", self.a("ikilik 12 kaç"))

    def test_life(self):
        self.assertIn("21:46", self.a("7'de uyanmak için ne zaman yatmalıyım"))
        self.assertIn("Balık", self.a("15 mart burcum"))
        self.assertIn("Oğlak", self.a("5 ocak burcum"))
        self.assertIn("Oğlak", self.a("25 aralık burcum"))
        self.assertIn("Koç", self.a("25 mart burcum"))
        self.assertIn("At yılı", self.a("1990 çin burcu"))
        self.assertIn("6:00 dk/km", self.a("5 km 30 dk tempo"))
        self.assertIn("1780 kcal", self.a("günlük kalori ihtiyacı: 30 yaş 80 kilo 180 erkek"))
        self.assertIn("tıbbi", self.a("günlük kalori ihtiyacı: 30 yaş 80 kilo 180 erkek"))
        self.assertIn("125 gram", self.a("1 bardak un kaç gram"))
        self.assertIn("08:00", self.a("istanbul 15:00 new york kaç"))
        self.assertIn("22 iş günü", self.a("1 mart ile 31 mart arası kaç iş günü"))
        self.assertIn("Cumhuriyet Bayramı", self.a("bir sonraki resmi tatil ne zaman"))
        self.assertIn("294. günü", self.a("yılın kaçıncı günü"))
        self.assertIn("6 kişilik tarif (×1,5): 3 bardak un, 4,5 yumurta", self.a("tarif 4 kişilik 6 kişiliğe: 2 bardak un, 3 yumurta"))

    def test_text_and_codes(self):
        self.assertEqual(self.a("büyük harf yap: istanbul ığdır"), "İSTANBUL IĞDIR")
        self.assertEqual(self.a("küçük harf yap: IĞDIR İZMİR"), "ığdır izmir")
        self.assertEqual(self.a("ters çevir: merhaba"), "abahrem")
        self.assertIn("palindrom.", self.a("palindrom mu: Ey Edip adanada pide ye"))
        self.assertIn("4 kelime", self.a("kelime say: bugün hava çok güzel"))
        self.assertEqual(self.a("base64 kodla: merhaba"), "bWVyaGFiYQ==")
        self.assertEqual(self.a("base64 çöz: bWVyaGFiYQ=="), "merhaba")
        self.assertIn("geçerli bir Base64", self.a("base64 çöz: ***"))
        self.assertEqual(self.a("mors: sos"), "... --- ...")
        self.assertIn("rgb(255, 136, 0)", self.a("#ff8800 rgb"))
        self.assertIn("#FF8800", self.a("rgb 255 136 0"))
        self.assertIsNone(self.a("rgb 300 0 0"))

    def test_ordinary_chat_is_not_intercepted(self):
        for t in ("evet", "10 kişi geldi", "kredi çekmek istiyorum", "kdv nedir", "ortalama notum nedir", "hava nasıl", "ters bir durum var",
                  "mors alfabesi nedir", "base64 nedir", "asal sayılar ne işe yarar", "burcum uyumlu mu", "tarif ver", "resmi tatil olsa iyi olur"):
            self.assertIsNone(self.a(t), t)

    def test_bounds_and_crashes(self):
        for t in ("99999999999999999999 asal mı", "999 faktöriyel", "fibonacci 999", "50000000000000000 yazıyla", "10000 roma rakamı",
                  "kredi taksiti: 1000 tl 999 ay aylık %3", "1 mart 2026 ile 1 mart 2999 arası kaç iş günü", "30 şubat burcum"):
            self.a(t)   # must not raise


if __name__ == "__main__":
    unittest.main()
