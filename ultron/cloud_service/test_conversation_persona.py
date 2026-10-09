"""Offline contract tests for shared ULTRON personality."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from conversation_persona import build_system_instruction, classify_tone


class TestConversationPersona(unittest.TestCase):
    def test_serious_overrides_joke(self):
        self.assertEqual(classify_tone("Param yok, şaka yap"), "serious")

    def test_requested_joke(self):
        self.assertEqual(classify_tone("Bana komik şaka yap"), "playful")

    def test_neutral(self):
        self.assertEqual(classify_tone("Merhaba"), "balanced")

    def test_consistent_identity(self):
        p = build_system_instruction(user_message="Merhaba")
        self.assertIn("You are ULTRON", p)
        self.assertIn("only the name ULTRON", p)

    def test_no_false_feelings(self):
        p = build_system_instruction()
        self.assertIn("Do not pretend to feel human emotions", p)

    def test_memory_untrusted_and_bounded(self):
        p = build_system_instruction(memory="m" * 8000, recent="r" * 8000,
                                     max_chars=5400, read_only=True)
        self.assertLessEqual(len(p), 5400)
        self.assertIn("<SAVED MEMORY>", p)
        self.assertIn("<RECENT CHAT>", p)
        self.assertIn("READ-ONLY MODE", p)

    def test_serious_instruction(self):
        p = build_system_instruction(user_message="Acil, hastayım")
        self.assertIn("No jokes or sarcasm", p)


    def test_explicit_personal_brief_is_grounded(self):
        p = build_system_instruction(
            user_message="Bugün ne yapmalıyım?",
            memory="Her salı İngilizce çalışırım",
            read_only=True
        )
        self.assertIn("PERSONAL BRIEFING", p)
        self.assertIn("do not invent appointments", p)
        self.assertIn("real tool confirms success", p)
        self.assertIn("Her salı İngilizce çalışırım", p)

    def test_unrequested_briefing_is_not_assumed(self):
        p = build_system_instruction(user_message="Merhaba")
        self.assertNotIn("PERSONAL BRIEFING", p)

    def test_owner_can_request_no_humour(self):
        p = build_system_instruction(user_message="Şaka yapma, ciddi konuş.")
        self.assertIn("Owner requests serious tone", p)
        self.assertIn("do not claim to store a permanent preference", p)

    def test_privacy_and_connected_device_limits(self):
        p = build_system_instruction()
        self.assertIn("explicit user permission", p)
        self.assertIn("physical limits", p)

    def test_integration_contract(self):
        app = (HERE / "app.py").read_text(encoding="utf-8")
        local = (HERE / "local_brain_bridge.py").read_text(encoding="utf-8")
        self.assertIn("from conversation_persona import build_system_instruction", app)
        self.assertIn("from conversation_persona import build_system_instruction", local)
        self.assertGreaterEqual(app.count("build_system_instruction("), 5)
        self.assertIn("read_only=True", local)


if __name__ == "__main__":
    unittest.main()
