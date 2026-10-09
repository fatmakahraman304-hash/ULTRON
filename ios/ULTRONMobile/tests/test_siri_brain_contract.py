"""iOS Siri free-first brain selection contracts (does not emulate Siri runtime)."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/"Sources"
SESSION=(ROOT/"CloudSession.swift").read_text(encoding="utf-8")
CONTENT=(ROOT/"ContentView.swift").read_text(encoding="utf-8")

class NativeSiriBrainTests(unittest.TestCase):
    def test_default_is_free_local_without_hidden_paid_fallback(self):
        self.assertIn('== "gemini"',SESSION)
        self.assertIn('geminiSelected ? "/api/chat" : "/api/local-chat"',SESSION)
        self.assertIn('for _ in 0..<25',SESSION)
        self.assertIn('throw DesktopTaskError.localTimeout',SESSION)
        self.assertIn('throw DesktopTaskError.localDesktopOffline',SESSION)
        self.assertNotIn('catch { return try await askGemini',SESSION)
    def test_native_user_can_explicitly_pick_gemini(self):
        self.assertIn('@AppStorage("ultron.siri.brain_mode")',CONTENT)
        self.assertIn('private var siriBrainMode = "local"',CONTENT)
        self.assertIn('Text("Gemini • isteğe bağlı").tag("gemini")',CONTENT)
        self.assertIn('Text("Qwen • ücretsiz laptop").tag("local")',CONTENT)
    def test_native_continuous_audio_still_labeled_gemini(self):
        self.assertIn("Sürekli dinleme hâlâ isteğe bağlı Gemini Live",CONTENT)
        self.assertIn("Continuous Live audio is independent and remains Gemini Live.",SESSION)


if __name__=="__main__":
    unittest.main()
