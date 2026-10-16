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

    def test_user_facing_legacy_labels_are_rebranded_without_renaming_protocols(self):
        dashboard = source("ultron/frontend/src/dashboard/Dashboard.tsx")
        runtime = source("ultron/frontend/src/dashboard/runtime.ts")
        notes = source("ultron/cloud_service/static/conversation-notes.js")
        merged = source("ultron/backend/merged_api.py")
        cloud_app = source("ultron/cloud_service/app.py")
        settings = source("ultron/backend/config/settings.json")
        persona = source("ultron/backend/app/agent/persona_guard.py")
        agent = source("ultron/backend/app/agent/agent.py")
        supervisor = source("ultron/backend/app/agent/supervisor.py")
        local_runtime = source("ultron/backend/app/core/runtime.py")
        cloud_bridge = source("ultron/backend/sitecustomize.py")
        tts = source("ultron/backend/app/voice/tts.py")
        health = source("ultron/backend/health.py")
        self.assertNotIn("MARK video", dashboard)
        self.assertNotIn("MARK video", runtime)
        self.assertIn("Video GÖLGE çalışma alanında açılıyor.", dashboard)
        self.assertIn("Önce GÖLGE ile bir sohbet başlat.", notes)
        self.assertIn("GÖLGE masaüstü uygulamasında kullanılabilir", merged)
        self.assertNotIn("ULTRON uses the original MARK desktop interface", merged)
        self.assertIn("'service': 'GÖLGE'", merged)
        self.assertIn('"service": "GÖLGE"', cloud_app)
        self.assertNotIn('"service": "ultron-cloud"', cloud_app)
        self.assertIn("audio_owner = 'desktop'", merged)
        self.assertIn("Sen GÖLGE'sin", persona)
        self.assertNotIn("Sen ULTRON'sun", persona)
        self.assertIn("Sen GÖLGE'sin", agent)
        self.assertNotIn("Sen Ultron'sın", agent)
        self.assertIn('"GÖLGE FINAL REPORT"', supervisor)
        self.assertNotIn('"ULTRON FINAL REPORT"', supervisor)
        self.assertIn("GÖLGE şu anda çevrimdışı", local_runtime)
        self.assertIn("[GÖLGE-RUNTIME]", local_runtime)
        self.assertIn("GÖLGE Cloud ile düşünüyor", cloud_bridge)
        self.assertIn("GÖLGE hazır.", tts)
        self.assertIn("[GÖLGE-HEALTH]", health)
        self.assertIn('"ultron_name": "GÖLGE"', settings)
        # Old wake model and transport identifiers are intentionally untouched.
        self.assertIn('"wake_word": "ultron"', settings)
        self.assertIn("X-MARK-Token", merged)

if __name__ == "__main__":
    unittest.main()
