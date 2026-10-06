"""Embed the reference-inspired cockpit without replacing MARK's runtime callbacks."""
import json
import os
import threading
import urllib.request
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
    remote_command = pyqtSignal(str)

    def __init__(self, ui, stack, toolbar):
        super().__init__(stack)
        self.ui, self.stack, self.toolbar = ui, stack, toolbar
        self.timer=QTimer(self)
        self.timer.timeout.connect(self.state)
        self.timer.start(80)
        self._cloud_busy=False
        self._command_busy=False
        self._presence_busy=False
        self._remote_task_ids=[]
        self.cloud_timer=QTimer(self)
        self.cloud_timer.timeout.connect(self.cloud_messages)
        self.cloud_timer.start(3000)
        self.command_timer=QTimer(self)
        self.command_timer.timeout.connect(self.cloud_commands)
        self.command_timer.start(2200)
        self.presence_timer=QTimer(self)
        self.presence_timer.timeout.connect(self.cloud_presence)
        self.presence_timer.start(5000)
        self.remote_command.connect(self._apply_remote_command)
        ui._win._log_sig.connect(self.log)

    def emit(self, **data):
        self.message.emit(json.dumps(data, ensure_ascii=False))

    @pyqtSlot()
    def ready(self):
        self.state()
        self.plugins()
        self.cloud_messages()
        self.cloud_presence()

    def plugins(self):
        getter=getattr(self.ui,'get_plugins',None)
        if callable(getter):
            try:
                self.emit(kind='plugins', data=getter())
            except Exception:
                self.emit(kind='plugins', data=None)

    def state(self):
        self.emit(kind='state', state=self.ui._win.hud.state, muted=self.ui.muted,
                  amplitude=float(self.ui._win.hud._amp_disp))

    def cloud_messages(self):
        """Poll shared Cloud chat without exposing the device token to React."""
        if self._cloud_busy:
            return
        base=os.environ.get('ULTRON_CLOUD_URL','').strip().rstrip('/')
        token=os.environ.get('ULTRON_DEVICE_TOKEN','').strip()
        if not base or not token:
            return
        self._cloud_busy=True

        def worker():
            try:
                request=urllib.request.Request(
                    base+'/api/messages?limit=200',
                    headers={
                        'Authorization':f'Bearer {token}',
                        'X-ULTRON-DEVICE':'desktop-ultron-ui',
                        'Accept':'application/json',
                    },
                    method='GET',
                )
                with urllib.request.urlopen(request,timeout=12) as response:
                    payload=json.loads(response.read().decode('utf-8'))
                rows=payload.get('messages',[])
                if isinstance(rows,list):
                    self.emit(kind='cloud_messages',data=rows)
            except Exception:
                # Cloud history is additive; an outage must never affect the native app.
                pass
            finally:
                self._cloud_busy=False

        threading.Thread(target=worker,daemon=True).start()

    def _cloud_control_request(self, path, body, timeout=10):
        base=os.environ.get('ULTRON_CLOUD_URL','').strip().rstrip('/')
        token=os.environ.get('ULTRON_DEVICE_TOKEN','').strip()
        if not base or not token:
            raise RuntimeError('Cloud not configured')
        data=json.dumps(body,ensure_ascii=False).encode('utf-8')
        request=urllib.request.Request(
            base+path,
            data=data,
            headers={
                'Authorization':f'Bearer {token}',
                'X-ULTRON-DEVICE':'desktop-ultron-control',
                'Accept':'application/json',
                'Content-Type':'application/json; charset=utf-8',
            },
            method='POST',
        )
        with urllib.request.urlopen(request,timeout=timeout) as response:
            raw=response.read().decode('utf-8')
        return json.loads(raw) if raw else {}

    def cloud_presence(self):
        """Publish desktop liveness/state so the phone can show online/offline."""
        if self._presence_busy:
            return
        self._presence_busy=True
        try:
            state={
                'ui_state':str(self.ui._win.hud.state),
                'muted':bool(self.ui.muted),
                'assistant':str(getattr(self.ui,'assistant_name','ULTRON')),
            }
        except Exception:
            state={'ui_state':'UNKNOWN'}

        def worker():
            try:
                self._cloud_control_request('/api/device-presence/heartbeat',{'state':state},timeout=8)
            except Exception:
                pass
            finally:
                self._presence_busy=False
        threading.Thread(target=worker,daemon=True).start()

    def _complete_remote_command(self, command_id, ok=True, message=''):
        if not command_id:
            return
        def worker():
            try:
                self._cloud_control_request(
                    f'/api/device-commands/{int(command_id)}/complete',
                    {'status':'completed' if ok else 'failed','result':{'message':str(message)[:2000]}},
                    timeout=8,
                )
            except Exception:
                pass
        threading.Thread(target=worker,daemon=True).start()

    def cloud_commands(self):
        """Claim safe phone->desktop control commands from ULTRON Cloud."""
        if self._command_busy:
            return
        base=os.environ.get('ULTRON_CLOUD_URL','').strip().rstrip('/')
        token=os.environ.get('ULTRON_DEVICE_TOKEN','').strip()
        if not base or not token:
            return
        self._command_busy=True

        def worker():
            try:
                body=json.dumps({'target':'desktop'}).encode('utf-8')
                request=urllib.request.Request(
                    base+'/api/device-commands/claim',
                    data=body,
                    headers={
                        'Authorization':f'Bearer {token}',
                        'X-ULTRON-DEVICE':'desktop-ultron-control',
                        'Accept':'application/json',
                        'Content-Type':'application/json; charset=utf-8',
                    },
                    method='POST',
                )
                with urllib.request.urlopen(request,timeout=10) as response:
                    payload=json.loads(response.read().decode('utf-8'))
                for item in payload.get('commands',[]):
                    command=str(item.get('command','')).strip().lower()
                    if command in {'wake','mute','unmute','interrupt','sync_memory','agent_task'}:
                        self.remote_command.emit(json.dumps(item,ensure_ascii=False))
            except Exception:
                pass
            finally:
                self._command_busy=False

        threading.Thread(target=worker,daemon=True).start()

    @pyqtSlot(str)
    def _apply_remote_command(self, raw):
        """Execute Cloud commands from the paired phone on the desktop ULTRON."""
        win=self.ui._win
        try:
            try:
                item=json.loads(raw)
                command=str(item.get('command','')).strip().lower()
                command_id=item.get('id')
                payload=item.get('payload', {})
                if isinstance(payload, str):
                    try:
                        payload=json.loads(payload)
                    except Exception:
                        payload={}
                if not isinstance(payload, dict):
                    payload={}
            except Exception:
                command=str(raw).strip().lower()
                payload={}
            if command=='wake':
                getter=getattr(self.ui,'wake_get_state',None)
                manual=getattr(self.ui,'on_wake_manual',None)
                state=getter() if callable(getter) else {}
                if state.get('enabled') and not state.get('awake') and callable(manual):
                    manual()
                self.emit(kind='remote_notice',text='Telefon: ULTRON uyandırma komutu alındı.')
                self._complete_remote_command(command_id,True,'ULTRON uyandırıldı.')
            elif command=='mute':
                if not self.ui.muted:
                    win._toggle_mute()
                self.emit(kind='remote_notice',text='Telefon: laptop mikrofonu kapatıldı.')
                self._complete_remote_command(command_id,True,'Laptop mikrofonu kapatıldı.')
            elif command=='unmute':
                if self.ui.muted:
                    win._toggle_mute()
                self.emit(kind='remote_notice',text='Telefon: laptop mikrofonu açıldı.')
                self._complete_remote_command(command_id,True,'Laptop mikrofonu açıldı.')
            elif command=='interrupt':
                win._do_interrupt()
                self.emit(kind='remote_notice',text='Telefon: konuşma durduruldu.')
                self._complete_remote_command(command_id,True,'Konuşma durduruldu.')
            elif command=='sync_memory':
                def sync_worker():
                    try:
                        from integration.cloud_memory_sync import sync
                        ok,message=sync()
                        self.emit(kind='remote_notice',text=message if ok else 'Cloud hafıza eşitlemesi atlandı.')
                        self._complete_remote_command(command_id,ok,message)
                    except Exception as exc:
                        self.emit(kind='remote_notice',text='Cloud hafıza eşitlemesi başarısız.')
                        self._complete_remote_command(command_id,False,str(exc))
                threading.Thread(target=sync_worker,daemon=True).start()
            elif command=='agent_task':
                text=str(payload.get('text','')).strip()
                if not text:
                    self.emit(kind='remote_notice',text='Telefondan boş görev geldi; çalıştırılmadı.')
                    self._complete_remote_command(command_id,False,'Görev metni boş.')
                    return
                if len(text)>50000:
                    text=text[:50000]
                # A remote agent task is treated exactly like a command typed
                # into the local ULTRON interface. Wake the assistant first when
                # wake-word mode is enabled, then hand the task to Gemini Live,
                # which can use the desktop's existing apps/files/browser/tools.
                getter=getattr(self.ui,'wake_get_state',None)
                manual=getattr(self.ui,'on_wake_manual',None)
                state=getter() if callable(getter) else {}
                if state.get('enabled') and not state.get('awake') and callable(manual):
                    manual()
                self.ui.write_log('You: '+text)
                handler=getattr(self.ui,'on_text_command',None)
                if callable(handler):
                    if command_id:
                        self._remote_task_ids.append(int(command_id))
                    handler(text)
                    self.emit(kind='remote_notice',text='Telefon görevi ULTRON agente gönderildi.')
                else:
                    self.emit(kind='remote_notice',text='ULTRON agent henüz hazır değil.')
                    self._complete_remote_command(command_id,False,'ULTRON agent henüz hazır değil.')
        except Exception as exc:
            self.emit(kind='remote_notice',text='Uzaktan komut uygulanamadı: '+str(exc)[:100])
            try:
                self._complete_remote_command(locals().get('command_id'),False,str(exc))
            except Exception:
                pass

    def phone_command(self, command):
        """Send a safe desktop->phone UI command through Cloud."""
        if command not in {'ping','refresh','open_memory','focus_chat','open_remote','vibrate','scroll_top'}:
            return
        base=os.environ.get('ULTRON_CLOUD_URL','').strip().rstrip('/')
        token=os.environ.get('ULTRON_DEVICE_TOKEN','').strip()
        if not base or not token:
            self.emit(kind='remote_notice',text='Cloud bağlantısı yapılandırılmamış.')
            return

        def worker():
            try:
                body=json.dumps({'target':'phone','command':command}).encode('utf-8')
                request=urllib.request.Request(
                    base+'/api/device-commands',
                    data=body,
                    headers={
                        'Authorization':f'Bearer {token}',
                        'X-ULTRON-DEVICE':'desktop-ultron-control',
                        'Accept':'application/json',
                        'Content-Type':'application/json; charset=utf-8',
                    },
                    method='POST',
                )
                with urllib.request.urlopen(request,timeout=10) as response:
                    response.read()
                self.emit(kind='remote_notice',text='Telefon komutu Cloud üzerinden gönderildi.')
            except Exception:
                self.emit(kind='remote_notice',text='Telefon komutu gönderilemedi.')

        threading.Thread(target=worker,daemon=True).start()

    @pyqtSlot(str)
    def log(self, text):
        # Only conversation output is mirrored. Technical logs stay in MARK's tools.
        if text.startswith('You:'):
            self.emit(kind='log', role='user', text=text.partition(':')[2].strip())
        elif text.startswith((self.ui.assistant_name+':', 'ULTRON:', 'ULTRON:')):
            answer=text.partition(':')[2].strip()
            self.emit(kind='log', role='assistant', text=answer)
            if self._remote_task_ids:
                command_id=self._remote_task_ids.pop(0)
                self._complete_remote_command(command_id,True,answer or 'Görev tamamlandı.')
        elif text.startswith('ERR:'):
            error=text[4:].strip()
            self.emit(kind='error', text=error)
            if self._remote_task_ids:
                command_id=self._remote_task_ids.pop(0)
                self._complete_remote_command(command_id,False,error or 'Görev başarısız.')

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
        if name.startswith('phone:'):
            self.phone_command(name.partition(':')[2])
        elif name=='hologrambrowser':
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
        elif name=='controls':
            win._toggle_controls(True)
        elif name=='plugins':
            self.plugins()
        elif name=='hologram':
            self.ui._open_hologram()
        elif name=='shutdown':
            win.close()  # Normal Qt exit; Services performs authenticated graceful backend shutdown.
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
    video=getattr(win,'_video_cont',None)
    if video is not None:
        video_dialog=QDialog(win);video_dialog.setWindowTitle('ULTRON · Video');video_dialog.resize(960,600)
        QVBoxLayout(video_dialog).addWidget(video)
        win._video_open_sig.connect(lambda *args:video_dialog.show())
        win._video_close_sig.connect(video_dialog.hide)
        video_dialog.finished.connect(lambda _:win.stop_video())
        dialogs.append(video_dialog)
    overlay=getattr(win,'_overlay',None)
    if overlay is not None:
        overlay.setParent(view)
        overlay.show()
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
