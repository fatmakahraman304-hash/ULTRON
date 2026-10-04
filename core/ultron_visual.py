"""High-DPI particle reactor and machined panel frames for the native desktop."""
import math
import random
from pathlib import Path
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PyQt6.QtWidgets import QWidget


def hull(p, rect, compact=False):
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    cut = 9 if compact else 18

    def outline(inset):
        l = x + inset
        t = y + inset
        r = x + w - inset
        b = y + h - inset
        c = max(4, cut - inset * .25)

        path = QPainterPath(QPointF(l, t + c))
        path.lineTo(l + c, t)
        path.lineTo(r - c * 1.65, t)
        path.lineTo(r, t + c * 1.65)
        path.lineTo(r, b - c)
        path.lineTo(r - c, b)
        path.lineTo(l + c * 1.35, b)
        path.lineTo(l, b - c * 1.35)
        path.closeSubpath()
        return path

    outer = outline(1)

    metal = QLinearGradient(x, y, x + w, y + h)
    metal.setColorAt(0.00, QColor("#515762"))
    metal.setColorAt(0.025, QColor("#171b22"))
    metal.setColorAt(0.085, QColor("#06080d"))
    metal.setColorAt(0.52, QColor("#0a0b10"))
    metal.setColorAt(0.90, QColor("#10131a"))
    metal.setColorAt(0.975, QColor("#232832"))
    metal.setColorAt(1.00, QColor("#5d626c"))

    p.setPen(QPen(QColor("#555b66"), 1))
    p.setBrush(metal)
    p.drawPath(outer)

    inner = outline(7)

    glass = QLinearGradient(x, y, x, y + h)
    glass.setColorAt(0.00, QColor(22, 26, 34, 236))
    glass.setColorAt(0.18, QColor(8, 10, 15, 238))
    glass.setColorAt(0.75, QColor(5, 7, 11, 242))
    glass.setColorAt(1.00, QColor(14, 8, 13, 242))

    p.setBrush(glass)
    p.setPen(QPen(QColor(88, 48, 58, 100), .8))
    p.drawPath(inner)

    # Inner technical frame
    p.setBrush(Qt.BrushStyle.NoBrush)
    for inset, col, width in (
        (4, QColor(255, 255, 255, 22), .7),
        (8, QColor(110, 48, 62, 105), .8),
        (11, QColor(30, 34, 43, 190), .7),
    ):
        p.setPen(QPen(col, width))
        p.drawPath(outline(inset))

    # Top-left red energy rail
    neon = QPainterPath(QPointF(x + 3, y + min(h * .38, 55)))
    neon.lineTo(x + 3, y + cut)
    neon.lineTo(x + cut, y + 3)
    neon.lineTo(x + min(w * .46, 145), y + 3)

    for width, alpha in ((8, 12), (4, 34), (1.7, 235)):
        p.setPen(QPen(QColor(255, 25, 52, alpha), width))
        p.drawPath(neon)

    # Bottom-right red energy rail
    p.setPen(QPen(QColor(255, 31, 57, 215), 1.7))
    p.drawLine(
        QPointF(x + w - min(60, w * .22), y + h - 4),
        QPointF(x + w - cut, y + h - 4)
    )

    # Metallic corner shine
    p.setPen(QPen(QColor(220, 230, 242, 110), .8))
    p.drawLine(
        QPointF(x + 5, y + cut),
        QPointF(x + cut, y + 5)
    )
    p.drawLine(
        QPointF(x + w - cut * 1.55, y + 6),
        QPointF(x + w - 6, y + cut * 1.55)
    )

    if not compact:
        p.setPen(QPen(QColor(100, 110, 125, 75), 1))
        for k in range(4):
            xx = x + w * .57 + k * 6
            p.drawLine(
                QPointF(xx, y + 3),
                QPointF(xx + 7, y + 10)
            )

        for xx, yy in (
            (x + 17, y + h - 24),
            (x + w - 17, y + 39),
        ):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#7d838c"))
            p.drawEllipse(QRectF(xx - 1.4, yy - 1.4, 2.8, 2.8))


class MetalPanel(QWidget):
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        hull(p,QRectF(1,1,self.width()-2,self.height()-2))
        p.end()


def paint_environment(p, w, h, phase):
    """Procedural ULTRON chamber. No external bitmap assets."""
    if w <= 2 or h <= 2:
        return

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    cx = w * .5
    cy = h * .43
    horizon = h * .695
    short = min(w, h)

    # Deep layered atmosphere
    bg = QLinearGradient(0, 0, 0, h)
    bg.setColorAt(0.00, QColor("#030407"))
    bg.setColorAt(0.34, QColor("#07080d"))
    bg.setColorAt(0.68, QColor("#10060b"))
    bg.setColorAt(1.00, QColor("#030407"))
    p.fillRect(QRectF(0, 0, w, h), bg)

    atmosphere = QRadialGradient(cx, cy, short * .75)
    atmosphere.setColorAt(0.00, QColor(120, 5, 25, 58))
    atmosphere.setColorAt(0.22, QColor(85, 4, 18, 35))
    atmosphere.setColorAt(0.52, QColor(35, 5, 12, 18))
    atmosphere.setColorAt(1.00, QColor(0, 0, 0, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(atmosphere)
    p.drawEllipse(
        QRectF(
            cx - short * .75,
            cy - short * .75,
            short * 1.5,
            short * 1.5
        )
    )

    # Central volumetric reactor beam
    beam = QLinearGradient(cx, h * .02, cx, horizon)
    beam.setColorAt(0.00, QColor(255, 15, 48, 0))
    beam.setColorAt(0.22, QColor(255, 30, 58, 25))
    beam.setColorAt(0.52, QColor(255, 18, 48, 38))
    beam.setColorAt(0.83, QColor(255, 18, 48, 12))
    beam.setColorAt(1.00, QColor(255, 0, 30, 0))
    p.fillRect(
        QRectF(cx - w * .085, h * .02, w * .17, horizon),
        beam
    )

    # Soft halo behind Neural Core
    halo = QRadialGradient(cx, cy, short * .39)
    halo.setColorAt(0.00, QColor(255, 28, 58, 34))
    halo.setColorAt(0.45, QColor(255, 18, 48, 16))
    halo.setColorAt(0.75, QColor(255, 10, 35, 5))
    halo.setColorAt(1.00, QColor(255, 0, 20, 0))
    p.setBrush(halo)
    p.drawEllipse(
        QRectF(
            cx - short * .39,
            cy - short * .39,
            short * .78,
            short * .78
        )
    )

    # Ceiling rails / perspective chamber
    p.setBrush(Qt.BrushStyle.NoBrush)

    for side in (-1, 1):
        for i in range(7):
            depth = i / 6
            outer_x = cx + side * w * (.49 - depth * .10)
            inner_x = cx + side * w * (.19 + depth * .025)
            top_y = h * (.06 + depth * .055)
            end_y = horizon - h * (.04 + depth * .018)

            p.setPen(
                QPen(
                    QColor(65, 72, 85, int(35 + depth * 45)),
                    1
                )
            )
            p.drawLine(
                QPointF(outer_x, top_y),
                QPointF(inner_x, end_y)
            )

    # Large angular side structures
    for side in (-1, 1):
        for i in range(4):
            d = i / 3
            outer = 0 if side < 0 else w
            edge = cx + side * w * (.39 - d * .035)
            top = h * (.16 + i * .11)
            bottom = min(horizon + h * .03, top + h * .31)

            path = QPainterPath(
                QPointF(outer, top - h * .055)
            )
            path.lineTo(
                outer - side * w * (.065 + d * .018),
                top
            )
            path.lineTo(edge, bottom)
            path.lineTo(
                edge + side * w * .025,
                bottom + h * .045
            )
            path.lineTo(
                outer,
                top + h * .225
            )
            path.closeSubpath()

            steel = QLinearGradient(
                outer, top,
                edge, bottom
            )
            steel.setColorAt(0.00, QColor("#242a34"))
            steel.setColorAt(0.17, QColor("#11151c"))
            steel.setColorAt(0.58, QColor("#06080d"))
            steel.setColorAt(0.86, QColor("#13090f"))
            steel.setColorAt(1.00, QColor("#28202a"))

            p.setPen(QPen(QColor(78, 86, 101, 95), 1))
            p.setBrush(steel)
            p.drawPath(path)

            # Structural red light strip
            strip_x = edge - side * w * .008

            p.setPen(QPen(QColor(255, 20, 52, 20), 9))
            p.drawLine(
                QPointF(strip_x, bottom - h * .12),
                QPointF(strip_x, bottom + h * .012)
            )

            p.setPen(QPen(QColor(255, 38, 66, 220), 1.8))
            p.drawLine(
                QPointF(strip_x, bottom - h * .12),
                QPointF(strip_x, bottom + h * .012)
            )

    # Rear wall technical arcs
    p.setBrush(Qt.BrushStyle.NoBrush)

    for rr, alpha, width in (
        (.37, 55, 1.0),
        (.43, 38, 1.0),
        (.50, 24, .8),
    ):
        rad = short * rr
        p.setPen(QPen(QColor(185, 50, 72, alpha), width))
        p.drawEllipse(
            QRectF(
                cx - rad,
                cy - rad,
                rad * 2,
                rad * 2
            )
        )

    # Reactor platform
    py = h * .795
    pw = min(w * .82, h * 1.35)
    ph = max(30, h * .13)

    platform_glow = QRadialGradient(
        cx, py, pw * .42
    )
    platform_glow.setColorAt(
        0.00, QColor(255, 28, 58, 48)
    )
    platform_glow.setColorAt(
        .35, QColor(255, 15, 45, 20)
    )
    platform_glow.setColorAt(
        1.00, QColor(255, 0, 30, 0)
    )

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(platform_glow)
    p.drawEllipse(
        QRectF(
            cx - pw * .42,
            py - ph * 1.55,
            pw * .84,
            ph * 3.1
        )
    )

    p.setBrush(Qt.BrushStyle.NoBrush)

    for scale, alpha, width in (
        (1.00, 75, 2.3),
        (.90, 115, 1.8),
        (.77, 185, 1.5),
        (.63, 225, 1.2),
        (.48, 135, .9),
    ):
        rect = QRectF(
            cx - pw * scale / 2,
            py - ph * scale / 2,
            pw * scale,
            ph * scale
        )

        p.setPen(
            QPen(
                QColor(255, 29, 59, alpha),
                width
            )
        )
        p.drawEllipse(rect)

    # Mechanical platform thickness
    for j in range(4):
        yy = py + ph * (.18 + j * .075)
        span = pw * (1 - j * .045)

        p.setPen(
            QPen(
                QColor(
                    65 + j * 12,
                    25,
                    32,
                    130
                ),
                2
            )
        )
        p.drawLine(
            QPointF(cx - span * .43, yy),
            QPointF(cx + span * .43, yy)
        )

    # Floor perspective grid
    p.setPen(QPen(QColor(118, 35, 52, 70), 1))

    for i in range(-13, 14):
        target = cx + i * w * .067
        p.drawLine(
            QPointF(cx, horizon),
            QPointF(target, h)
        )

    for j in range(1, 14):
        t = j / 14
        yy = horizon + (h - horizon) * (t * t)

        p.setPen(
            QPen(
                QColor(
                    125,
                    36,
                    52,
                    int(20 + 75 * t)
                ),
                1
            )
        )
        p.drawLine(
            QPointF(0, yy),
            QPointF(w, yy)
        )

    # Small procedural particles in the chamber
    p.setPen(Qt.PenStyle.NoPen)

    for i in range(38):
        a = i * 2.399963 + phase * (.04 + (i % 5) * .006)
        radius = short * (.18 + ((i * 37) % 100) / 100 * .42)

        px = cx + math.cos(a) * radius
        py2 = cy + math.sin(a * .73) * radius * .54

        size = 1.0 + (i % 3) * .55
        alpha = 28 + (i % 7) * 13

        p.setBrush(
            QColor(255, 48, 72, alpha)
        )
        p.drawEllipse(
            QRectF(
                px - size,
                py2 - size,
                size * 2,
                size * 2
            )
        )

    # Animated scanning band
    scan_y = (
        phase * 28
    ) % max(1, h)

    scan = QLinearGradient(
        0,
        scan_y - 15,
        0,
        scan_y + 15
    )
    scan.setColorAt(
        0.00, QColor(255, 40, 64, 0)
    )
    scan.setColorAt(
        0.50, QColor(255, 40, 64, 18)
    )
    scan.setColorAt(
        1.00, QColor(255, 40, 64, 0)
    )

    p.fillRect(
        QRectF(0, scan_y - 15, w, 30),
        scan
    )

    # Fine scanlines
    p.setPen(
        QPen(
            QColor(255, 255, 255, 6),
            1
        )
    )

    yy = 0
    while yy < h:
        p.drawLine(
            QPointF(0, yy),
            QPointF(w, yy)
        )
        yy += 7

    # Dark side vignette
    for left in (True, False):
        start_x = 0 if left else w
        end_x = w * .16 if left else w * .84

        fade = QLinearGradient(
            start_x, 0,
            end_x, 0
        )

        fade.setColorAt(
            0,
            QColor(2, 3, 6, 245)
        )
        fade.setColorAt(
            1,
            QColor(2, 3, 6, 0)
        )

        p.fillRect(
            QRectF(
                0 if left else w * .84,
                0,
                w * .16,
                h
            ),
            fade
        )

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
            for pos,rgba in [(0,(0,0,0,0)),(.58,(255,15,45,0)),(.70,(230,5,30,12)),(.775,(255,18,48,105)),(.805,(255,75,95,205)),(.825,(255,12,35,92)),(.95,(255,0,30,0)),(1,(0,0,0,0))]:glow.setColorAt(pos,QColor(*rgba))
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

        # Procedural outer energy aura
        aura = QRadialGradient(0, 0, r * 1.24)
        aura.setColorAt(0.00, QColor(255, 28, 58, 25))
        aura.setColorAt(0.48, QColor(255, 22, 52, 18))
        aura.setColorAt(0.76, QColor(255, 12, 42, 8))
        aura.setColorAt(1.00, QColor(255, 0, 30, 0))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(aura)
        p.drawEllipse(
            QRectF(
                -r * 1.24,
                -r * 1.24,
                r * 2.48,
                r * 2.48
            )
        )
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
