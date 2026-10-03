"""Resolution-independent metallic ULTRON mask for the native HUD."""
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainterPath, QPen, QLinearGradient, QRadialGradient


def paint_mask(p, cx, cy, radius, phase, amplitude):
    p.save()
    p.translate(cx, cy)
    p.scale(radius, radius)
    glow = QRadialGradient(0, 0, .95)
    glow.setColorAt(0, QColor(255, 20, 42, 48))
    glow.setColorAt(1, QColor(255, 20, 42, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(glow)
    p.drawEllipse(QRectF(-1,-1,2,2))
    def plate(points, bright=False):
        path = QPainterPath(QPointF(*points[0]))
        for point in points[1:]: path.lineTo(QPointF(*point))
        path.closeSubpath()
        metal = QLinearGradient(-.45,-.7,.45,.65)
        metal.setColorAt(0,QColor('#b5bec8' if bright else '#59636f'))
        metal.setColorAt(.35,QColor('#353e49'))
        metal.setColorAt(.55,QColor('#73808c' if bright else '#272f39'))
        metal.setColorAt(1,QColor('#080b10'))
        p.setBrush(metal)
        p.setPen(QPen(QColor('#8a949e' if bright else '#414955'),.006))
        p.drawPath(path)
    # Dark silhouette and independently shaded armor plates.
    plate([(-.32,-.66),(-.47,-.36),(-.42,.29),(-.2,.64),(0,.76),(.2,.64),(.42,.29),(.47,-.36),(.32,-.66),(0,-.78)])
    for side in (-1,1):
        def mirrored(points): return [(side*x,y) for x,y in points]
        plate(mirrored([(.025,-.74),(.27,-.65),(.36,-.43),(.26,-.16),(.08,-.07),(.025,-.3)]),True)
        plate(mirrored([(.31,-.64),(.45,-.36),(.39,.01),(.28,-.1),(.36,-.44)]))
        plate(mirrored([(.39,.06),(.25,.04),(.12,.22),(.13,.37),(.3,.29),(.4,.15)]),True)
        plate(mirrored([(.4,.2),(.29,.36),(.12,.48),(.1,.66),(.2,.6),(.37,.32)]))
        plate(mirrored([(.08,-.06),(.18,.08),(.1,.28),(.015,.33),(.015,.05)]))
        eye = QPainterPath(QPointF(side*.09,.025))
        for x,y in [(.32,-.075),(.27,.055),(.12,.115)]: eye.lineTo(side*x,y)
        eye.closeSubpath()
        p.setBrush(QColor('#ff3344'))
        for width,alpha in [(.055,22),(.032,55),(.012,160)]:
            p.setPen(QPen(QColor(255,25,45,alpha),width));p.drawPath(eye)
        p.setPen(QPen(QColor('#ffe0df'),.006));p.drawPath(eye)
        p.setPen(QPen(QColor('#e82436'),.007))
        p.drawLine(QPointF(side*.035,-.65),QPointF(side*.06,-.28))
        p.drawLine(QPointF(side*.34,.25),QPointF(side*.18,.52))
    plate([(-.095,.31),(0,.35),(.095,.31),(.085,.51),(0,.59),(-.085,.51)],True)
    p.setPen(QPen(QColor('#06070b'),.022))
    for y in (.38,.425,.47):p.drawLine(QPointF(-.06,y),QPointF(.06,y))
    # Floating projection platform; pulse follows the real audio level.
    p.setBrush(Qt.BrushStyle.NoBrush)
    for i in range(5):
        width=.52+i*.08
        p.setPen(QPen(QColor(255,40,55,190-i*25),.007 if i%2 else .013))
        p.drawEllipse(QRectF(-width,.78-i*.015,width*2,.14+i*.025))
    p.setPen(QPen(QColor(255,80,95,int(90+100*amplitude)),.012))
    p.drawLine(QPointF(0,.72),QPointF(0,.86))
    p.restore()
