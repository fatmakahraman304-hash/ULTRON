"""Embed the reference-inspired cockpit without replacing MARK's runtime callbacks."""
import json
import os
import threading
from pathlib import Path
from PyQt6.QtCore import QObject, Qt, QCoreApplication, QTimer, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QStackedWidget, QToolBar, QFileDialog
from .paths import ROOT


def prepare():
    if QCoreApplication.instance() is None:
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)


class NativeBridge(QObject):
    message = pyqtSignal(str)

    def __init__(self, ui, stack, toolbar):
        super().__init__(stack)
        self.ui, self.stack, self.toolbar = ui, stack, toolbar
        self.timer=QTimer(self)
        self.timer.timeout.connect(self.state)
        self.timer.start(80)
        ui._win._log_sig.connect(self.log)

    def emit(self, **data):
        self.message.emit(json.dumps(data, ensure_ascii=False))

    @pyqtSlot()
    def ready(self):
        self.state()

    def state(self):
        self.emit(kind='state', state=self.ui._win.hud.state, muted=self.ui.muted,
                  amplitude=float(self.ui._win.hud._amp_disp))

    @pyqtSlot(str)
    def log(self, text):
        # Only conversation output is mirrored. Technical logs stay in MARK's tools.
        if text.startswith('You:'):
            self.emit(kind='log', role='user', text=text.partition(':')[2].strip())
        elif text.startswith((self.ui.assistant_name+':', 'ULTRON:', 'ULTRON:')):
            self.emit(kind='log', role='assistant', text=text.partition(':')[2].strip())
        elif text.startswith('ERR:'):
            self.emit(kind='error', text=text[4:].strip())

    @pyqtSlot(str)
    def send(self, text):
        if not text.strip() or len(text)>50000:
            return
        if self.ui.on_text_command:
            threading.Thread(target=self.ui.on_text_command,args=(text,),daemon=True).start()
        else:
            self.emit(kind='error',text='Gemini Live henüz hazır değil. Yerel model seçebilirsiniz.')

    @pyqtSlot(str)
    def action(self, name):
        win=self.ui._win
        if name=='hologrambrowser':
            import webbrowser
            self.ui.stop_camera_stream()
            base=os.environ.get('MARK_ULTRON_URL','')
            token=os.environ.get('MARK_ULTRON_TOKEN','')
            if base and token:
                webbrowser.open(base+'/merged/hologram#'+token)
        elif name=='mute':
            win._toggle_mute()
            self.state()
        elif name=='interrupt':
            win._do_interrupt()
        elif name=='audio':
            win._open_audio_devices()
        elif name=='camera':
            win.start_camera_stream()
        elif name=='settings':
            win._show_setup()
        elif name=='file':
            filename,_=QFileDialog.getOpenFileName(win,'Dosya ekle')
            if filename:
                win._drop_zone._set_file(filename)
                file=Path(filename)
                self.emit(kind='file',name=file.name,size=file.stat().st_size)


class LocalPage(QWebEnginePage):
    def __init__(self, profile, parent, origin):
        super().__init__(profile,parent)
        self.origin=origin

    def javaScriptConsoleMessage(self, level, message, line, source):
        print(f"[Cockpit JS] {message[:300]}", flush=True)

    def acceptNavigationRequest(self,url,kind,main):
        # The native command bridge is exposed only to our authenticated local UI.
        allowed=not main or (url.scheme()=='http' and url.authority()==self.origin) or (not self.origin and url.isLocalFile() and Path(url.toLocalFile()).resolve().is_relative_to((ROOT/'ultron/frontend/dist').resolve()))
        print(f'[Cockpit] Navigation {url.path()}: {allowed}',flush=True)
        return allowed


def attach(ui):
    """One dashboard; hidden native widgets continue to service runtime callbacks."""
    url=os.environ.get('MARK_ULTRON_URL','')
    token=os.environ.get('MARK_ULTRON_TOKEN','')
    win=ui._win
    original=win.takeCentralWidget()
    original.setParent(win)
    original.hide()
    view=QWebEngineView(win)
    profile=QWebEngineProfile(view)
    page=LocalPage(profile,view,QUrl(url).authority())
    view.setPage(page)
    win.setCentralWidget(view)
    native=NativeBridge(ui,view,None)
    channel=QWebChannel(page)
    channel.registerObject('mark',native)
    page.setWebChannel(channel)
    page.permissionRequested.connect(lambda permission:permission.deny())
    # Retain specialist widgets (reviews, quizzes, approvals and camera), not a second dashboard.
    for name in ('_quick_drawer','_ctrl_drawer','_confirm_banner','_clipboard_panel','_cam_preview'):
        widget=getattr(win,name,None)
        if widget is not None:
            widget.setParent(view)
            widget.hide()
    from PyQt6.QtWidgets import QDialog,QVBoxLayout
    dialogs=[]
    camera_dialog=QDialog(win);camera_dialog.setWindowTitle('ULTRON · Kamera');camera_dialog.resize(800,500)
    camera_layout=QVBoxLayout(camera_dialog);camera_layout.addWidget(win._cam_live_lbl)
    win._cam_stream_sig.connect(lambda active:camera_dialog.show() if active else camera_dialog.hide())
    camera_dialog.finished.connect(lambda _:win.stop_camera_stream())
    dialogs.append(camera_dialog)
    # Move existing functional panels into tool dialogs so their callbacks and rich content survive.
    for name, signals, title in (
        ('_content_panel', ('_content_sig','_review_sig'), 'ULTRON · Sonuç'),
        ('_quiz_panel', ('_quiz_sig',), 'ULTRON · Çalışma')):
        widget=getattr(win,name,None)
        if widget is None:continue
        dialog=QDialog(win);dialog.setWindowTitle(title);dialog.resize(760,520)
        layout=QVBoxLayout(dialog);layout.addWidget(widget)
        for signal in signals:getattr(win,signal).connect(lambda *args,d=dialog:d.show())
        dialogs.append(dialog)
    if hasattr(ui,'_hologram_toolbar'):ui._hologram_toolbar.hide()
    win.addAction(ui._hologram_action)
    win.setWindowTitle('ULTRON')
    win.resize(1440,900)
    def save_download(download):
        address=download.url().toString()
        png=address.startswith('data:image/png')
        project=address.startswith('blob:'+url.rstrip('/')+'/') and download.suggestedFileName().endswith('.ultron.json') and download.mimeType()=='application/json'
        if not (png or project):download.cancel();return
        filename,_=QFileDialog.getSaveFileName(win,'Hologram kaydet','ultron.png' if png else 'ultron.ultron.json','PNG (*.png)' if png else 'ULTRON (*.ultron.json)')
        if not filename:download.cancel();return
        path=Path(filename);download.setDownloadDirectory(str(path.parent));download.setDownloadFileName(path.name);download.accept()
    profile.downloadRequested.connect(save_download)
    if url and token:view.setUrl(QUrl(url+'/merged/dashboard#'+token))
    else:view.setUrl(QUrl.fromLocalFile(str(ROOT/'ultron/frontend/dist/index.html')))
    ui._dashboard=(view,page,profile,channel,native,original,dialogs)
    return True
