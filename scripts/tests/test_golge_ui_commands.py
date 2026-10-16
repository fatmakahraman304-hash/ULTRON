import unittest
from pathlib import Path

from integration.golge_ui_commands import is_stop_command


class GolgeUiCommandTests(unittest.TestCase):
    def test_exact_stop_phrases_are_recognized_with_turkish_normalization(self):
        for phrase in ("Dur", "GÖLGE sus.", "Konuşmayı kes", "Konuşmayı durdur", "Yanıtı durdur", "TTS durdur"):
            with self.subTest(phrase=phrase):
                self.assertTrue(is_stop_command(phrase))

    def test_non_stop_sentences_are_not_interrupted(self):
        for phrase in ("Durumu açıkla", "Dünya durmadan dönüyor", "Bir dakika bekle", "Susamlı tarif"):
            with self.subTest(phrase=phrase):
                self.assertFalse(is_stop_command(phrase))

    def test_native_qt_send_short_circuits_the_model_and_calls_real_interrupt(self):
        source = Path(__file__).resolve().parents[2].joinpath("integration", "web_panel.py").read_text(encoding="utf-8")
        start = source.index("    def send(self, text):")
        end = source.index("    @pyqtSlot(str, str)", start)
        implementation = source[start:end]
        self.assertLess(implementation.index("if is_stop_command(text)"), implementation.index("self.ui.on_text_command"))
        self.assertIn("self.ui._win._do_interrupt()", implementation)


if __name__ == "__main__":
    unittest.main()
