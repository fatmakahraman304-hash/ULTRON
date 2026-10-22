import os
import unittest
from datetime import date

import personality as pe
import style_skills as st

DAY = date(2026, 10, 22)


class PersonalityTests(unittest.TestCase):
    def test_default_is_the_playful_robot_and_env_can_change_it(self):
        self.assertEqual(pe.persona_of({}), "robot")
        self.assertEqual(pe.persona_of({"persona": "bogus"}), "robot")
        old = os.environ.get("GOLGE_DEFAULT_PERSONA")
        try:
            os.environ["GOLGE_DEFAULT_PERSONA"] = "normal"
            self.assertEqual(pe.persona_of({}), "normal")
            self.assertEqual(pe.persona_of({"persona": "robot"}), "robot")      # the owner's choice wins
        finally:
            if old is None:
                os.environ.pop("GOLGE_DEFAULT_PERSONA", None)
            else:
                os.environ["GOLGE_DEFAULT_PERSONA"] = old

    def test_persona_text_keeps_the_safety_rules(self):
        text = pe.persona_block({"persona": "robot"})
        for must in ("Never joke when the owner is stressed", "money trouble", "emergency", "do not claim real feelings", "information always comes first"):
            self.assertIn(must, text)
        self.assertIn("never joke about distress", pe.persona_block({"persona": "friend"}).lower().replace("never joke", "never joke"))
        combined = pe.effective_instruction({"persona": "robot", "length": "short"}, st.style_instruction)
        self.assertIn("PERSONALITY", combined)
        self.assertIn("very short", combined)

    def test_flavor_is_deterministic_rare_and_never_on_serious_or_failed_answers(self):
        style = {}
        replies = [f"Hatırlatıcı kuruldu: {i}. madde." for i in range(200)]
        decorated = [pe.decorate("reminder", r, style, DAY) for r in replies]
        flavored = [d for r, d in zip(replies, decorated) if d != r]
        self.assertTrue(20 <= len(flavored) <= 120)                              # about a third, never every answer
        self.assertEqual(decorated, [pe.decorate("reminder", r, style, DAY) for r in replies])   # deterministic
        self.assertTrue(all(d.startswith(r) and "\n\n🤖 " in d for r, d in zip(replies, decorated) if d != r))
        for skill in ("expenses", "ledger", "memory", "journal", "alerts", "approvals", "gaps", "feedback"):
            self.assertEqual(pe.decorate(skill, "Kaydettim.", style, DAY), "Kaydettim.")
        failing = ["⚠ Bütçeni aştın!", "Bulamadım", "Bu işlem yapılamıyor", "Kaydedemedim: hata"]
        self.assertTrue(all(pe.decorate("reminder", r, style, DAY) == r for r in failing))
        self.assertEqual(pe.decorate("habits", "😴 Uyku kaydedildi", style, DAY), "😴 Uyku kaydedildi")      # mood/sleep/weight are not joked about
        self.assertEqual(pe.decorate("reminder", "x" * 500, style, DAY), "x" * 500)
        self.assertEqual(pe.decorate("reminder", "Tamam", {"persona": "normal"}, DAY), "Tamam")
        self.assertEqual(pe.decorate("reminder", "Tamam", {"persona": "friend"}, DAY), "Tamam")

    def test_every_quip_is_short_and_clean(self):
        for skill, quips in pe.QUIPS.items():
            for q in quips:
                self.assertTrue(10 < len(q) < 90, (skill, q))
                self.assertFalse(any(m in q for m in pe._SKIP_MARKERS), q)

    def test_persona_commands_are_recognised_but_ordinary_chat_is_not(self):
        for t in ("robot modu aç", "şakacı robot ol", "robot gibi konuş", "samimi arkadaş modu", "normal mod", "robot modunu kapat", "kişiliğin ne", "ciddi mod"):
            self.assertTrue(st.wants_style(t), t)
        for t in ("robot filmi öner", "robot süpürge nasıl çalışır", "normal bir gün", "robot kolu göster"):
            self.assertFalse(st.wants_style(t), t)


if __name__ == "__main__":
    unittest.main()
