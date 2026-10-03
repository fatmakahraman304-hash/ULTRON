"""Hologram tool window owned by the original MARK desktop."""
import os
from pathlib import Path
from PyQt6.QtCore import QUrl, pyqtSlot, Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QToolBar, QFileDialog
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView
from .web_panel import NativeBridge, LocalPage


class HologramBridge(NativeBridge):
    @pyqtSlot(str)
    def hologramAction(self, name):
        if name == 'close':
            self.parent().close()
        elif name == 'hologrambrowser':
            import webbrowser
            self.ui.stop_camera_stream()
            webbrowser.open(os.environ['MARK_ULTRON_URL']+'/merged/hologram#'+os.environ['MARK_ULTRON_TOKEN'])


def attach(ui):
    toolbar = QToolBar('Hologram araçları', ui._win)
    toolbar.setMovable(False)
    toolbar.setStyleSheet('QToolBar {background:#080a0e;color:#ff3047;border:0;padding:3px;} QToolButton {color:#ff3047;padding:7px;}')
    action = toolbar.addAction('◈ Hologram çalışma alanı')
    action.setShortcut(QKeySequence('Ctrl+H'))
    ui._win.addToolBar(toolbar)
    ui._hologram_window = None

    def open_hologram():
        if ui._hologram_window is not None:
            ui._hologram_window.showNormal()
            ui._hologram_window.raise_()
            ui._hologram_window.activateWindow()
            return
        base, token = os.environ.get('MARK_ULTRON_URL'), os.environ.get('MARK_ULTRON_TOKEN')
        if not base or not token:
            ui.write_log('ERR: Hologram için yerel ULTRON servisi açık olmalı.')
            return
        dialog = QDialog(ui._win)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setWindowTitle('ULTRON · Hologram çalışma alanı')
        dialog.resize(1350, 850)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0,0,0,0)
        view = QWebEngineView(dialog)
        profile = QWebEngineProfile(view)
        page = LocalPage(profile, view, QUrl(base).authority())
        view.setPage(page)
        page.permissionRequested.connect(lambda permission: permission.deny())
        bridge = HologramBridge(ui, dialog, toolbar)
        channel = QWebChannel(page)
        channel.registerObject('mark', bridge)
        page.setWebChannel(channel)
        layout.addWidget(view)
        def save(download):
            address = download.url().toString()
            png = address.startswith('data:image/png')
            project = address.startswith('blob:'+base.rstrip('/')+'/') and download.mimeType()=='application/json' and download.suggestedFileName().endswith('.ultron.json')
            if not (png or project):
                download.cancel()
                return
            filename,_ = QFileDialog.getSaveFileName(dialog,'Hologramı kaydet','ultron-hologram.png' if png else 'ultron-proje.ultron.json','PNG (*.png)' if png else 'ULTRON proje (*.ultron.json)')
            if not filename:
                download.cancel()
                return
            destination = Path(filename)
            download.setDownloadDirectory(str(destination.parent))
            download.setDownloadFileName(destination.name)
            download.accept()
        profile.downloadRequested.connect(save)
        def failed(ok):
            if not ok:
                ui.write_log('ERR: Hologram yüklenemedi. INSTALL.bat ile hologram bileşenlerini kurun.')
        view.loadFinished.connect(failed)
        dialog._resources = (view,page,profile,channel,bridge)
        dialog.destroyed.connect(lambda: setattr(ui,'_hologram_window',None))
        ui._hologram_window = dialog
        ui._hologram_page = page
        view.setUrl(QUrl(base+'/merged/hologram#'+token))
        dialog.show()
    action.triggered.connect(open_hologram)
    ui._open_hologram = open_hologram
    ui._hologram_action = action
    ui._hologram_toolbar = toolbar
