"""Clipboard-backed text entry that leaves the user's clipboard as it found it.

pyautogui types by sending one keystroke per character through a fixed
KEYBOARD_KEYS table. That table has no entry for a single Turkish-specific
letter — confirmed directly against the installed pyautogui: 'ğ ü ş ı ö ç İ
Ğ Ü Ş Ö Ç' are all absent. pyautogui.typewrite()/.write() cannot type any of
them; it either raises or silently drops the character. Clipboard paste has
no such limit, but every clipboard-paste call site in this project used to
overwrite the user's clipboard permanently to do it. This module does both:
paste reliably, then put back whatever was there before.
"""
from __future__ import annotations

import time

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False


def needs_clipboard(text: str) -> bool:
    """True when pyautogui's keystroke typing cannot represent this text."""
    return not text.isascii()


def available() -> bool:
    return _PYAUTOGUI and _PYPERCLIP


def paste_text(text: str, *, mac: bool = False) -> bool:
    """Copy text, paste it, then restore whatever was on the clipboard before.

    Returns True once the clipboard path was used. Returns False (no paste
    attempted) only when pyautogui/pyperclip are unavailable — callers should
    fall back to keystroke typing in that case.
    """
    if not available():
        return False
    previous = None
    try:
        previous = pyperclip.paste()
    except Exception:
        previous = None
    pyperclip.copy(text)
    time.sleep(0.1)
    pyautogui.hotkey("command" if mac else "ctrl", "v")
    time.sleep(0.2)
    if previous is not None:
        try:
            pyperclip.copy(previous)
        except Exception:
            pass
    return True
