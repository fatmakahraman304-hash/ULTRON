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
        self.timer.start(600)
        ui._win._log_sig.connect(self.log)

    def emit(self, **data):
        self.message.emit(json.dumps(data, ensure_ascii=False))

    @pyqtSlot()
    def ready(self):
        self.state()

    def state(self):
        self.emit(kind='state', state=self.ui._win.hud.state, muted=self.ui.muted)

    @pyqtSlot(str)
    def log(self, text):
        # Only conversation output is mirrored. Technical logs stay in MARK's tools.
        if text.startswith('You:'):
            self.emit(kind='log', role='user', text=text.partition(':')[2].strip())
        elif text.startswith((self.ui.assistant_name+':', 'JARVIS:', 'ULTRON:')):
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
                webbrowser.open(base+'/merged/dashboard?hologram=1#'+token)
        elif name=='mute':
            win._toggle_mute()
            self.state()
        elif name=='interrupt':
            win._do_interrupt()
        elif name=='audio':
            win._open_audio_devices()
        elif name=='legacy':
            self.stack.setCurrentIndex(0)
            self.toolbar.show()
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
        allowed=not main or (url.scheme()=='http' and url.authority()==self.origin)
        print(f'[Cockpit] Navigation {url.path()}: {allowed}',flush=True)
        return allowed


def attach(ui):
    url=os.environ.get('MARK_ULTRON_URL')
    token=os.environ.get('MARK_ULTRON_TOKEN')
    if not url or not token:
        return False
    win=ui._win
    original=win.takeCentralWidget()
    stack=QStackedWidget(win)
    stack.addWidget(original)
    view=QWebEngineView(stack)
    profile=QWebEngineProfile('mark-cockpit',view)
    profile.setPersistentStoragePath(str(ROOT/'data/webview'))
    profile.setCachePath(str(ROOT/'cache/webview'))
    profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
    page=LocalPage(profile,view,QUrl(url).authority())
    view.setPage(page)
    stack.addWidget(view)
    win.setCentralWidget(stack)
    toolbar=QToolBar('ULTRON',win)
    toolbar.setStyleSheet('QToolBar {background:#101319;color:#f3f4f6;padding:7px;border:0;}')
    back=toolbar.addAction('← ULTRON arayüzüne dön')
    back.triggered.connect(lambda:(stack.setCurrentIndex(1),toolbar.hide()))
    win.addToolBar(toolbar)
    toolbar.hide()
    native=NativeBridge(ui,stack,toolbar)
    page.permissionRequested.connect(lambda permission: permission.deny())
    channel=QWebChannel(page)
    channel.registerObject('mark',native)
    page.setWebChannel(channel)
    def save_hologram_image(download):
        # Only the explicitly generated PNG is handled by this native download hook.
        if not download.url().toString().startswith('data:image/png'):
            download.cancel()
            return
        filename,_=QFileDialog.getSaveFileName(win,'Hologram görüntüsünü kaydet','ultron-hologram.png','PNG (*.png)')
        if not filename:
            download.cancel()
            return
        destination=Path(filename)
        download.setDownloadDirectory(str(destination.parent))
        download.setDownloadFileName(destination.name)
        download.accept()
    profile.downloadRequested.connect(save_hologram_image)
    stack.setCurrentIndex(1)
    win.setWindowTitle('ULTRON · MARK AI')
    win.resize(1440,900)
    # Runtime-created quizzes, video and reviews remain available in the original UI.
    def show_original(*_):
        stack.setCurrentIndex(0)
        toolbar.show()
    for name in ('_content_sig','_quiz_sig','_review_sig','_video_sig'):
        signal=getattr(win,name,None)
        if signal is not None:
            signal.connect(show_original)
    def load_done(ok):
        print(f'[Cockpit] Loaded {view.url().path()}: {ok}',flush=True)
        if ok and view.url().path().startswith('/frontend/'):
            stack.setCurrentIndex(1)
            toolbar.hide()
        elif not ok and view.url().path().startswith('/frontend/'):
            show_original()
            ui.write_log('ERR: ULTRON arayüzü yüklenemedi; MARK araçları açıldı.')
    view.loadFinished.connect(load_done)
    def loading(info):
        if info.errorCode() < 0 and info.errorCode() != -3:
            print(f'[Cockpit] Load error {info.errorCode()}: {info.errorString()}',flush=True)
    page.loadingChanged.connect(loading)
    page.renderProcessTerminated.connect(lambda reason,code:show_original())
    QTimer.singleShot(15000, lambda: show_original() if not view.url().path().startswith('/frontend/') else None)
    view.setUrl(QUrl(url+'/merged/dashboard#'+token))
    ui._web_cockpit=(view,page,profile,channel,native,stack,toolbar)
    return True
