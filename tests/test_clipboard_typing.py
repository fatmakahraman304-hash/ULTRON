"""Regression tests for Turkish-character typing and clipboard preservation.

Confirmed bug: pyautogui's keystroke table (KEYBOARD_KEYS) has no entry for
ğ ü ş ı ö ç İ Ğ Ü Ş Ö Ç — pyautogui.typewrite()/.write() cannot type any
Turkish-specific letter. The fix routes such text through the clipboard
instead, and must put the user's previous clipboard content back afterward.
All pyautogui/pyperclip calls are mocked; nothing is typed into a real window.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import clipboard_safe
from actions import computer_control


class ClipboardSafeTests(unittest.TestCase):
    def setUp(self):
        self.fake_pyautogui = MagicMock()
        self.fake_pyperclip = MagicMock()
        self.fake_pyperclip.paste.return_value = "kullanıcının eski panosu"
        clipboard_safe.pyautogui = self.fake_pyautogui
        clipboard_safe.pyperclip = self.fake_pyperclip
        clipboard_safe._PYAUTOGUI = True
        clipboard_safe._PYPERCLIP = True

    def test_needs_clipboard_true_for_turkish_letters(self):
        for word in ("öğrenci", "İstanbul", "güneş", "çiçek"):
            self.assertTrue(clipboard_safe.needs_clipboard(word), word)

    def test_needs_clipboard_false_for_plain_ascii(self):
        self.assertFalse(clipboard_safe.needs_clipboard("Hello world 123!"))

    def test_paste_text_restores_previous_clipboard(self):
        ok = clipboard_safe.paste_text("Çağla'ya mesaj gönder")

        self.assertTrue(ok)
        copy_calls = [c.args[0] for c in self.fake_pyperclip.copy.call_args_list]
        self.assertEqual(copy_calls, ["Çağla'ya mesaj gönder", "kullanıcının eski panosu"])
        self.fake_pyautogui.hotkey.assert_called_once_with("ctrl", "v")

    def test_paste_text_uses_command_v_on_mac(self):
        clipboard_safe.paste_text("şşş", mac=True)
        self.fake_pyautogui.hotkey.assert_called_once_with("command", "v")

    def test_paste_text_unavailable_without_pyautogui(self):
        clipboard_safe._PYAUTOGUI = False
        self.assertFalse(clipboard_safe.paste_text("herhangi bir şey"))


class ComputerControlTurkishTypingTests(unittest.TestCase):
    def setUp(self):
        self.fake_pyautogui = MagicMock()
        self.fake_pyperclip = MagicMock()
        self.fake_pyperclip.paste.return_value = "eski pano"
        computer_control.pyautogui = self.fake_pyautogui
        computer_control.pyperclip = self.fake_pyperclip
        computer_control._PYAUTOGUI = True
        computer_control._PYPERCLIP = True
        clipboard_safe.pyautogui = self.fake_pyautogui
        clipboard_safe.pyperclip = self.fake_pyperclip
        clipboard_safe._PYAUTOGUI = True
        clipboard_safe._PYPERCLIP = True

    def test_type_routes_turkish_text_through_clipboard_not_keystrokes(self):
        computer_control._type("İstanbul'a gidiyorum")

        self.fake_pyautogui.typewrite.assert_not_called()
        self.fake_pyautogui.hotkey.assert_called_once_with("ctrl", "v")
        self.assertEqual(self.fake_pyperclip.copy.call_args_list[0].args[0], "İstanbul'a gidiyorum")

    def test_type_keeps_fast_keystroke_path_for_plain_ascii(self):
        computer_control._type("Hello")

        self.fake_pyautogui.typewrite.assert_called_once_with("Hello", interval=0.03)
        self.fake_pyautogui.hotkey.assert_not_called()

    def test_smart_type_short_turkish_text_uses_clipboard(self):
        # 9 characters: short enough that the old len()>20 threshold alone
        # would have sent it through the broken keystroke path.
        computer_control._smart_type("güneşli", clear_first=False)

        self.fake_pyautogui.typewrite.assert_not_called()
        self.fake_pyautogui.hotkey.assert_called_once_with("ctrl", "v")

    def test_type_restores_clipboard_after_turkish_paste(self):
        computer_control._type("Çay içelim mi?")

        copy_calls = [c.args[0] for c in self.fake_pyperclip.copy.call_args_list]
        self.assertEqual(copy_calls[-1], "eski pano")


if __name__ == "__main__":
    unittest.main()
