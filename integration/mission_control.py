"""Reference-layout mission control using real native controls and live telemetry."""
import math
import time
from pathlib import Path
import psutil
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QPainterPath
from PyQt6.QtWidgets import QWidget, QPushButton, QLineEdit, QTextEdit, QStackedWidget, QToolBar, QFileDialog, QMessageBox
from .paths import ROOT


class MissionControl(QWidget):
    DESIGN_W, DESIGN_H = 1672, 941
    def __init__(self, ui, tools):
        super().__init__()
        self.ui, self.win, self.tools = ui, ui._win, tools
        self.plate = QPixmap(str(ROOT/'assets/ultron/mission-control-plate.png'))
        self.setMinimumSize(1000,560)
        self.widgets=[]
        self.phase=0
        self.disk='—'
        self.selected='DASHBOARD'
        self.setStyleSheet('background:transparent;')
        actions=[('DASHBOARD',lambda:self.navigate('DASHBOARD')),
                 ('SYSTEM',self.system_info),('AI CORE',self.local_ai),
                 ('VISION',self.camera),('FILES',self.pick_file),('BROWSER',lambda:self.compose('Web araştırması: ')),
                 ('TERMINAL',lambda:self.compose('Kod / terminal isteği: ')),
                 ('AUTOMATION',self.local_ai),('SECURITY',self.security),('SETTINGS',self.settings)]
        for i,(label,callback) in enumerate(actions):
            self.button(label,(14,111+i*48,168,42),callback,'nav-'+label.lower())
        bottom=[('KONUŞ',self.win._toggle_mute),('GÖR',self.camera),('ARA',lambda:self.compose('Araştır: ')),
                ('AÇ',self.pick_file),('ÇALIŞTIR',self.local_ai),('PLANLA',lambda:self.compose('Plan hazırla: '))]
        for i,(label,callback) in enumerate(bottom):
            self.button(label,(550+i*88,852,80,30),callback,'action-'+str(i))
        self.button('HOLOGRAMI AÇ',(1503,406,145,36),lambda:ui._open_hologram(),'model-0')
        self.button('KAMERAYI AÇ',(89,815,135,35),self.camera,'live-camera')
        self.button('HARİTA ARA',(1460,833,140,32),lambda:self.compose('Haritada yer araştır: '),'map-search')
        self.entry=QLineEdit(self)
        self.entry.setPlaceholderText('ULTRON’a mesaj yaz…')
        self.entry.setStyleSheet('QLineEdit {background:rgba(5,5,8,220);color:#f2eeee;border:1px solid #992334;border-radius:4px;padding:5px;} QLineEdit:focus {border-color:#ff3b4d;}')
        self.entry.returnPressed.connect(self.submit)
        self.widgets.append((self.entry,(550,891,476,34)))
        self.button('GÖNDER',(1032,891,80,34),self.submit,'send')
        self.log=QTextEdit(self);self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(100)
        self.log.setStyleSheet('QTextEdit{background:rgba(4,4,6,180);color:#e9dce0;border:0;padding:4px;} QScrollBar:vertical{width:5px;background:#12070a;} QScrollBar::handle:vertical{background:#862435;min-height:12px;}')
        self.widgets.append((self.log,(1434,164,210,176)))
        self.win._log_sig.connect(self.log.append)
        self.log.append('ULTRON kontrol merkezi hazır.')
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(80)
        self.telemetry=QTimer(self);self.telemetry.timeout.connect(self.refresh_disk);self.telemetry.start(5000)
        self.refresh_disk()
        self.relayout()

    def refresh_disk(self):
        try:self.disk=f'{psutil.disk_usage(str(ROOT.anchor)).percent:.0f}%'
        except OSError:self.disk='—'

    def button(self,text,rect,callback,name):
        b=QPushButton(text,self);b.setObjectName('mission-'+name)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet('QPushButton{background:rgba(5,4,6,95);color:#e8e3e4;border:1px solid transparent;text-align:left;padding-left:10px;} QPushButton:hover{background:rgba(175,7,24,100);border:1px solid #d62e42;} QPushButton:pressed{background:#8c1528;}')
        b.clicked.connect(callback);self.widgets.append((b,rect));return b

    def navigate(self,name):
        self.selected=name;self.update()

    def compose(self,prefix=''):
        self.entry.setText(prefix);self.entry.setFocus()

    def submit(self):
        value=self.entry.text().strip()
        if not value:return
        self.win._input.setText(value);self.win._send();self.entry.clear()

    def pick_file(self):
        filename,_=QFileDialog.getOpenFileName(self,'ULTRON · Dosya ekle')
        if filename:
            self.win._drop_zone._set_file(filename)
            self.log.append('Dosya: '+Path(filename).name)

    def local_ai(self):
        self.ui._merged_dock.show();self.ui._merged_dock.raise_()

    def security(self):
        self.ui._review_action()

    def settings(self):
        self.tools();self.win._drawer_btn.setChecked(True);self.win._toggle_drawer(True)

    def camera(self):
        self.tools();self.win.start_camera_stream()

    def system_info(self):
        QMessageBox.information(self,'Sistem durumu',
            'CPU: '+self.win._bar_cpu._text+'\nRAM: '+self.win._bar_mem._text+
            '\nGPU: '+self.win._bar_gpu._text+'\nDisk: '+self.disk+
            '\nSıcaklık: '+self.win._bar_tmp._text+'\n'+self.win._uptime_lbl.text())

    def tick(self):
        self.phase+=.08
        if self.isVisible():self.update()

    def relayout(self):
        scale=min(self.width()/self.DESIGN_W,self.height()/self.DESIGN_H)
        ox=(self.width()-self.DESIGN_W*scale)/2;oy=(self.height()-self.DESIGN_H*scale)/2
        self.transform=(scale,ox,oy)
        for widget,(x,y,w,h) in self.widgets:
            widget.setGeometry(round(ox+x*scale),round(oy+y*scale),round(w*scale),round(h*scale))
            font=QFont('Segoe UI');font.setPixelSize(max(9,round(13*scale)));widget.setFont(font)

    def resizeEvent(self,event):
        self.relayout();super().resizeEvent(event)

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(),QColor('#020203'))
        scale,ox,oy=self.transform;p.translate(ox,oy);p.scale(scale,scale)
        p.drawPixmap(QRectF(0,0,1672,941),self.plate,QRectF(self.plate.rect()))
        def text(x,y,value,size=14,color='#e5e0e0',width=400):
            font=QFont('Segoe UI');font.setPixelSize(size);p.setFont(font);p.setPen(QColor(color))
            p.drawText(QRectF(x,y,width,size*1.6),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter,value)
        def glass(x,y,w,h):
            p.setPen(QPen(QColor('#8a2433'),.7));p.setBrush(QColor(3,3,5,205));p.drawRoundedRect(QRectF(x,y,w,h),6,6)
        glass(17,17,286,75)
        text(37,25,'◈',42,'#ff243f');text(97,23,'U L T R O N',29)
        text(102,61,'AI  MISSION  CONTROL',11,'#b78e99')
        metrics=[('CPU',self.win._bar_cpu._text,self.win._bar_cpu._value),
                 ('GPU',self.win._bar_gpu._text,self.win._bar_gpu._value),
                 ('RAM',self.win._bar_mem._text,self.win._bar_mem._value),
                 ('SSD',self.disk,float(self.disk.rstrip('%')) if '%' in self.disk else 0),
                 ('NETWORK',self.win._bar_net._text,self.win._bar_net._value)]
        for i,(label,value,amount) in enumerate(metrics):
            x=376+i*133;glass(x,22,128,67)
            text(x+16,30,label,11,'#ec9caa');text(x+16,46,value,17)
            p.fillRect(QRectF(x+16,73,94,3),QColor('#352029'))
            p.fillRect(QRectF(x+16,73,94*min(100,amount)/100,3),QColor('#ff3049'))
        glass(1320,22,116,66);text(1340,24,time.strftime('%H:%M'),28);text(1340,60,time.strftime('%d.%m.%Y'),11)
        glass(1444,22,126,66);text(1458,29,'HAVA DURUMU',11,'#dc9ca6');text(1458,50,'Bağlı değil',14)
        text(221,137,'WORLD',14);text(498,173,'KONUM',10,'#ff465b');text(498,194,'Bağlı değil',12)
        text(222,366,'SYSTEM STATUS',14)
        for i,(label,value,_) in enumerate(metrics[:4]):
            text(339,409+i*33,label,10,'#d38697',90);text(380,408+i*33,value,14,width=66)
        text(465,409,'SICAKLIK',10,'#d38697');text(465,426,self.win._bar_tmp._text,14)
        text(465,467,'ÇALIŞMA SÜRESİ',10,'#d38697');text(465,485,self.win._uptime_lbl.text().replace('UP','').strip(),14)
        text(465,520,'YEREL SİSTEM',10,'#d38697')
        text(1175,178,'AI ASSISTANT',14)
        amp=min(1,max(0,self.win.hud._amp_disp))
        muted=self.ui.muted
        for i in range(48):
            height=2 if muted else 2+amp*45*(.3+.7*math.sin(i*.73+self.phase*8)**2)*(1-abs(i-24)/25)
            p.setPen(QPen(QColor('#ff324b' if not muted else '#70404a'),2))
            p.drawLine(QPointF(1186+i*4,241-height/2),QPointF(1186+i*4,241+height/2))
        state=self.win.hud.state
        text(1177,279,'Mikrofon kapalı' if muted else 'Mikrofon açık',13,'#ff7186')
        text(1177,307,state,12)
        text(1177,334,'Yerel ses denetimi',11,'#aa8b95')
        text(1435,132,'RECENT ACTIVITY',14)
        text(1160,386,'3D MODEL / HOLOGRAM',14)
        for i,label in enumerate(('Çalışma alanında:', 'Parça inceleme', 'GLB / proje aktarımı')):
            text(1513,450+i*29,label,11,'#c2a8ae',140)
        text(1165,551,'Örnek model · incelemek için HOLOGRAM',10,'#c2a8ae')
        text(1180,598,'CITY MAP',14)
        glass(1173,815,278,37);text(1187,824,'Görsel referans · canlı harita bağlı değil',11)
        text(89,623,'LIVE FEED',14)
        glass(86,778,399,28);text(100,782,'Örnek görünüm · canlı kamera bağlantısı yok',11)
        glass(540,811,569,79)
        for i,glyph in enumerate(('◉','◎','⌕','▱','▷','◷')):text(576+i*88,822,glyph,23,'#ff3851')
        text(567,926,'Ctrl+H  Hologram   ·   Ctrl+L  Yerel AI   ·   ESC  Konuşmayı durdur',10,'#d29ba6')
        p.end()


def attach(ui):
    win=ui._win
    original=win.takeCentralWidget()
    stack=QStackedWidget(win);stack.addWidget(original)
    win.setCentralWidget(stack)
    back=QToolBar('Araçlar',win);back.setMovable(False)
    back.setStyleSheet('QToolBar{background:#080609;color:#f6dee3;border:0;} QToolButton{color:#ff5168;padding:6px;}')
    win.addToolBar(back);back.hide()
    def tools():
        stack.setCurrentIndex(0);back.show()
    mission=MissionControl(ui,tools);stack.addWidget(mission)
    def home():stack.setCurrentIndex(1);back.hide()
    back.addAction('← ULTRON kontrol merkezi',home)
    home()
    for signal in ('_content_sig','_quiz_sig','_review_sig','_video_open_sig','_cam_stream_sig','_reconfig_sig','_confirm_sig'):
        getattr(win,signal).connect(lambda *args:tools())
    if hasattr(ui,'_hologram_toolbar'):ui._hologram_toolbar.hide()
    win.addAction(ui._hologram_action)
    ui._mission=mission;ui._mission_stack=stack;ui._mission_home=home;ui._mission_tools=tools
