"""High-DPI particle reactor and machined panel frames for the native desktop."""
import math
import random
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PyQt6.QtWidgets import QWidget


class MetalPanel(QWidget):
    def paintEvent(self, event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width()-2,self.height()-2
        shape=QPainterPath(QPointF(1,16))
        for x,y in [(16,1),(w-18,1),(w,18),(w,h-17),(w-17,h),(17,h),(1,h-16)]:shape.lineTo(x,y)
        shape.closeSubpath()
        metal=QLinearGradient(0,0,w,h)
        for pos,col in [(0,'#20232a'),(.035,'#0c0f14'),(.5,'#080b10'),(1,'#14171d')]:metal.setColorAt(pos,QColor(col))
        p.setBrush(metal);p.setPen(QPen(QColor('#3a3e48'),1));p.drawPath(shape)
        p.setPen(QPen(QColor('#ff344b'),2))
        p.drawLine(QPointF(2,34),QPointF(2,16));p.drawLine(QPointF(2,16),QPointF(16,2));p.drawLine(QPointF(16,2),QPointF(min(84,w-25),2))
        p.setPen(QPen(QColor('#81303d'),1));p.drawLine(QPointF(w-88,h-1),QPointF(w-18,h-1))
        p.setPen(QPen(QColor('#68717e'),1));p.drawLine(QPointF(w-18,5),QPointF(w-5,18))
        p.end()


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
