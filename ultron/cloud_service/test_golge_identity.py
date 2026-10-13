"""GÖLGE rebrand regression tests without touching saved credentials."""
import unittest
from unittest.mock import patch
from pathlib import Path

from memory import config_manager
from ultron.cloud_service.development_updates import dev_intent


class GolgeIdentityTests(unittest.TestCase):
    def test_legacy_saved_name_migrates_in_memory_without_overwriting_custom_name(self):
        for saved, expected in [
            ({}, "GÖLGE"),
            ({"assistant_name": "ULTRON"}, "GÖLGE"),
            ({"assistant_name": "ultron"}, "GÖLGE"),
            ({"assistant_name": "GÖLGE"}, "GÖLGE"),
            ({"assistant_name": "Başka Asistan"}, "Başka Asistan"),
        ]:
            with self.subTest(saved=saved):
                with patch.object(config_manager, "load_api_keys", return_value=saved):
                    self.assertEqual(config_manager.get_assistant_name(), expected)

    def test_new_owner_development_intents_still_accepted(self):
        self.assertTrue(dev_intent("GÖLGE, kendini geliştir"))
        self.assertTrue(dev_intent("gölge arayüzünü güncelle"))
        self.assertTrue(dev_intent("ULTRON sistemini güncelle"))
        self.assertFalse(dev_intent("Bugün hava nasıl?"))

    def test_desktop_and_cloud_identify_as_golge_without_breaking_auth_headers(self):
        root = Path(__file__).resolve().parents[2]
        qt = (root / "ui.py").read_text(encoding="utf-8")
        local = (root / "mark_app.py").read_text(encoding="utf-8")
        web = (root / "integration/web_panel.py").read_text(encoding="utf-8")
        cloud = (root / "ultron/cloud_service/app.py").read_text(encoding="utf-8")
        self.assertIn('"GÖLGE AI Assistant"', qt)
        self.assertIn('GÖLGE.lnk', qt)
        self.assertIn('self._asst_name = "GÖLGE"', local)
        self.assertIn('GÖLGE:', web)
        self.assertIn('X-ULTRON-DEVICE', web)
        self.assertIn('X-ULTRON-DEVICE', cloud)
        self.assertIn('ULTRON_SESSION_SECRET', cloud)


if __name__ == "__main__":
    unittest.main()
