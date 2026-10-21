"""Verified WhatsApp Desktop driver: confirm the right person before sending.

actions/send_message.py used to drive WhatsApp with a blind keystroke sequence
(Win key, type the app name, Ctrl+F, type the contact, Enter, Enter) and
report "sent" the moment the keystrokes were issued — without ever reading
back which window or conversation actually received them. On a slow machine,
or if the search list hadn't finished filtering, that sequence could land in
the wrong conversation while still claiming success.

This module replaces the blind sequence with one that is allowed to fail, but
never allowed to be wrong:

  1. Find the real WhatsApp Desktop window (not a Start-menu guess).
  2. Type the receiver into the real search box, then poll the real chat list
     until a row actually starts with that name — never press Enter/click on
     a guess before the filter has caught up.
  3. Before typing the message, re-check WhatsApp's own accessible label for
     the opened message box. WhatsApp sets it to "<Contact> sohbetine bir
     mesaj yazın" ("Write a message to <Contact>'s chat") — this is WhatsApp
     itself telling us which conversation is open, independent of anything we
     clicked, so it is the strongest check available and costs nothing extra.
  4. Paste the message, read the box back, and only press Enter if what the
     box holds matches what we meant to send.
  5. After Enter, poll until the box is actually empty before calling it
     sent. WhatsApp reports an "empty" box as the single character "\n", not
     "" — the Help text above was read directly from a live inspection of a
     real (self-chat only; no third party's messages were read) WhatsApp
     Desktop window, not guessed.

Any step that cannot be verified returns a failure with a reason, never a
guess dressed up as success. There is deliberately no LLM call anywhere in
this module — a cached per-language classification call was floated as an
idea elsewhere in this codebase, but adding a model call to a path that can
send a real message to a real person is a cost and a failure mode this
driver does not need to take on.
"""
from __future__ import annotations

import time
import unicodedata

try:
    from pywinauto import Application, findwindows
    import pyautogui
    import pyperclip
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

_WINDOW_CLASS = "WinUIDesktopWin32WindowClass"
_FILTER_TIMEOUT_SECONDS = 4.0
_SEND_TIMEOUT_SECONDS = 5.0
_POLL_INTERVAL_SECONDS = 0.2


def _fold(value: object) -> str:
    """Case/diacritic-insensitive compare for Turkish and English names alike."""
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(ch for ch in text if not unicodedata.combining(ch)).replace("ı", "i")


def _find_window():
    for hwnd in findwindows.find_windows(title_re=r"^WhatsApp$", visible_only=False):
        try:
            app = Application(backend="uia").connect(handle=hwnd)
            win = app.window(handle=hwnd)
            if win.element_info.class_name == _WINDOW_CLASS:
                return win
        except Exception:
            continue
    return None


def _first_visible(controls):
    for c in controls:
        try:
            if c.is_visible():
                return c
        except Exception:
            continue
    return None


def _search_box(win):
    # WhatsApp's own WebView2 content is exposed to UIA more than once (the
    # same control appears dozens of times at an identical rectangle). Every
    # duplicate reports the same screen coordinates, so click_input() always
    # lands on whatever is really rendered there regardless of which
    # duplicate node we hold — taking the first visible one is sufficient.
    candidates = [
        c for c in win.descendants(control_type="Edit")
        if _safe_rect_left(c) < 450
    ]
    return _first_visible(candidates)


def _safe_rect_left(control) -> int:
    try:
        return control.rectangle().left
    except Exception:
        return -1


def _compose_box(win):
    candidates = [
        c for c in win.descendants(control_type="Edit")
        if _safe_rect_left(c) >= 450
    ]
    return _first_visible(candidates)


def _chat_rows(win):
    rows = []
    for c in win.descendants(control_type="DataItem"):
        try:
            if c.is_visible() and c.window_text():
                rows.append(c)
        except Exception:
            continue
    return rows


def _box_text(edit_control) -> str:
    try:
        value = edit_control.get_value()
    except Exception:
        value = edit_control.window_text()
    return (value or "").strip()


class _WhatsAppTransport:
    def __init__(self, win):
        self._win = win

    def send_message_to(self, receiver: str, message: str) -> tuple[bool, str]:
        win = self._win
        try:
            win.restore()
            win.set_focus()
        except Exception as exc:
            return False, f"pencere odaklanamadı: {type(exc).__name__}"

        search = _search_box(win)
        if search is None:
            return False, "arama kutusu bulunamadı"

        try:
            search.click_input()
            time.sleep(0.15)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("delete")
            time.sleep(0.1)
            pyperclip.copy(receiver)
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "v")
        except Exception as exc:
            return False, f"kişi aranamadı: {type(exc).__name__}"

        folded_receiver = _fold(receiver)
        target_row = None
        deadline = time.monotonic() + _FILTER_TIMEOUT_SECONDS
        while time.monotonic() < deadline and target_row is None:
            time.sleep(_POLL_INTERVAL_SECONDS)
            for row in _chat_rows(win):
                if _fold(row.window_text()).startswith(folded_receiver):
                    target_row = row
                    break

        if target_row is None:
            return False, f"'{receiver}' için eşleşen bir sohbet bulunamadı; mesaj gönderilmedi"

        try:
            target_row.click_input()
            time.sleep(0.3)
        except Exception as exc:
            return False, f"sohbet açılamadı: {type(exc).__name__}"

        compose = _compose_box(win)
        if compose is None:
            return False, "mesaj kutusu bulunamadı; mesaj gönderilmedi"

        # WhatsApp labels this exact control "<Contact> sohbetine bir mesaj
        # yazın" — it is WhatsApp's own statement of which conversation this
        # box belongs to, not something we inferred from a click.
        try:
            label = _fold(compose.element_info.name)
        except Exception:
            label = ""
        if not label or folded_receiver not in label:
            return False, (
                f"açılan sohbet kutusu '{receiver}' ile eşleşmiyor "
                f"(etiket: {compose.element_info.name!r}); mesaj gönderilmedi"
            )

        previous_clipboard = None
        try:
            previous_clipboard = pyperclip.paste()
        except Exception:
            previous_clipboard = None
        try:
            compose.click_input()
            time.sleep(0.15)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("delete")
            time.sleep(0.1)
            pyperclip.copy(message)
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.2)
        except Exception as exc:
            return False, f"mesaj yazılamadı: {type(exc).__name__}"
        finally:
            # The message has already landed in the compose box by the time
            # we get here; restoring now never affects what was pasted, only
            # what the user finds on their own clipboard afterward.
            if previous_clipboard is not None:
                try:
                    pyperclip.copy(previous_clipboard)
                except Exception:
                    pass

        typed = _box_text(compose)
        if message.strip() not in typed:
            return False, "yazılan metin kutuya tam yansımadı; mesaj gönderilmedi"

        try:
            pyautogui.press("enter")
        except Exception as exc:
            return False, f"gönderme tuşu basılamadı: {type(exc).__name__}"

        deadline = time.monotonic() + _SEND_TIMEOUT_SECONDS
        emptied = False
        while time.monotonic() < deadline:
            time.sleep(_POLL_INTERVAL_SECONDS)
            if not _box_text(compose):
                emptied = True
                break

        if not emptied:
            return False, "mesaj kutusu gönderimden sonra boşalmadı; gönderim doğrulanamadı"
        return True, ""


def get() -> tuple[_WhatsAppTransport | None, str]:
    """Return (transport, reason). transport is None when unavailable."""
    if not _AVAILABLE:
        return None, "pywinauto/pyautogui/pyperclip kurulu değil"
    win = _find_window()
    if win is None:
        return None, "WhatsApp Desktop penceresi bulunamadı (uygulama açık olmalı)"
    return _WhatsAppTransport(win), ""
