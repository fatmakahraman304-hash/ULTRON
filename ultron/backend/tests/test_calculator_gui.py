"""Regression coverage: no unverified Windows Calculator keyboard/mouse input."""
import sys
from types import SimpleNamespace

import pytest
from app.tools import calculator_gui as calc


@pytest.mark.parametrize("message,expected", [
    ("Hesap makinesini aç ve 125 × 8 + 40 işlemini hesapla. Sonucu söyle.", "125*8+40"),
    ("Hesap makinesinde 12+3 işlemini hesapla", "12+3"),
    ("Calculator 125 x 8 + 40 işlemini hesapla", "125*8+40"),
])
def test_explicit_calculator_request_only(message, expected):
    assert calc.extract_calculator_expression(message) == expected


@pytest.mark.parametrize("message", [
    "Hesap makinesini aç.",
    "125 × 8 + 40 kaç eder?",
    "Windows Hesap Makinesinin tarihi nedir?",
    "Hesap makinesinde 125 × 8 + 40 nedir?",
    "Hesap makinesini aç ve 125 × 8 + 40 ve 8+1 işlemlerini hesapla",
    "Hesap makinesini aç ve 125.5 × 8 + 40 işlemini hesapla",
    "Hesap makinesini aç ve 2+3*4 işlemini hesapla",
    "Hesap makinesini aç ve 3/0 işlemini hesapla",
    "Hesap makinesini aç ve 999999999*999999999 işlemini hesapla",
])
def test_ambiguous_unsafe_or_non_action_is_not_triggered(message):
    assert calc.extract_calculator_expression(message) is None


@pytest.mark.parametrize("expression,answer", [
    ("125*8+40", 1040),
    ("100-25+5", 80),
    ("12/3+4", 8),
    ("9*7", 63),
    ("10-15", -5),
])
def test_strict_arithmetic_matches_calculator_standard(expression, answer):
    assert calc.parse_expression(expression) == (expression, answer)


@pytest.mark.parametrize("display,number,correct", [
    ("Display is 1,040", 1040, True),
    ("Ekrandaki değer 1.040", 1040, True),
    ("Display is 1039", 1040, False),
    ("Display is -5", -5, True),
    ("Windows Calculator", 1040, False),
    ("Display is 1040 secret", 1040, False),
])
def test_accessibility_result_readback(display, number, correct):
    assert calc._result_matches(display, number) is correct


@pytest.fixture(autouse=True)
def pretend_calculator_process_names(monkeypatch):
    """UIA child controls on the user's PC belong to CalculatorApp.exe."""
    names = {91: "applicationframehost.exe", 92: "calculatorapp.exe",
             93: "notepad.exe"}
    monkeypatch.setattr(calc, "_process_name", lambda pid: names.get(pid, ""))


class FakeButton:
    def __init__(self, window, button_id, *, pid=92):
        self.window = window
        self.button_id = button_id
        self.element_info = SimpleNamespace(
            automation_id=button_id, process_id=pid,
            control_type="Text" if button_id == "CalculatorResults" else "Button"
        )
        self.iface_invoke = self
    def Invoke(self):
        self.window.pressed.append(self.button_id)
        if self.button_id == "equalButton":
            self.window.display = "Ekran sonucu: 1.040"
    def window_text(self):
        return self.window.display


class FakeWindow:
    """Real Desktop().windows() returns a wrapper with NO child_window method."""
    def __init__(self, trusted=True):
        self.trusted = trusted
        self.pressed = []
        self.display = "Display is 0"
        self.element_info = SimpleNamespace(process_id=91)
        self._children = [FakeButton(self, "CalculatorResults")]
        self._children += [FakeButton(self, key) for key in calc._BUTTONS.values()]
    def descendants(self):
        return list(self._children)
    def is_visible(self):
        return True
    def window_text(self):
        return "Hesap Makinesi"


def test_real_desktop_windows_wrapper_is_located_without_child_window(monkeypatch):
    window = FakeWindow()
    assert not hasattr(window, "child_window")
    monkeypatch.setitem(sys.modules, "pywinauto", SimpleNamespace(
        Desktop=lambda backend: SimpleNamespace(windows=lambda: [window])
    ))
    assert calc._locate_calculator_window() is window
    assert calc._verified_calculator(window) is True


def test_foreign_process_button_is_never_invoked(monkeypatch):
    window = FakeWindow()
    for child in window._children:
        if child.button_id == "num1Button":
            child.element_info.process_id = 93
    assert calc._verified_calculator(window) is True
    with pytest.raises(calc.CalculatorUnavailable, match="calculator_control_not_verified"):
        calc._invoke_button(window, "num1Button")
    assert window.pressed == []


def test_duplicate_calculator_buttons_are_not_accepted():
    window = FakeWindow()
    window._children.append(FakeButton(window, "num1Button"))
    with pytest.raises(calc.CalculatorUnavailable, match="calculator_control_not_verified"):
        calc._invoke_button(window, "num1Button")
    assert window.pressed == []


def test_unknown_automation_id_cannot_be_invoked():
    window = FakeWindow()
    with pytest.raises(calc.CalculatorUnavailable, match="calculator_button_not_allowed"):
        calc._invoke_button(window, "unsafeButton")
    assert window.pressed == []


def test_real_ui_buttons_invoke_only_a_verified_calculator_and_read_screen(monkeypatch):
    window = FakeWindow()
    com_calls = []
    monkeypatch.setattr(calc, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setitem(sys.modules, "pythoncom", SimpleNamespace(
        CoInitialize=lambda: com_calls.append("init"),
        CoUninitialize=lambda: com_calls.append("close"),
    ))
    monkeypatch.setattr(calc, "_locate_calculator_window", lambda: window)
    monkeypatch.setattr(calc, "_verified_calculator", lambda candidate: candidate.trusted)
    monkeypatch.setattr(calc.time, "sleep", lambda *_: None)
    result = calc.run_calculator_expression("125*8+40")
    assert result == {
        "ok": True, "expression": "125*8+40",
        "result": "1040", "verified": True, "source": "windows-calculator-uia",
    }
    assert window.pressed == [
        "clearButton", "num1Button", "num2Button", "num5Button",
        "multiplyButton", "num8Button", "plusButton",
        "num4Button", "num0Button", "equalButton",
    ]
    assert com_calls == ["init", "close"]


def test_window_switch_stops_without_sending_any_button(monkeypatch):
    window = FakeWindow(trusted=False)
    monkeypatch.setattr(calc, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setitem(sys.modules, "pythoncom", SimpleNamespace(
        CoInitialize=lambda: None, CoUninitialize=lambda: None))
    monkeypatch.setattr(calc, "_locate_calculator_window", lambda: window)
    result = calc.run_calculator_expression("125*8+40")
    assert result == {"ok": False, "error_code": "calculator_identity_changed"}
    assert window.pressed == []


def test_calc_display_mismatch_is_never_reported_as_verified(monkeypatch):
    window = FakeWindow()
    def wrong_result():
        return "Display is 999"
    monkeypatch.setattr(calc, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setitem(sys.modules, "pythoncom", SimpleNamespace(
        CoInitialize=lambda: None, CoUninitialize=lambda: None))
    monkeypatch.setattr(calc, "_locate_calculator_window", lambda: window)
    monkeypatch.setattr(calc, "_verified_calculator", lambda _: True)
    monkeypatch.setattr(calc, "_read_result", lambda _: wrong_result())
    monkeypatch.setattr(calc.time, "sleep", lambda *_: None)
    result = calc.run_calculator_expression("125*8+40")
    assert result == {"ok": False, "error_code": "calculator_result_not_verified"}


def test_fake_window_title_cannot_impersonate_calculator(monkeypatch):
    window = SimpleNamespace(
        is_visible=lambda: True,
        window_text=lambda: "Calculator",
        element_info=SimpleNamespace(process_id=8),
        descendants=lambda: [],
    )
    monkeypatch.setattr(calc, "_process_name", lambda pid: "notepad.exe")
    assert calc._verified_calculator(window) is False


def test_desktop_api_keeps_calculator_action_local_even_with_cloud_enabled(monkeypatch):
    import asyncio
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer
    import merged_api

    monkeypatch.setenv("MARK_ULTRON_TOKEN", "")
    invoked = []
    created_cloud = []

    def fake_calculator(expr):
        invoked.append(expr)
        return {"ok": True, "verified": True, "result": "1040"}

    monkeypatch.setattr(calc, "run_calculator_expression", fake_calculator)

    class FakeCloud:
        enabled = True
        def __init__(self):
            self.calls = []
            created_cloud.append(self)
        async def chat(self, prompt, **kwargs):
            self.calls.append(prompt)
            return {"reply": "Cloud doesn't control the Windows Calculator"}

    monkeypatch.setattr(merged_api, "CloudClient", FakeCloud)

    async def run():
        hub = SimpleNamespace(bridge=SimpleNamespace(runtime=object(), available=True),
                              agent=SimpleNamespace(state="IDLE"),
                              memory=SimpleNamespace(add_session=lambda *_: None))
        async def no_op(*_):
            pass
        hub.broadcast = no_op
        hub.on_activity = no_op
        app = web.Application()
        merged_api.install(app, hub)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.post("/api/merged/invoke", json={
                "text": "Hesap makinesini aç ve 125 × 8 + 40 işlemini hesapla.",
                "mode": "general",
            })
            body = await response.json()
            assert response.status == 200
            assert body["ok"] and body["verified"]
            assert body["source"] == "desktop-calculator-ui"
            assert "1040" in body["text"]
            assert invoked == ["125*8+40"]
            assert created_cloud[0].calls == []

            response = await client.post("/api/merged/invoke", json={
                "text": "Hesap makinesini aç.",
                "mode": "general",
            })
            body = await response.json()
            assert body["source"] == "cloud"
            assert created_cloud[0].calls == ["Hesap makinesini aç."]
            assert invoked == ["125*8+40"]

            monkeypatch.setattr(calc, "run_calculator_expression",
                                lambda _: {"ok": False, "error_code": "calculator_result_not_verified"})
            response = await client.post("/api/merged/invoke", json={
                "text": "Hesap makinesini aç ve 125 × 8 + 40 işlemini hesapla.",
                "mode": "general",
            })
            body = await response.json()
            assert not body["ok"]
            assert not body["verified"]
            assert body["error_code"] == "calculator_result_not_verified"
            assert created_cloud[0].calls == ["Hesap makinesini aç."]
        finally:
            await client.close()

    asyncio.run(run())
