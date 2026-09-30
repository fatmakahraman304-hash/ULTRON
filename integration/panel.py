"""A dock inside MARK, including local access before a Gemini key exists."""
import json
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLineEdit, QPushButton, QTextEdit, QComboBox, QMessageBox
from .bridge import Bridge

class Worker(QThread):
    done = pyqtSignal(str)
    def __init__(self, text, mode, parent=None):
        super().__init__(parent)
        self.text, self.mode = text, mode
    def run(self):
        try:
            result = Bridge().ask(self.text, self.mode)
            self.done.emit(result.get('text') or json.dumps(result, ensure_ascii=False))
        except Exception as exc:
            self.done.emit(f'Yerel motor: {exc}')


def attach(ui):
    dock = QDockWidget('MARK · Yerel AI / Görevler', ui._win)
    panel = QWidget()
    layout = QVBoxLayout(panel)
    output = QTextEdit()
    output.setReadOnly(True)
    output.setPlainText('Gemini Live: MARK ses arayüzü. Yerel AI: aşağıdaki kutu. Agent görevlerinde mevcut güvenlik kuralları uygulanır.')
    mode = QComboBox()
    for label, value in [('Otomatik', 'auto'), ('Kod', 'coding'), ('Hızlı', 'fast'), ('Genel', 'general'), ('Agent görevi', 'agent')]:
        mode.addItem(label, value)
    entry = QLineEdit()
    entry.setPlaceholderText('Yerel AI isteği…')
    send = QPushButton('Gönder')
    status = QPushButton('Sağlık / Görev durumu')
    approval = QPushButton('Bekleyen onayı incele')
    for widget in (output, mode, entry, send, status, approval):
        layout.addWidget(widget)
    dock.setWidget(panel)
    ui._win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    dock.setMinimumWidth(300)
    workers = []
    def submit():
        text = entry.text().strip()
        if not text:
            return
        output.append('Siz: ' + text)
        entry.clear()
        send.setEnabled(False)
        worker = Worker(text, mode.currentData(), dock)
        workers.append(worker)
        worker.done.connect(output.append)
        worker.finished.connect(lambda: send.setEnabled(True))
        worker.start()
    def check():
        try:
            b = Bridge()
            output.append(json.dumps(b.health(), ensure_ascii=False, indent=2))
            output.append(json.dumps(b.request('/api/tasks'), ensure_ascii=False, indent=2))
        except Exception as exc:
            output.append(str(exc))
    def review():
        try:
            b = Bridge()
            pending = b.request('/api/task/pending')
            if not pending.get('id'):
                output.append('Bekleyen komut onayı yok. Uzun görevlerin durumu Görev durumu düğmesinde.')
                return
            details = pending.get('text', '') + '\n\nRiskler: ' + json.dumps(pending.get('risks', []), ensure_ascii=False)
            choice = QMessageBox.question(ui._win, 'İşlemi onaylıyor musunuz?', details,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            path = '/api/task/approve' if choice == QMessageBox.StandardButton.Yes else '/api/task/reject'
            output.append(json.dumps(b.request(path, {'id': pending['id']}), ensure_ascii=False))
        except Exception as exc:
            output.append(str(exc))
    send.clicked.connect(submit)
    entry.returnPressed.connect(submit)
    status.clicked.connect(check)
    approval.clicked.connect(review)
    ui._merged_dock = dock
    ui._merged_workers = workers
