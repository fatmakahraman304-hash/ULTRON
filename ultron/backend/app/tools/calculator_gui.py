"""Strict Windows Calculator UI Automation, never global keyboard/mouse input.

Only explicit arithmetic requests are supported. Every button is targeted by its
Windows accessibility AutomationId and invoked without moving focus or sending
system-wide keystrokes. A verified on-screen result is required for success.
"""
from __future__ import annotations

from decimal import Decimal
import os
import re
import subprocess
import sys
import time

from ultron.cloud_service.text_normalization import fold_turkish

_BUTTONS = {
    **{str(i): f"num{i}Button" for i in range(10)},
    "+": "plusButton",
    "-": "minusButton",
    "*": "multiplyButton",
    "/": "divideButton",
    "=": "equalButton",
    "C": "clearButton",
}
_TRUSTED_CALCULATOR_PROCESSES = {"calculatorapp.exe", "calculator.exe"}
_CONTAINER_PROCESS = "applicationframehost.exe"
_WINDOW_TITLES = {"calculator", "hesap makinesi"}
_EXPR = re.compile(r"(?<![0-9.,])(\d{1,9}(?:\s*[+*/×÷xX−-]\s*\d{1,9}){1,7})(?![0-9.,])")
_MAX_VALUE = Decimal(10) ** 12


class CalculatorUnavailable(RuntimeError):
    """Safe fixed-code error; never includes window titles or process details."""


def extract_calculator_expression(text: str) -> str | None:
    """Route only explicit Windows Calculator requests with one simple expression."""
    words = fold_turkish(text)
    if not re.search(r"\b(?:hesap\s+makinesi(?:ni|nde|ne|yle)?|calculator)\b", words):
        return None
    if not re.search(r"\b(?:hesapla|hesaplayip|islemi|islemini|sonucu|gir|yaz|tuslari)\b", words):
        return None
    matches = list(_EXPR.finditer(text))
    if len(matches) != 1:
        return None
    raw = matches[0].group(1)
    # Ignore no numbers elsewhere: a date/second expression would be ambiguous.
    if re.search(r"\d", text[:matches[0].start()] + text[matches[0].end():]):
        return None
    normalized = re.sub(r"\s+", "", raw).replace("×", "*").replace("x", "*").replace("X", "*").replace("÷", "/").replace("−", "-")
    try:
        parse_expression(normalized)
    except (ValueError, ZeroDivisionError):
        return None
    return normalized


def parse_expression(expr: str) -> tuple[str, int]:
    """Accept small integer arithmetic when Calculator Standard matches precedence."""
    if not isinstance(expr, str) or len(expr) > 56 or not re.fullmatch(
        r"\d{1,9}(?:[+\-*/]\d{1,9}){1,7}", expr
    ):
        raise ValueError("unsupported_expression")
    bits = re.findall(r"\d+|[+\-*/]", expr)
    numbers = [Decimal(bits[i]) for i in range(0, len(bits), 2)]
    ops = bits[1::2]
    if any(n > _MAX_VALUE for n in numbers):
        raise ValueError("out_of_range")

    def apply(a: Decimal, op: str, b: Decimal) -> Decimal:
        if op == "/" and b == 0:
            raise ValueError("division_by_zero")
        value = {"+": lambda: a + b, "-": lambda: a - b,
                 "*": lambda: a * b, "/": lambda: a / b}[op]()
        if not value.is_finite() or abs(value) > _MAX_VALUE:
            raise ValueError("out_of_range")
        if value != value.to_integral_value():
            raise ValueError("fractional_result_unsupported")
        return value

    # Standard Calculator computes sequentially. Reject expressions for which
    # that differs from mathematical operator precedence rather than misreport.
    sequential = numbers[0]
    for operator, number in zip(ops, numbers[1:]):
        sequential = apply(sequential, operator, number)
    collapsed = [numbers[0]]
    low_ops = []
    for operator, number in zip(ops, numbers[1:]):
        if operator in ("*", "/"):
            collapsed[-1] = apply(collapsed[-1], operator, number)
        else:
            low_ops.append(operator)
            collapsed.append(number)
    expected = collapsed[0]
    for operator, number in zip(low_ops, collapsed[1:]):
        expected = apply(expected, operator, number)
    if expected != sequential:
        raise ValueError("calculator_standard_precedence_mismatch")
    return expr, int(expected)


def _process_name(pid: int) -> str:
    import psutil
    try:
        return psutil.Process(int(pid)).name().casefold()
    except (psutil.Error, OSError, ValueError, TypeError):
        return ""


def _verified_calculator(window) -> bool:
    """Window must genuinely belong to Calculator, not just have a similar title."""
    try:
        if not window.is_visible():
            return False
        if window.window_text().strip().casefold() not in _WINDOW_TITLES:
            return False
        name = _process_name(window.element_info.process_id)
        if name in _TRUSTED_CALCULATOR_PROCESSES:
            return True
        if name != _CONTAINER_PROCESS:
            return False
        # UWP Calculator may live inside the trusted ApplicationFrameHost frame.
        for child in window.descendants()[:250]:
            if _process_name(child.element_info.process_id) in _TRUSTED_CALCULATOR_PROCESSES:
                return True
    except (AttributeError, LookupError, OSError):
        return False
    return False


def _calculator_control(window, automation_id: str, *, button: bool = False):
    """Resolve a descendant of a UIAWrapper by AutomationId.

    Desktop(backend='uia').windows() gives UIAWrapper objects, NOT a
    WindowSpecification. UIAWrapper has descendants() but no child_window().
    Only actual CalculatorApp/Calculator process-owned descendants qualify.
    """
    if not _verified_calculator(window):
        raise CalculatorUnavailable("calculator_identity_changed")
    try:
        matches = []
        for child in window.descendants():
            info = child.element_info
            if info.automation_id != automation_id:
                continue
            if button and str(info.control_type).casefold() != "button":
                continue
            if _process_name(info.process_id) not in _TRUSTED_CALCULATOR_PROCESSES:
                continue
            matches.append(child)
    except Exception as exc:
        raise CalculatorUnavailable("calculator_control_not_verified") from exc
    if len(matches) != 1:
        raise CalculatorUnavailable("calculator_control_not_verified")
    return matches[0]


def _locate_calculator_window():
    from pywinauto import Desktop
    matches = []
    for window in Desktop(backend="uia").windows():
        if not _verified_calculator(window):
            continue
        try:
            _calculator_control(window, "CalculatorResults")
            _calculator_control(window, "clearButton", button=True)
            _calculator_control(window, "equalButton", button=True)
        except CalculatorUnavailable:
            continue
        matches.append(window)
    # Do not choose arbitrarily among multiple or unverified windows.
    return matches[0] if len(matches) == 1 else None


def _invoke_button(window, automation_id: str) -> None:
    if automation_id not in _BUTTONS.values():
        raise CalculatorUnavailable("calculator_button_not_allowed")
    try:
        button = _calculator_control(window, automation_id, button=True)
        pattern = button.iface_invoke
        if pattern is None:
            raise CalculatorUnavailable("calculator_button_not_invokable")
        # UI Automation InvokePattern targets the specific control. Unlike
        # send_keys(), this cannot send a key to another focused application.
        pattern.Invoke()
    except CalculatorUnavailable:
        raise
    except Exception as exc:
        raise CalculatorUnavailable("calculator_button_unavailable") from exc


def _result_matches(actual: str, expected: int) -> bool:
    """Windows results localize thousands separators: 1,040 / 1.040."""
    if not isinstance(actual, str):
        return False
    end = re.search(r"([−-]?\d[\d.,\s]*)\s*$", actual)
    if not end:
        return False
    raw = end.group(1).strip().replace("−", "-")
    # Arithmetic currently accepts integer outcomes only.
    if not re.fullmatch(r"-?\d[\d.,\s]*", raw):
        return False
    digits = re.sub(r"[\s,.]", "", raw)
    try:
        return int(digits) == expected
    except ValueError:
        return False


def _read_result(window) -> str:
    try:
        return _calculator_control(window, "CalculatorResults").window_text()
    except CalculatorUnavailable:
        raise
    except Exception as exc:
        raise CalculatorUnavailable("calculator_result_unavailable") from exc


def run_calculator_expression(expr: str) -> dict:
    """Open Calculator if needed, invoke buttons, verify real UIA result."""
    expression, expected = parse_expression(expr)
    if sys.platform != "win32":
        return {"ok": False, "error_code": "windows_calculator_only"}
    # pywinauto COM interfaces must be initialized on this worker thread.
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except ImportError:
        return {"ok": False, "error_code": "calculator_automation_unavailable"}
    try:
        window = _locate_calculator_window()
        if window is None:
            try:
                subprocess.Popen(["calc.exe"], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
            except OSError:
                return {"ok": False, "error_code": "calculator_launch_failed"}
            for _ in range(28):
                time.sleep(0.2)
                window = _locate_calculator_window()
                if window is not None:
                    break
        if window is None:
            return {"ok": False, "error_code": "calculator_window_not_verified"}
        try:
            _invoke_button(window, "clearButton")
            for char in expression:
                _invoke_button(window, _BUTTONS[char])
            _invoke_button(window, "equalButton")
            for _ in range(12):
                actual = _read_result(window)
                if _result_matches(actual, expected):
                    return {
                        "ok": True, "expression": expression,
                        "result": str(expected), "verified": True,
                        "source": "windows-calculator-uia",
                    }
                time.sleep(0.15)
        except CalculatorUnavailable as exc:
            return {"ok": False, "error_code": str(exc)}
        return {"ok": False, "error_code": "calculator_result_not_verified"}
    except Exception:
        # Never send global keys as a fallback, never echo private UI labels.
        return {"ok": False, "error_code": "calculator_automation_unavailable"}
    finally:
        pythoncom.CoUninitialize()
