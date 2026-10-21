"""Regression tests for open_app's launch verification and new aliases.

Before this fix, open_app() reported "Opened X." the instant the launcher
call didn't raise an exception — never checking that a window actually
appeared. These tests mock the window-enumeration helpers (no real process
is launched) to pin down the honest-reporting contract.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from actions import open_app


class OpenAppVerificationTests(unittest.TestCase):
    def setUp(self):
        self._orig_launchers = dict(open_app._OS_LAUNCHERS)
        self._orig_window_titles = open_app._window_titles
        self._orig_wait = open_app._wait_for_new_window

    def tearDown(self):
        open_app._OS_LAUNCHERS = self._orig_launchers
        open_app._window_titles = self._orig_window_titles
        open_app._wait_for_new_window = self._orig_wait

    def test_reports_the_new_window_title_when_one_appears(self):
        open_app._OS_LAUNCHERS[open_app._SYSTEM] = lambda name: True
        open_app._window_titles = lambda: set()
        open_app._wait_for_new_window = lambda before, timeout=6.0: "Hesap Makinesi"

        result = open_app.open_app({"app_name": "calculator"})

        self.assertIn("Hesap Makinesi", result)
        self.assertIn("calculator", result)

    def test_does_not_claim_success_when_no_new_window_appears(self):
        open_app._OS_LAUNCHERS[open_app._SYSTEM] = lambda name: True
        open_app._window_titles = lambda: set()
        open_app._wait_for_new_window = lambda before, timeout=6.0: None

        result = open_app.open_app({"app_name": "calculator"})

        if open_app._SYSTEM == "Windows":
            self.assertIn("doğrulanamadı", result)
        self.assertNotIn("Opened calculator.", result)

    def test_launcher_failure_is_not_reported_as_success(self):
        open_app._OS_LAUNCHERS[open_app._SYSTEM] = lambda name: False

        result = open_app.open_app({"app_name": "nonexistent_app_xyz"})

        self.assertIn("Could not confirm", result)

    def test_about_alias_resolves_to_ms_settings_about(self):
        self.assertEqual(open_app._normalize("about"), open_app._APP_ALIASES["about"][open_app._SYSTEM])
        if open_app._SYSTEM == "Windows":
            self.assertEqual(open_app._normalize("sistem hakkında"), "ms-settings:about")


if __name__ == "__main__":
    unittest.main()
