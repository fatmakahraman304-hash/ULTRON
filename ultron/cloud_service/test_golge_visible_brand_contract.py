"""GÖLGE user-facing name: native iOS, Windows dashboard, PWA.

This deliberately preserves *technical* keys and Swift symbols to prevent
account loss, broken existing deep links and protocol incompatibility.
"""
from __future__ import annotations
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


def source(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


class VisibleGolgeBrandContract(unittest.TestCase):
    def test_desktop_display_defaults_and_video_titles(self):
        dashboard = source("ultron/frontend/src/dashboard/Dashboard.tsx")
        runtime = source("ultron/frontend/src/dashboard/runtime.ts")
        hologram = source("ultron/frontend/hologram.html")
        self.assertNotIn("ULTRON", dashboard)
        self.assertNotIn("'ULTRON'", runtime)
        self.assertIn("GÖLGE", dashboard)
        self.assertIn("title:'GÖLGE'", runtime)
        self.assertIn("<title>GÖLGE Hologram</title>", hologram)

    def test_native_iphone_display_and_shortcut_talk(self):
        project = source("ios/ULTRONMobile/project.yml")
        content = source("ios/ULTRONMobile/Sources/ContentView.swift")
        intents = source("ios/ULTRONMobile/Sources/ULTRONAppIntents.swift")
        self.assertIn("CFBundleDisplayName: GÖLGE", project)
        self.assertIn("NSMicrophoneUsageDescription: GÖLGE,", project)
        self.assertIn('Text("GÖLGE")', content)
        self.assertNotIn('"ULTRON', content)
        self.assertNotIn('"ULTRON', intents)
        self.assertIn('static var title: LocalizedStringResource = "GÖLGE Dinlemeyi Başlat"', intents)
        self.assertIn('static var title: LocalizedStringResource = "GÖLGE\'ye Sor"', intents)
        # Do not silently rename native API methods or AppIntent classes:
        self.assertIn("struct AskULTRONIntent: AppIntent", intents)
        self.assertIn("CloudSession.shared.askULTRON(question)", intents)

    def test_new_shortcut_name_and_old_shortcut_remain_compatible(self):
        router = source("ios/ULTRONMobile/Sources/PhoneActionRouter.swift")
        self.assertIn('URLQueryItem(name: "name", value: "GÖLGE Bridge")', router)
        self.assertIn('name == "GÖLGE Bridge" || name == "ULTRON Bridge"', router)
        self.assertIn('content.title = "GÖLGE"', router)
        self.assertIn('"source": "ultron"', router)

    def test_cloud_sessions_and_saved_credentials_not_migrated(self):
        cloud = source("ios/ULTRONMobile/Sources/CloudSession.swift")
        self.assertIn("Windows GÖLGE ve Ollama", cloud)
        self.assertIn('"X-ULTRON-DEVICE"', cloud)
        self.assertIn('"ultron.siri.conversation_id"', cloud)
        self.assertIn("com.ultron.mobile", source("ios/ULTRONMobile/project.yml"))
        html = source("ultron/cloud_service/static/index.html")
        self.assertIn("<title>GÖLGE Mobile</title>", html)
        self.assertNotIn("<title>ULTRON", html)

if __name__ == "__main__":
    unittest.main()
