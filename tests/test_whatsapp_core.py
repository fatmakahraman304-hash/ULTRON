"""Regression tests for the verified WhatsApp Desktop driver.

No real window, keystroke, or message is involved: pywinauto/pyautogui are
replaced with fakes so these tests can run anywhere, including CI. What they
protect is the fail-closed behavior itself — every point where the old blind
keystroke sequence could silently land in (or claim) the wrong place.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plugins import _whatsapp_core as wa


class _FakeElementInfo:
    def __init__(self, name="", automation_id=""):
        self.name = name
        self.automation_id = automation_id


class _FakeRect:
    def __init__(self, left):
        self.left = left


class _FakeControl:
    def __init__(self, left, text="", value=None, name="", visible=True):
        self._left = left
        self._text = text
        self._value = text if value is None else value
        self.element_info = _FakeElementInfo(name=name)
        self._visible = visible
        self.click_input = MagicMock()

    def is_visible(self):
        return self._visible

    def rectangle(self):
        return _FakeRect(self._left)

    def window_text(self):
        return self._text

    def get_value(self):
        return self._value


class _FakeWindow:
    def __init__(self, search, compose, rows):
        self._search = search
        self._compose = compose
        self._rows = rows
        self.restore = MagicMock()
        self.set_focus = MagicMock()

    def descendants(self, control_type=None):
        if control_type == "Edit":
            return [self._search, self._compose]
        if control_type == "DataItem":
            return self._rows
        return []


class WhatsAppDriverTests(unittest.TestCase):
    def setUp(self):
        self.fake_pyautogui = MagicMock()
        self.fake_pyperclip = MagicMock()
        wa.pyautogui = self.fake_pyautogui
        wa.pyperclip = self.fake_pyperclip
        self.fake_pyperclip.paste.return_value = "önceki pano içeriği"
        wa._AVAILABLE = True
        self._orig_filter_timeout = wa._FILTER_TIMEOUT_SECONDS
        self._orig_send_timeout = wa._SEND_TIMEOUT_SECONDS
        self._orig_poll = wa._POLL_INTERVAL_SECONDS
        wa._FILTER_TIMEOUT_SECONDS = 0.05
        wa._SEND_TIMEOUT_SECONDS = 0.05
        wa._POLL_INTERVAL_SECONDS = 0.01

    def tearDown(self):
        wa._FILTER_TIMEOUT_SECONDS = self._orig_filter_timeout
        wa._SEND_TIMEOUT_SECONDS = self._orig_send_timeout
        wa._POLL_INTERVAL_SECONDS = self._orig_poll

    def _make_transport(self, search, compose, rows):
        return wa._WhatsAppTransport(_FakeWindow(search, compose, rows))

    def test_sends_only_after_label_and_echo_confirm_the_right_chat(self):
        search = _FakeControl(left=100, text="")
        row = _FakeControl(left=200, text="Mert Pazartesi Birazdan gidecem cano")
        compose = _FakeControl(
            left=700, text="Merhaba", name="Mert sohbetine bir mesaj yazın",
        )
        transport = self._make_transport(search, compose, [row])

        # After Enter, the real box reports the empty state as "\n".
        def press(key):
            if key == "enter":
                compose._text = "\n"
                compose._value = "\n"
        self.fake_pyautogui.press.side_effect = press

        ok, reason = transport.send_message_to("Mert", "Merhaba")

        self.assertTrue(ok)
        self.assertEqual(reason, "")
        row.click_input.assert_called_once()
        # The user's own clipboard must survive this call unchanged.
        self.assertEqual(self.fake_pyperclip.copy.call_args_list[-1].args[0], "önceki pano içeriği")

    def test_no_matching_chat_row_fails_closed(self):
        search = _FakeControl(left=100, text="")
        compose = _FakeControl(left=700, text="\n", name="")
        transport = self._make_transport(search, compose, rows=[])

        ok, reason = transport.send_message_to("Kimse Yok", "Merhaba")

        self.assertFalse(ok)
        self.assertIn("eşleşen bir sohbet bulunamadı", reason)

    def test_mismatched_compose_label_refuses_to_type(self):
        """The row we clicked opened some OTHER conversation — must not type."""
        search = _FakeControl(left=100, text="")
        row = _FakeControl(left=200, text="Mert Pazartesi Birazdan gidecem cano")
        compose = _FakeControl(
            left=700, text="\n", name="Ayşe sohbetine bir mesaj yazın",
        )
        transport = self._make_transport(search, compose, [row])

        ok, reason = transport.send_message_to("Mert", "Merhaba")

        self.assertFalse(ok)
        self.assertIn("eşleşmiyor", reason)
        self.fake_pyperclip.copy.assert_called_once_with("Mert")  # only the search, never the message

    def test_paste_mismatch_is_not_reported_as_sent(self):
        search = _FakeControl(left=100, text="")
        row = _FakeControl(left=200, text="Mert Pazartesi Birazdan gidecem cano")
        compose = _FakeControl(
            left=700, text="\n", name="Mert sohbetine bir mesaj yazın",
        )
        transport = self._make_transport(search, compose, [row])
        # Paste never lands in the fake box, so its text stays empty.

        ok, reason = transport.send_message_to("Mert", "Merhaba")

        self.assertFalse(ok)
        self.assertIn("tam yansımadı", reason)
        enter_presses = [c for c in self.fake_pyautogui.press.call_args_list if c.args == ("enter",)]
        self.assertEqual(enter_presses, [])  # Enter never sent

    def test_box_not_emptying_after_enter_is_not_reported_as_sent(self):
        search = _FakeControl(left=100, text="")
        row = _FakeControl(left=200, text="Mert Pazartesi Birazdan gidecem cano")
        compose = _FakeControl(
            left=700, text="Merhaba", name="Mert sohbetine bir mesaj yazın",
        )
        transport = self._make_transport(search, compose, [row])
        # Enter is pressed but the box (simulating a stuck/failed send) never clears.

        ok, reason = transport.send_message_to("Mert", "Merhaba")

        self.assertFalse(ok)
        self.assertIn("boşalmadı", reason)

    def test_turkish_fold_matches_case_and_diacritics(self):
        self.assertEqual(wa._fold("İstanbul"), wa._fold("istanbul"))
        self.assertEqual(wa._fold("Çağla"), wa._fold("cagla"))

    def test_get_reports_reason_when_window_missing(self):
        original = wa._find_window
        wa._find_window = lambda: None
        try:
            transport, reason = wa.get()
        finally:
            wa._find_window = original
        self.assertIsNone(transport)
        self.assertIn("bulunamadı", reason)


if __name__ == "__main__":
    unittest.main()
