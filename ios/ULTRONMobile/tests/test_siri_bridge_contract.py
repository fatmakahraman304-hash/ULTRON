"""Static mobile/Cloud contract guards; Xcode CI separately compiles the Swift app.

These tests do not simulate actual iOS background execution or Siri delivery.
"""
import unittest
from pathlib import Path


SOURCES = Path(__file__).resolve().parents[1] / "Sources"


class SiriBridgeContractTests(unittest.TestCase):
    def source(self, filename):
        return (SOURCES / filename).read_text(encoding="utf-8")

    def test_siri_dispatch_reuses_authenticated_cloud_desktop_queue(self):
        text = self.source("CloudSession.swift")
        self.assertIn("func enqueueDesktopTask(", text)
        self.assertIn("try await ensureLogin()", text)
        self.assertIn('"target": "desktop"', text)
        self.assertIn('"command": "agent_task"', text)
        self.assertIn('"/api/device-commands"', text)
        self.assertIn("DesktopTaskError.notQueued", text)
        self.assertNotIn("ULTRON_DEVICE_TOKEN", text)

    def test_cloud_shortcut_requires_explicit_foreground_user_action(self):
        router = self.source("PhoneActionRouter.swift")
        view = self.source("ContentView.swift")
        self.assertIn('item.action == "shortcut_bridge" && !userInitiated', router)
        self.assertIn("resumePendingActionIfPossible(userInitiated: true)", view)
        self.assertIn('guard name == "ULTRON Bridge"', router)
        self.assertIn('case "shortcut_bridge":', router)
        self.assertIn('URLQueryItem(name: "name", value: "ULTRON Bridge")', router)

    def test_pending_action_payload_is_keychain_backed(self):
        router = self.source("PhoneActionRouter.swift")
        keychain = self.source("KeychainStore.swift")
        self.assertIn("KeychainStore.save(text, account: secureAccount)", router)
        self.assertIn("KeychainStore.read(account: secureAccount)", router)
        self.assertIn("KeychainStore.delete(account: secureAccount)", router)
        self.assertIn("kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly", keychain)
        self.assertNotIn("UserDefaults.standard.set(data, forKey: defaultsKey)", router)

    def test_native_voice_events_are_actually_handled(self):
        voice = self.source("BackgroundVoiceController.swift")
        self.assertIn('case "ios_action":', voice)
        self.assertIn("prepareIOSBridgeCommand", voice)
        self.assertIn('case "ios_shortcut":', voice)
        self.assertIn("prepareNamedShortcut", voice)
        self.assertIn('case "laptop_task":', voice)

    def test_siri_question_and_task_status_are_bounded_network_requests(self):
        cloud = self.source("CloudSession.swift")
        intents = self.source("ULTRONAppIntents.swift")
        self.assertIn('"/api/chat"', cloud)
        self.assertIn('"/api/device-commands/recent"', cloud)
        self.assertIn("URLQueryItem(name: \"limit\", value: \"1\")", cloud)
        for name in ("AskULTRONIntent", "SendULTRONDesktopTaskIntent",
                     "CheckULTRONDesktopTaskIntent"):
            self.assertIn("struct " + name + ": AppIntent", intents)
        self.assertIn("static var openAppWhenRun = false", intents)


if __name__ == "__main__":
    unittest.main()
