"""A dock inside MARK, including local access before a Gemini key exists."""
import json
import os
import threading
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLineEdit, QPushButton, QTextEdit, QComboBox, QMessageBox
from .bridge import Bridge

class Worker(QObject):
    done = pyqtSignal(str)
    finished = pyqtSignal()
    def __init__(self, text, mode, parent=None):
        super().__init__(parent)
        self.text, self.mode = text, mode
    def start(self):
        threading.Thread(target=self.run,daemon=True).start()
    def run(self):
        try:
            result = Bridge().ask(self.text, self.mode)
            message = result.get('text') or json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            message = f'Yerel motor: {exc}'
        try:
            self.done.emit(message)
        except RuntimeError:
            return  # Qt widget was deleted during the bounded request.
        finally:
            try: self.finished.emit()
            except RuntimeError: return


def attach(ui):
    from .hologram_panel import attach as attach_hologram
    from .web_panel import attach as attach_dashboard
    attach_hologram(ui)
    attach_dashboard(ui)
