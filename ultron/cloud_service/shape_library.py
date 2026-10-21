"""Deterministic 3D shape library for the hologram: ask for a heart, star, DNA, rocket … and get a
validated primitive assembly instantly, offline, without a model call.

Every generator returns parts in the same schema as `scene_design.validate` (box, sphere, cylinder, cone,
torus, circle, plane, triangle; Y up; flat shapes face +Z). A count in the request ("8 köşeli yıldız",
"12 basamaklı merdiven") parameterises the shapes that support it. Unknown requests return None so the
caller can fall back to the language model or the Poly Haven catalogue.
"""
from __future__ import annotations

import math
import re

if __package__:
    from .text_normalization import fold_turkish
else:
    from text_normalization import fold_turkish

MAX_PARTS = 24
TAU = math.tau


def _c(v, lo, hi):
    return round(max(lo, min(hi, float(v))), 3)


def part(name, shape, size, pos=(0, 0, 0), rot=(0, 0, 0)):
    return {"name": name, "shape": shape,
            "size": [_c(s, .05, 6) for s in size],
            "position": [_c(p, -6, 6) for p in pos],
            "rotation": [_c(r, -6.28, 6.28) for r in rot]}


def _ring(n, radius, y=0.0):
    for i in range(n):
        a = TAU * i / n
        yield a, radius * math.cos(a), y, radius * math.sin(a)


# ── generators: each returns a list of parts (≤ MAX_PARTS) ────────────────

def cube(n):
    return [part("küp", "box", (2, 2, 2))]


def sphere(n):
    return [part("küre", "sphere", (2.4, 2.4, 2.4))]


def cylinder(n):
    return [part("silindir", "cylinder", (1.6, 2.4, 1.6))]


def cone(n):
    return [part("koni", "cone", (2, 2.6, 2))]


def ring(n):
    return [part("halka", "torus", (2.6, 2.6, .9), rot=(math.pi / 2, 0, 0))]


def pyramid(n):
    levels = max(2, min(n or 5, 10))
    out = []
    for i in range(levels):
        width = 3.4 * (1 - i / levels) + .3
        out.append(part(f"kat {i + 1}", "box", (width, .5, width), (0, -1.6 + i * .5, 0)))
    return out


def star(n):
    points = max(3, min(n or 5, 16))
    out = [part("merkez", "circle", (.9, .9, .1), (0, 0, 0))]
    for i in range(points):
        a = TAU * i / points
        r = 1.15
        out.append(part(f"uç {i + 1}", "triangle", (.9, 1.5, .25), (-math.sin(a) * r, math.cos(a) * r, 0), (0, 0, a)))
    return out


def heart(n):
    # The classic heart: a square turned 45° with a round lobe on each upper side.
    s = 2.2
    off = s / 2 * math.sqrt(2) / 2
    shift = -.5
    return [part("gövde", "box", (s, s, 2.0), (0, shift, 0), (0, 0, math.pi / 4)),
            part("sol lob", "sphere", (s, s, 2.0), (-off, off + shift, 0)),
            part("sağ lob", "sphere", (s, s, 2.0), (off, off + shift, 0))]


def helix(n):
    turns = max(1, min(n or 3, 4))
    steps = 8
    out = []
    for strand, phase in (("A", 0), ("B", math.pi)):
        for i in range(steps):
            t = i / (steps - 1)
            a = phase + turns * TAU * t
            out.append(part(f"zincir {strand}{i + 1}", "sphere", (.35, .35, .35), (math.cos(a) * 1.0, -2.4 + 4.8 * t, math.sin(a) * 1.0)))
    for i in range(0, steps, 2):
        t = i / (steps - 1)
        a = turns * TAU * t
        out.append(part(f"basamak {i // 2 + 1}", "cylinder", (.08, 2.0, .08), (0, -2.4 + 4.8 * t, 0), (math.pi / 2, a, 0)))
    return out[:MAX_PARTS]


def spiral(n):
    steps = max(6, min((n or 3) * 6, MAX_PARTS))
    out = []
    for i in range(steps):
        t = i / (steps - 1)
        a = t * TAU * 2.5
        r = .3 + 2.4 * t
        out.append(part(f"nokta {i + 1}", "sphere", (.3, .3, .3), (math.cos(a) * r, math.sin(a) * r, 0)))
    return out


def house(n):
    return [part("gövde", "box", (3, 2, 2.4), (0, -.5, 0)),
            part("çatı", "cone", (3.6, 1.6, 3.6), (0, 1.3, 0), (0, math.pi / 4, 0)),
            part("kapı", "plane", (.7, 1.2, .1), (0, -1.0, 1.21)),
            part("pencere", "plane", (.6, .6, .1), (-.9, -.2, 1.21)),
            part("baca", "box", (.4, .9, .4), (.9, 1.6, -.3))]


def tree(n):
    return [part("gövde", "cylinder", (.5, 2.0, .5), (0, -1.5, 0)),
            part("yaprak alt", "cone", (3.0, 1.6, 3.0), (0, -.2, 0)),
            part("yaprak orta", "cone", (2.4, 1.4, 2.4), (0, .8, 0)),
            part("yaprak üst", "cone", (1.7, 1.2, 1.7), (0, 1.7, 0))]


def snowman(n):
    return [part("alt", "sphere", (2.2, 2.2, 2.2), (0, -1.6, 0)),
            part("orta", "sphere", (1.6, 1.6, 1.6), (0, .1, 0)),
            part("baş", "sphere", (1.1, 1.1, 1.1), (0, 1.35, 0)),
            part("havuç burun", "cone", (.18, .7, .18), (0, 1.35, .65), (math.pi / 2, 0, 0)),
            part("şapka", "cylinder", (.8, .5, .8), (0, 2.0, 0))]


def robot(n):
    return [part("gövde", "box", (1.6, 2.0, 1.0), (0, 0, 0)),
            part("baş", "box", (1.1, .9, 1.0), (0, 1.5, 0)),
            part("anten", "cylinder", (.08, .6, .08), (0, 2.25, 0)),
            part("sol kol", "cylinder", (.35, 1.8, .35), (-1.15, .1, 0)),
            part("sağ kol", "cylinder", (.35, 1.8, .35), (1.15, .1, 0)),
            part("sol bacak", "cylinder", (.45, 1.6, .45), (-.45, -1.8, 0)),
            part("sağ bacak", "cylinder", (.45, 1.6, .45), (.45, -1.8, 0)),
            part("sol göz", "sphere", (.2, .2, .2), (-.28, 1.55, .52)),
            part("sağ göz", "sphere", (.2, .2, .2), (.28, 1.55, .52))]


def rocket(n):
    out = [part("gövde", "cylinder", (1.0, 3.0, 1.0), (0, 0, 0)),
           part("burun", "cone", (1.0, 1.2, 1.0), (0, 2.1, 0)),
           part("pencere", "circle", (.45, .45, .05), (0, .6, .51))]
    for i in range(3):
        a = TAU * i / 3
        out.append(part(f"kanat {i + 1}", "triangle", (.9, 1.1, .1), (math.cos(a) * .75, -1.3, math.sin(a) * .75), (0, -a + math.pi / 2, 0)))
    out.append(part("alev", "cone", (.6, 1.0, .6), (0, -2.2, 0), (0, 0, math.pi)))
    return out


def car(n):
    out = [part("gövde", "box", (3.2, .8, 1.5), (0, -.4, 0)),
           part("kabin", "box", (1.7, .8, 1.3), (-.1, .4, 0))]
    for sx in (-1.1, 1.1):
        for sz in (-.8, .8):
            out.append(part("tekerlek", "cylinder", (.7, .3, .7), (sx, -.85, sz), (math.pi / 2, 0, 0)))
    return out


def table(n):
    out = [part("tabla", "box", (3.2, .2, 2.0), (0, .6, 0))]
    for sx in (-1.4, 1.4):
        for sz in (-.8, .8):
            out.append(part("ayak", "cylinder", (.2, 1.6, .2), (sx, -.3, sz)))
    return out


def chair(n):
    out = [part("oturak", "box", (1.6, .2, 1.6), (0, -.2, 0)),
           part("arkalık", "box", (1.6, 1.6, .2), (0, .7, -.7))]
    for sx in (-.65, .65):
        for sz in (-.65, .65):
            out.append(part("ayak", "cylinder", (.15, 1.2, .15), (sx, -.9, sz)))
    return out


def stairs(n):
    steps = max(3, min(n or 8, 20))
    return [part(f"basamak {i + 1}", "box", (2.4, .25, 6 / steps * .9 + .1), (0, -2.4 + i * (4.8 / steps), -2.4 + i * (4.8 / steps)))
            for i in range(steps)]


def spiral_stairs(n):
    steps = max(6, min(n or 12, MAX_PARTS))
    return [part(f"basamak {i + 1}", "box", (1.5, .15, .5), (math.cos(i * .55) * .8, -2.4 + i * 4.8 / steps, math.sin(i * .55) * .8), (0, -i * .55, 0))
            for i in range(steps)]


def atom(n):
    out = [part("çekirdek", "sphere", (.9, .9, .9))]
    for k in range(3):
        tilt = math.pi * k / 3                      # three orbit planes tilted around the Y axis
        for i in range(6):
            a = TAU * i / 6 + k
            x, y = 1.9 * math.cos(a), 1.9 * math.sin(a)
            pos = (x * math.cos(tilt), y, x * math.sin(tilt))
            out.append(part(f"yörünge {k + 1}.{i + 1}", "sphere", (.16, .16, .16), pos))
        a = TAU * k / 3
        x, y = 1.9 * math.cos(a), 1.9 * math.sin(a)
        out.append(part(f"elektron {k + 1}", "sphere", (.32, .32, .32), (x * math.cos(tilt), y, x * math.sin(tilt))))
    return out


def solar_system(n):
    planets = max(3, min(n or 6, 8))
    out = [part("güneş", "sphere", (1.5, 1.5, 1.5))]
    for i in range(planets):
        r = 1.3 + i * .55
        a = i * 1.7
        size = .28 + .05 * (i % 4)
        out.append(part(f"gezegen {i + 1}", "sphere", (size, size, size), (r * math.cos(a), 0, r * math.sin(a))))
    return out[:MAX_PARTS]


def saturn(n):
    return [part("gezegen", "sphere", (2.0, 2.0, 2.0)),
            part("halka", "torus", (4.2, 4.2, .12), rot=(math.pi / 2 + .35, 0, 0))]


def earth(n):
    return [part("dünya", "sphere", (3.0, 3.0, 3.0)),
            part("eksen", "cylinder", (.06, 4.2, .06), rot=(0, 0, .4)),
            part("ay", "sphere", (.6, .6, .6), (2.6, .9, 0)),
            part("kutup", "circle", (.8, .8, .02), (-.6, 1.45, 0), (-.4, 0, 0))]


def plane_(n):
    return [part("gövde", "cylinder", (.6, 3.6, .6), (0, 0, 0), (0, 0, math.pi / 2)),
            part("burun", "cone", (.6, .9, .6), (2.2, 0, 0), (0, 0, -math.pi / 2)),
            part("kanat", "box", (1.0, .08, 4.0), (.2, -.1, 0)),
            part("kuyruk", "box", (.6, .08, 1.5), (-1.6, 0, 0)),
            part("dikey kuyruk", "box", (.7, .8, .08), (-1.6, .4, 0))]


def flower(n):
    petals = max(4, min(n or 8, 12))
    out = [part("merkez", "sphere", (.7, .7, .7), (0, 1.2, 0)),
           part("sap", "cylinder", (.12, 2.8, .12), (0, -.3, 0))]
    for i in range(petals):
        a = TAU * i / petals
        out.append(part(f"yaprak {i + 1}", "sphere", (.55, .55, .25), (math.cos(a) * .85, 1.2 + math.sin(a) * .85, 0), (0, 0, a)))
    out.append(part("yaprak sap", "triangle", (.9, .5, .05), (.6, -.9, 0), (0, 0, -.9)))
    return out


def arrow(n):
    return [part("sap", "cylinder", (.35, 2.6, .35), (0, -.6, 0)),
            part("uç", "cone", (1.1, 1.3, 1.1), (0, 1.3, 0))]


def castle(n):
    out = [part("duvar", "box", (4.0, 1.6, 1.2), (0, -.7, 0)),
           part("kapı", "plane", (.8, 1.1, .1), (0, -.9, .61))]
    for sx in (-2.0, 2.0):
        out.append(part("kule", "cylinder", (.9, 3.0, .9), (sx, .0, 0)))
        out.append(part("kule çatı", "cone", (1.1, .9, 1.1), (sx, 1.9, 0)))
    return out


def mushroom(n):
    return [part("sap", "cylinder", (.7, 1.4, .7), (0, -1, 0)),
            part("şapka", "sphere", (2.6, 1.6, 2.6), (0, .2, 0))]


def cup(n):
    return [part("fincan", "cylinder", (1.6, 1.8, 1.6), (0, 0, 0)),
            part("kulp", "torus", (1.0, 1.0, .2), (1.0, 0, 0)),
            part("tabak", "cylinder", (2.4, .1, 2.4), (0, -.95, 0))]


def laptop(n):
    return [part("taban", "box", (3.0, .15, 2.0), (0, -.9, 0)),
            part("ekran", "box", (3.0, 1.9, .1), (0, .1, -1.0), (-.25, 0, 0)),
            part("ekran yüzü", "plane", (2.7, 1.6, .02), (0, .1, -.93), (-.25, 0, 0))]


def phone(n):
    return [part("gövde", "box", (1.2, 2.4, .12)), part("ekran", "plane", (1.05, 2.1, .01), (0, 0, .07))]


def book(n):
    return [part("kapak", "box", (1.8, 2.4, .5)), part("sayfalar", "box", (1.6, 2.2, .42), (.06, 0, 0))]


def candle(n):
    return [part("mum", "cylinder", (.6, 2.0, .6), (0, -.4, 0)),
            part("alev", "cone", (.3, .6, .3), (0, 1.0, 0)),
            part("fitil", "cylinder", (.04, .25, .04), (0, .7, 0))]


def lamp(n):
    return [part("taban", "cylinder", (1.3, .15, 1.3), (0, -2.2, 0)),
            part("gövde", "cylinder", (.12, 3.0, .12), (0, -.7, 0)),
            part("abajur", "cone", (1.8, 1.2, 1.8), (0, 1.3, 0), (0, 0, math.pi))]


def bridge(n):
    out = [part("yol", "box", (6, .2, 1.0), (0, -.6, 0))]
    for sx in (-2.2, 2.2):
        out.append(part("kule", "box", (.35, 3.0, .35), (sx, .8, 0)))
    for i in range(7):
        x = -2.2 + i * .733
        h = .45 + 1.2 * ((x / 2.2) ** 2)
        out.append(part(f"halat {i + 1}", "cylinder", (.04, max(.1, 2.0 - h), .04), (x, .1 + (2.0 - h) / 2 - .6 + .45, 0)))
    return out


def tower(n):
    levels = max(3, min(n or 6, 12))
    return [part(f"kat {i + 1}", "box", (2.2 - i * .12, 4.6 / levels, 2.2 - i * .12), (0, -2.3 + (i + .5) * 4.6 / levels, 0)) for i in range(levels)]


def eiffel(n):
    return [part("alt", "box", (3.4, .3, 3.4), (0, -2.5, 0)),
            part("ayaklar", "cone", (3.0, 2.6, 3.0), (0, -1.1, 0)),
            part("orta", "box", (1.5, .25, 1.5), (0, 0, 0)),
            part("gövde", "cone", (1.4, 2.0, 1.4), (0, 1.1, 0)),
            part("anten", "cylinder", (.06, 1.0, .06), (0, 2.6, 0))]


def ship(n):
    return [part("gövde", "box", (3.4, .8, 1.2), (0, -.8, 0)),
            part("kabin", "box", (1.0, .7, .9), (.4, -.05, 0)),
            part("baca", "cylinder", (.3, .6, .3), (.4, .5, 0)),
            part("direk", "cylinder", (.06, 1.8, .06), (-1.0, .2, 0)),
            part("yelken", "triangle", (1.2, 1.5, .02), (-.6, .3, 0))]


def gear(n):
    teeth = max(6, min(n or 10, 16))
    out = [part("gövde", "cylinder", (2.4, .5, 2.4), rot=(math.pi / 2, 0, 0)),
           part("delik", "torus", (.9, .9, .2), rot=(0, 0, 0))]
    for i in range(teeth):
        a = TAU * i / teeth
        out.append(part(f"diş {i + 1}", "box", (.4, .5, .4), (math.cos(a) * 1.35, math.sin(a) * 1.35, 0), (0, 0, a)))
    return out[:MAX_PARTS]


def clock(n):
    return [part("kadran", "circle", (3.2, 3.2, .05)), part("çerçeve", "torus", (3.2, 3.2, .15)),
            part("akrep", "box", (.12, .9, .04), (0, .45, .05)),
            part("yelkovan", "box", (.08, 1.3, .04), (.5, .3, .06), (0, 0, -1.0))]


def diamond(n):
    return [part("üst", "cone", (2.2, 1.2, 2.2), (0, .6, 0)), part("alt", "cone", (2.2, 1.8, 2.2), (0, -.9, 0), (0, 0, math.pi))]


def hourglass(n):
    return [part("üst", "cone", (1.8, 1.8, 1.8), (0, 1.0, 0), (0, 0, math.pi)), part("alt", "cone", (1.8, 1.8, 1.8), (0, -1.0, 0)),
            part("üst kapak", "cylinder", (2.1, .15, 2.1), (0, 2.0, 0)), part("alt kapak", "cylinder", (2.1, .15, 2.1), (0, -2.0, 0))]


def pawn(n):
    return [part("taban", "cylinder", (1.8, .3, 1.8), (0, -1.6, 0)), part("gövde", "cone", (1.4, 2.2, 1.4), (0, -.3, 0)),
            part("boyun", "torus", (1.0, 1.0, .2), (0, .8, 0), (math.pi / 2, 0, 0)), part("baş", "sphere", (1.0, 1.0, 1.0), (0, 1.3, 0))]


def dna_alias(n):
    return helix(n)


# keyword (folded, whole-word prefix match) → (generator, count word hint)
CATALOG = (
    (("kup", "kutu", "cube", "box"), cube), (("kure", "top", "sphere", "ball"), sphere),
    (("silindir", "cylinder"), cylinder), (("koni", "cone"), cone), (("halka", "simit", "torus", "yuzuk", "ring"), ring),
    (("piramit", "pyramid"), pyramid), (("yildiz", "star"), star), (("kalp", "heart"), heart),
    (("dna", "helis", "helix"), helix), (("spiral", "girdap", "galaksi", "galaxy"), spiral),
    (("ev", "house", "kulube"), house), (("agac", "tree"), tree), (("kardan adam", "snowman"), snowman),
    (("robot",), robot), (("roket", "rocket", "uzay araci"), rocket), (("araba", "otomobil", "car", "arac"), car),
    (("masa", "table"), table), (("sandalye", "chair", "koltuk"), chair), (("sarmal merdiven", "spiral stairs"), spiral_stairs),
    (("merdiven", "stairs"), stairs), (("atom",), atom), (("gunes sistemi", "solar system", "gezegenler"), solar_system),
    (("saturn", "satur"), saturn), (("dunya", "earth", "globe"), earth), (("ucak", "airplane", "plane"), plane_),
    (("cicek", "flower", "papatya"), flower), (("ok", "arrow"), arrow), (("kale", "castle"), castle),
    (("mantar", "mushroom"), mushroom), (("fincan", "kupa", "bardak", "cup", "mug"), cup), (("laptop", "bilgisayar", "notebook"), laptop),
    (("telefon", "phone"), phone), (("kitap", "book"), book), (("mum", "candle"), candle), (("lamba", "lamp", "abajur"), lamp),
    (("kopru", "bridge"), bridge), (("kule", "tower", "gokdelen", "skyscraper"), tower), (("eyfel", "eiffel"), eiffel),
    (("gemi", "tekne", "ship", "boat"), ship), (("disli", "gear", "cark"), gear), (("saat", "clock"), clock),
    (("elmas", "diamond", "mucevher"), diamond), (("kum saati", "hourglass"), hourglass), (("piyon", "pawn", "satranc"), pawn),
)

_COUNT = re.compile(r"\b(\d{1,2})\b")
_CASE = "(?:i|in|e|de|den|u|un|ler|lar|im)?"


def _pattern(word: str) -> re.Pattern:
    # Short words must match as a whole word (plus a case suffix) so "ev" does not match "evet".
    body = re.escape(word)
    return re.compile(rf"(?<![a-z]){body}{_CASE}(?![a-z])" if len(word) <= 4 else rf"(?<![a-z]){body}")


_COMPILED = tuple((tuple(_pattern(w) for w in words), gen) for words, gen in CATALOG)


def _count(folded: str) -> int | None:
    m = _COUNT.search(folded)
    return int(m.group(1)) if m else None


def _matches(folded: str):
    found = []                                   # (start, end, generator)
    for patterns, gen in _COMPILED:
        spans = [m.span() for rx in patterns if (m := rx.search(folded))]
        if spans and gen not in [g for _, _, g in found]:
            found.append((*max(spans, key=lambda s: s[1] - s[0]), gen))
    # "kum saati" must not also build a clock, "sarmal merdiven" must not also build straight stairs
    kept = [(s, e, g) for s, e, g in found
            if not any((s2 <= s and e <= e2 and (e2 - s2) > (e - s)) for s2, e2, g2 in found if g2 is not g)]
    return [g for _, _, g in sorted(kept, key=lambda x: x[0])]


def _scaled(parts, factor, dx):
    out = []
    for p in parts:
        out.append(part(p["name"], p["shape"], [s * factor for s in p["size"]],
                        [p["position"][0] * factor + dx, p["position"][1] * factor, p["position"][2] * factor], p["rotation"]))
    return out


def generate(description: str) -> dict | None:
    """A validated design for a known shape request, else None."""
    folded = fold_turkish(description or "").strip()
    if not folded:
        return None
    gens = _matches(folded)
    if not gens:
        return None
    n = _count(folded)
    gens = gens[:3]
    if len(gens) == 1:
        parts = gens[0](n)
    else:
        parts, slot = [], 5.0 / len(gens)
        for i, g in enumerate(gens):
            piece = g(None)
            factor = .55 if len(gens) == 2 else .4
            scaled = _scaled(piece, factor, -2.5 + slot * (i + .5))
            if len(parts) + len(scaled) > MAX_PARTS:
                break
            parts.extend(scaled)
    parts = parts[:MAX_PARTS]
    if not parts:
        return None
    name = " ".join(description.split())[:90] or "şekil"
    return {"name": name, "parts": parts}
