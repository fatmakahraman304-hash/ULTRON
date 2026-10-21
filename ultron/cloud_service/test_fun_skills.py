import random
import unittest
from datetime import datetime, timezone

import fun_skills as fun

NOW = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)


class FunTests(unittest.TestCase):
    def a(self, text, seed=1):
        return fun.answer(text, NOW, random.Random(seed))

    def test_every_content_command_answers(self):
        for text, marker in (("motivasyon ver", "💪"), ("atasözü", "Anlamı"), ("deyim", "Anlamı"), ("espri yap", "😄"), ("ilginç bilgi", "💡"),
                             ("günün kelimesi", "Günün kelimesi"), ("tasarruf ipucu", "💰"), ("verimlilik ipucu", "🎯"), ("uyku hijyeni", "😴"),
                             ("ne yesem", "fikirler"), ("akşam yemeği önerisi", "Akşam"), ("tatlı önerisi", "Tatlı"), ("nefes egzersizi", "4-7-8"),
                             ("göz dinlendirme", "20-20-20"), ("esneme hareketleri", "esneme"), ("8 top: bugün şanslı mıyım", "🎱"),
                             ("iltifat et", ""), ("günün tavsiyesi", "✅")):
            reply = self.a(text)
            self.assertTrue(reply and marker in reply, text)

    def test_word_of_the_day_is_stable_within_a_day(self):
        self.assertEqual(self.a("günün kelimesi", 1), self.a("günün kelimesi", 99))

    def test_rock_paper_scissors_rules(self):
        outcomes = set()
        for seed in range(40):
            reply = self.a("taş kağıt makas: taş", seed)
            outcomes.add("Berabere" in reply and "tie" or ("Sen kazandın" in reply and "win") or "lose")
        self.assertEqual(outcomes, {"tie", "win", "lose"})
        self.assertIn("Seçimini yaz", self.a("taş kağıt makas oyna"))

    def test_medical_style_texts_carry_a_disclaimer(self):
        self.assertIn("tıbbi tavsiye değildir", self.a("nefes egzersizi"))
        self.assertIn("uzmana danış", self.a("esneme hareketleri"))

    def test_content_quality_guards(self):
        for seq in (fun.MOTIVATION, fun.JOKES, fun.FACTS, fun.TIPS, fun.SAVING, fun.PRODUCTIVITY, fun.SLEEP_HYGIENE, fun.COMPLIMENTS):
            self.assertTrue(all(isinstance(x, str) and 15 < len(x) < 260 for x in seq))
        for seq in (fun.PROVERBS, fun.IDIOMS, fun.WORDS, fun.RIDDLES):
            self.assertTrue(all(len(x) == 2 and all(x) for x in seq))
        self.assertEqual(len(set(fun.FACTS)), len(fun.FACTS))
        self.assertTrue(all(fun.RIDDLES[i][1] == fun.RIDDLES[i][1].lower() for i in range(len(fun.RIDDLES))))

    def test_ordinary_chat_is_not_intercepted(self):
        for t in ("motivasyon nedir", "espri anlıyor musun", "atasözü yazıyorum", "bilgi ver", "tavsiye ver", "bana bir tavsiye ver", "ne yesem bilemedim",
                  "deyim öğrenmek istiyorum", "taş atmak yasak mı", "hava nasıl"):
            self.assertIsNone(self.a(t), t)


if __name__ == "__main__":
    unittest.main()
