"""Offline regression checks for desktop ULTRON's respectful personality."""
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
from app.agent.persona_guard import ANCHOR, PersonaGuard, analyze


class TestDesktopPersona(unittest.TestCase):
    def test_anchor_is_supportive(self):
        self.assertIn("saygılı", ANCHOR)
        self.assertIn("ULTRON", ANCHOR)
        self.assertIn("şaka", ANCHOR.lower())
        self.assertNotIn("Biyolojik zaaflarla alay", ANCHOR)

    def test_direct_response_needs_no_forced_boss(self):
        with tempfile.TemporaryDirectory() as temp:
            guard = PersonaGuard(log_path=str(Path(temp) / "drift.db"))
            report = guard.check("İşlemi doğruladım. Sonuç hazır.")
            self.assertEqual(report["violations"], [])
            self.assertFalse(report["anchored_next"])

    def test_normal_apology_is_not_persona_violation(self):
        self.assertEqual(analyze("Üzgünüm, şu an bağlantı kurulamıyor.")["violations"], [])

    def test_agent_postprocessor_no_forced_prefix(self):
        source = (BACKEND / "app" / "agent" / "agent.py").read_text(encoding="utf-8")
        self.assertIn("return PersonaGuard.reframe(answer)", source)
        self.assertNotIn("return self._boss_hitap(answer)", source)
        self.assertNotIn("soğuk, hesapçı, otoriter", source)


if __name__ == "__main__":
    unittest.main()
