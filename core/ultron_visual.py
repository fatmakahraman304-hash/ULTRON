"""High-DPI particle reactor and machined panel frames for the native desktop."""
import math
import random
from pathlib import Path
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PyQt6.QtWidgets import QWidget


def hull(p, rect, compact=False):
    x,y,w,h=rect.x(),rect.y(),rect.width(),rect.height()
    cut=10 if compact else 19
    def outline(inset):
        l,t,r,b=x+inset,y+inset,x+w-inset,y+h-inset
        path=QPainterPath(QPointF(l,t+cut))
        for xx,yy in [(l+cut,t),(r-cut*1.7,t),(r,t+cut*1.7),(r,b-cut),(r-cut,b),(l+cut*1.4,b),(l,b-cut*1.4)]:path.lineTo(xx,yy)
        path.closeSubpath();return path
    outer=outline(1)
    metal=QLinearGradient(x,y,x+w,y+h)
    for pos,col in [(0,'#505760'),(.025,'#171a22'),(.075,'#070a0f'),(.78,'#080b11'),(.96,'#1e222b'),(1,'#626871')]:metal.setColorAt(pos,QColor(col))
    p.setBrush(metal);p.setPen(QPen(QColor('#535861'),1));p.drawPath(outer)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for inset,col,width in [(5,'#171b22',1),(8,'#3d252d',.6)]:
        p.setPen(QPen(QColor(col),width));p.drawPath(outline(inset))
    neon=QPainterPath(QPointF(x+3,y+min(h*.36,53)))
    neon.lineTo(x+3,y+cut);neon.lineTo(x+cut,y+3);neon.lineTo(x+min(w*.48,132),y+3)
    for width,alpha in [(7,12),(3,35),(1.5,220)]:p.setPen(QPen(QColor(255,30,50,alpha),width));p.drawPath(neon)
    p.setPen(QPen(QColor('#ffd2d7'),.8));p.drawLine(QPointF(x+5,y+cut),QPointF(x+cut,y+5))
    p.setPen(QPen(QColor('#ed233f'),2));p.drawLine(QPointF(x+w-46,y+h-4),QPointF(x+w-cut,y+h-4))
    p.setPen(QPen(QColor('#9ca5ae'),1));p.drawLine(QPointF(x+w-cut*1.7,y+6),QPointF(x+w-6,y+cut*1.7))
    if not compact:
        p.setPen(QPen(QColor('#393c45'),1))
        for k in range(4):
            xx=x+w*.58+k*5
            p.drawLine(QPointF(xx,y+3),QPointF(xx+6,y+9))
        for xx,yy in [(x+16,y+h-25),(x+w-16,y+40)]:
            p.setBrush(QColor('#83858d'));p.setPen(Qt.PenStyle.NoPen);p.drawEllipse(QRectF(xx-1.4,yy-1.4,2.8,2.8))


class MetalPanel(QWidget):
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        hull(p,QRectF(1,1,self.width()-2,self.height()-2))
        p.end()


_environment_image = None


def paint_environment(p,w,h,phase):
    global _environment_image
    if _environment_image is None:
        source = Path(__file__).resolve().parents[1]/'assets/ultron/reactor-environment.png'
        _environment_image = QPixmap(str(source)) if source.is_file() else QPixmap()
    p.save()
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    if not _environment_image.isNull():
        p.drawPixmap(QRectF(0,0,w,h),_environment_image,QRectF(_environment_image.rect()))
    else:
        atmosphere=QRadialGradient(w*.5,h*.55,min(w,h)*.65)
        atmosphere.setColorAt(0,QColor('#1c0b12'));atmosphere.setColorAt(1,QColor('#050609'))
        p.fillRect(QRectF(0,0,w,h),atmosphere)
    # Dark edge fades merge the illustration into the live native interface.
    for left in (True,False):
        gradient=QLinearGradient(0 if left else w,0,w*.13 if left else w*.87,0)
        gradient.setColorAt(0,QColor('#050609'));gradient.setColorAt(1,QColor(5,6,9,0))
        p.fillRect(QRectF(0 if left else w*.87,0,w*.13,h),gradient)
    p.restore()


class ParticleCore:
    def __init__(self):
        self.key=None
        self.texture=None

    def paint(self,p,cx,cy,r,phase,amplitude,name='ULTRON'):
        dpr=p.device().devicePixelRatioF()
        key=(round(r),round(dpr,2))
        if self.key!=key:
            self.key=key
            side=int(math.ceil(r*2.3))
            self.texture=QPixmap(int(side*dpr),int(side*dpr))
            self.texture.setDevicePixelRatio(dpr);self.texture.fill(Qt.GlobalColor.transparent)
            q=QPainter(self.texture);q.setRenderHint(QPainter.RenderHint.Antialiasing)
            q.translate(side/2,side/2)
            glow=QRadialGradient(0,0,r)
            for pos,rgba in [(0,(0,0,0,0)),(.58,(255,15,45,0)),(.70,(230,5,30,12)),(.775,(255,18,48,80)),(.805,(255,60,80,150)),(.825,(255,12,35,65)),(.95,(255,0,30,0)),(1,(0,0,0,0))]:glow.setColorAt(pos,QColor(*rgba))
            q.setPen(Qt.PenStyle.NoPen);q.setBrush(glow);q.drawEllipse(QRectF(-r,-r,2*r,2*r))
            rng=random.Random(2207)
            for i in range(3000):
                a=rng.random()*math.tau
                rad=r*(.805+rng.gauss(0,.028 if i%4 else .065))
                x,y=math.cos(a)*rad,math.sin(a)*rad
                size=rng.uniform(.4,1.5)*(r/300)**.35
                bright=i%11==0
                q.setBrush(QColor(255,180 if bright else 32,185 if bright else 57,rng.randint(90,245)))
                q.drawEllipse(QRectF(x-size,y-size,size*2,size*2))
            q.end()
        p.save();p.translate(cx,cy)
        # Sparse telemetry rings outside the particulate volume.
        p.setBrush(Qt.BrushStyle.NoBrush)
        for scale in (.94,1.025):
            p.setPen(QPen(QColor('#35323c'),.7));p.drawEllipse(QRectF(-r*scale,-r*scale,2*r*scale,2*r*scale))
        for i in range(120):
            a=i*math.tau/120
            p.setPen(QPen(QColor('#8d4754' if i%5==0 else '#382a34'),1))
            p.drawLine(QPointF(math.cos(a)*r*.96,math.sin(a)*r*.96),QPointF(math.cos(a)*r*(1.015 if i%5==0 else .987),math.sin(a)*r*(1.015 if i%5==0 else .987)))
        p.save();p.rotate(phase*3)
        scale=1+min(amplitude,.9)*.025
        p.scale(scale,scale)
        logical=self.texture.width()/self.texture.devicePixelRatioF()
        p.drawPixmap(QPointF(-logical/2,-logical/2),self.texture);p.restore()
        # Tilted orbital paths give the circular field spatial depth.
        for k,angle in enumerate((-27,31,-51)):
            p.save();p.rotate(angle+math.sin(phase*.2+k)*5)
            orbit=QRectF(-r*1.04,-r*(.27+k*.035),r*2.08,r*(.54+k*.07))
            p.setBrush(Qt.BrushStyle.NoBrush)
            for width,alpha in [(5,12),(2,55),(.7,190)]:
                p.setPen(QPen(QColor(255,75,95,alpha) if k!=1 else QColor(192,209,220,alpha),width));p.drawEllipse(orbit)
            a=phase*(.3+k*.08)+k*2
            x,y=math.cos(a)*r*1.04,math.sin(a)*r*(.27+k*.035)
            flare=QRadialGradient(x,y,12)
            flare.setColorAt(0,QColor('#ffffff'));flare.setColorAt(.15,QColor('#ff8290'));flare.setColorAt(1,QColor(255,20,50,0))
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(flare);p.drawEllipse(QRectF(x-12,y-12,24,24));p.restore()
        p.setPen(QPen(QColor('#e8edf4'),1))
        font=QFont('Segoe UI',max(14,int(r*.085)),QFont.Weight.DemiBold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,5);p.setFont(font)
        p.drawText(QRectF(-r*.6,-25,r*1.2,50),Qt.AlignmentFlag.AlignCenter,name.upper())
        font=QFont('Segoe UI',8);font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,3);p.setFont(font);p.setPen(QColor('#a47b85'))
        p.drawText(QRectF(-r*.6,29,r*1.2,24),Qt.AlignmentFlag.AlignCenter,'N E U R A L   C O R E')
        p.restore()
