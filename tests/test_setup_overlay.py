"""Regressions for the first-run setup overlay."""
import os
import json

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QLineEdit, QVBoxLayout, QWidget

import ui


def _app():
    return QApplication.instance() or QApplication([])


def test_setup_overlay_takes_keyboard_focus_and_accepts_key_text():
    app = _app()
    parent = QWidget()
    parent.resize(640, 480)
    layout = QVBoxLayout(parent)
    chat_input = QLineEdit()
    layout.addWidget(chat_input)
    # Match first boot: the setup overlay is built while MainWindow is hidden.
    overlay = ui.SetupOverlay(parent)
    overlay.setGeometry(50, 30, 460, 390)
    overlay.show()
    parent.show()
    QTest.qWait(20)

    assert app.focusWidget() is overlay._key_input
    assert overlay._key_input.echoMode() == QLineEdit.EchoMode.Password
    QTest.keyClicks(overlay._key_input, "AIzaTestKey")
    assert overlay._key_input.text() == "AIzaTestKey"
    QTest.mouseClick(overlay._key_visibility_btn, Qt.MouseButton.LeftButton)
    assert overlay._key_input.echoMode() == QLineEdit.EchoMode.Normal

    overlay.close()
    parent.close()


def test_first_run_setup_is_remembered_without_dropping_other_settings(
    tmp_path, monkeypatch
):
    config_file = tmp_path / "config" / "api_keys.json"
    config_file.parent.mkdir()
    config_file.write_text('{"llm_model": "qwen3:4b"}', encoding="utf-8")
    monkeypatch.setattr(ui, "API_FILE", config_file)

    assert not ui._setup_is_complete()
    ui._save_setup_config("AIzaExampleOnly", "windows")

    saved = json.loads(config_file.read_text(encoding="utf-8"))
    assert saved["llm_model"] == "qwen3:4b"
    assert saved["gemini_api_key"] == "AIzaExampleOnly"
    assert saved["os_system"] == "windows"
    assert ui._setup_is_complete()
