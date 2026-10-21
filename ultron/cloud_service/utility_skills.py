"""Small exact utilities that need no model or network: coin/dice/random pick, date arithmetic,
age, BMI, tip and bill splitting. Pure functions; randomness can be injected for tests."""
from __future__ import annotations

import random
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

if __package__:
    from .text_normalization import fold_turkish
else:
    from text_normalization import fold_turkish

HOME_TZ = ZoneInfo("Europe/Istanbul")
DAYS = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")
MONTHS = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
_MONTH_KEYS = {"ocak": 1, "subat": 2, "mart": 3, "nisan": 4, "mayis": 5, "haziran": 6, "temmuz": 7,
               "agustos": 8, "eylul": 9, "ekim": 10, "kasim": 11, "aralik": 12}
_MON = "|".join(_MONTH_KEYS)
_DATE = rf"(\d{{1,2}})[./](\d{{1,2}})[./](\d{{4}})|(\d{{1,2}}) ({_MON})(?: (\d{{4}}))?"

_COIN = re.compile(r"^(?:bir\s+)?(?:yazi\s*tura\s*(?:at|cek)?|yazi\s+mi\s+tura\s+mi|para\s+at)\s*\??$")
_DICE = re.compile(r"^(?:(\d{1,2})\s+)?(?:(\d{1,3})\s+yuzlu\s+)?zar\w*\s+(?:at|sal)\w*\s*$|^(?:(\d{1,2})\s+)?zar\s+at\s*$")
_RANDOM = re.compile(r"^(?:bana\s+)?(?:(\d{1,9})\s+(?:ile|ve|-)\s+(\d{1,9})\s+arasinda\s+)?(?:bir\s+)?rastgele\s+(?:bir\s+)?sayi(?:\s+(?:sec|soyle|ver|uret))?\s*$|^(\d{1,9})\s+(?:ile|ve)\s+(\d{1,9})\s+arasinda\s+(?:bir\s+)?(?:sayi|rastgele)\w*(?:\s+(?:sec|soyle|ver))?\s*$")
_PICK = re.compile(r"^(?:sec|karar ver|kura cek|rastgele sec)\s*[:\-]\s*(.+)$")
_ADD = re.compile(r"^(\d{1,5})\s+(gun|hafta|ay|yil)\s+(sonra|once)\s+(?:hangi\s+gun(?:du)?|ne\s+zaman(?:di)?|tarih\w*)\s*\??$")
_BETWEEN = re.compile(rf"^(?:{_DATE})\s+(?:ile|ve)\s+(?:{_DATE})\s+arasi(?:nda)?\s+kac\s+gun\s*\??$")
_WEEKDAY = re.compile(rf"^(?:{_DATE})\s+hangi\s+gun(?:e\s+denk\s*(?:geliyor)?)?\s*\??$")
_AGE = re.compile(rf"^(?:(?:ben\s+)?(\d{{4}})\s+dogumlu(?:yum)?|(?:{_DATE})\s+dogumlu(?:yum)?|dogum\s+tarihim\s+(?:{_DATE}))\s*[,.]?\s*(?:kac\s+yasindayim|yasimi\s+hesapla|yas\s+hesapla)\s*\??$|^(?:kac\s+yasindayim)\s*[:\-]?\s*(\d{{4}})\s*$")
_BMI = re.compile(r"^(?:boyum|boy)\s+(\d{2,3})\s+(?:cm\s+)?(?:kilom|kilo|kg)\s+(\d{2,3}(?:[.,]\d)?)\s*(?:kg\s+)?(?:vki|bmi|vucut\s+kitle\s+indeksi\w*)?\s*(?:hesapla|kac)?\s*\??$|^(?:vki|bmi|vucut\s+kitle\s+indeksi)\s+hesapla\s+(\d{2,3})\s*(?:cm)?\s+(\d{2,3}(?:[.,]\d)?)\s*(?:kg)?\s*$")
_BILL = re.compile(r"^(?:hesap\s+)?(\d{1,6}(?:[.,]\d{1,2})?)\s*(?:tl|lira|₺)?\s*(?:hesab\w*\s+)?(?:(\d{1,2})\s+kisi\w*\s+)?(?:(?:%\s*(\d{1,2})|yuzde\s+(\d{1,2}))\s+bahsis\w*\s*)?(?:(\d{1,2})\s+kisi\w*\s+)?(?:bol\w*|bahsis\w*\s*(?:hesapla)?|ne\s+kadar\s+duser)\s*\??$")


_TIP = re.compile(r"^(?:hesap\s+)?(\d{1,6}(?:[.,]\d{1,2})?)\s*(?:tl|lira|₺)?\s*(?:%\s*(\d{1,2})|yuzde\s+(\d{1,2}))\s+bahsis\w*(?:\s+(?:hesapla|ne\s+kadar))?\s*\??$")


def wants_utility(text: str) -> bool:
    return answer(text, rng=random.Random(0)) is not None


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def _fmt(n: float) -> str:
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _date_from(groups, offset: int, default_year: int | None = None) -> date | None:
    g = groups[offset: offset + 6]
    try:
        if g[0]:
            return date(int(g[2]), int(g[1]), int(g[0]))
        if g[3]:
            return date(int(g[5]) if g[5] else (default_year or datetime.now(HOME_TZ).year), _MONTH_KEYS[g[4]], int(g[3]))
    except (ValueError, KeyError):
        return None
    return None


def _long(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]} {d.year} {DAYS[d.weekday()]}"


def _add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    last = (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)).day
    return date(year, month, min(d.day, last))


def answer(text: str, now: datetime | None = None, rng: random.Random | None = None) -> str | None:
    f = fold_turkish(text).strip()
    if not f or len(f) > 110:
        return None
    rng = rng or random.SystemRandom()
    today = (now or datetime.now(timezone.utc)).astimezone(HOME_TZ).date()

    if _COIN.match(f):
        return "🪙 " + rng.choice(("Yazı", "Tura")) + " geldi."
    m = _DICE.match(f)
    if m:
        count = int(m.group(1) or m.group(3) or 1)
        sides = int(m.group(2) or 6)
        if not 1 <= count <= 10 or not 2 <= sides <= 1000:
            return "En fazla 10 zar, 2–1000 yüzlü olabilir."
        rolls = [rng.randint(1, sides) for _ in range(count)]
        tail = f" (toplam {sum(rolls)})" if count > 1 else ""
        return f"🎲 {', '.join(map(str, rolls))}{tail}"
    m = _RANDOM.match(f)
    if m:
        a, b = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4)) if m.group(3) else ("1", "100")
        lo, hi = sorted((int(a), int(b)))
        return f"🎲 {rng.randint(lo, hi)} ({lo}–{hi} arası)"
    m = _PICK.match(f)
    if m:
        original = text.split(":", 1)[-1] if ":" in text else text.split("-", 1)[-1]
        items = [x.strip() for x in re.split(r"[,;]|\s+veya\s+|\s+yoksa\s+", original, flags=re.I) if x.strip()]
        if len(items) < 2 or len(items) > 12:
            return "Seçmem için 2–12 seçenek yaz. Örn. “seç: pizza, hamburger, lahmacun”."
        return f"🎯 Benim seçimim: {rng.choice(items)}"
    m = _ADD.match(f)
    if m:
        n, unit, direction = int(m.group(1)), m.group(2), m.group(3)
        sign = 1 if direction == "sonra" else -1
        try:
            target = (today + timedelta(days=sign * n * (7 if unit == "hafta" else 1)) if unit in ("gun", "hafta")
                      else _add_months(today, sign * n * (12 if unit == "yil" else 1)))
        except (OverflowError, ValueError):
            return None
        word = "olacak" if sign > 0 else "idi"
        return f"{n} {unit.replace('gun', 'gün').replace('yil', 'yıl')} {direction.replace('once', 'önce')}: {_long(target)} ({word})."
    m = _BETWEEN.match(f)
    if m:
        a, b = _date_from(m.groups(), 0, today.year), _date_from(m.groups(), 6, today.year)
        if a and b:
            days = abs((b - a).days)
            return f"{_long(a)} ile {_long(b)} arasında {days} gün ({days // 7} hafta {days % 7} gün) var."
        return None
    m = _WEEKDAY.match(f)
    if m:
        d = _date_from(m.groups(), 0, today.year)
        return f"{_long(d)}." if d else None
    m = _AGE.match(f)
    if m:
        g = m.groups()
        year = g[0] or g[-1]
        if year and not 1900 <= int(year) <= today.year:
            return None
        born = date(int(year), 1, 1) if year else (_date_from(g, 1, today.year) or _date_from(g, 7, today.year))
        if not born or born > today or today.year - born.year > 120:
            return None
        years = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        if year:
            return f"{year} doğumlusun: bu yıl {today.year - int(year)} yaşına giriyorsun veya girdin (gün/ay bilinmediği için kesin yaş için tam doğum tarihini söyle)."
        anniv = _add_months(born, years * 12)
        months = (today.year - anniv.year) * 12 + today.month - anniv.month - (today.day < anniv.day)
        return f"{years} yaşında ve {months} aylıksın ({(today - born).days} gündür yaşıyorsun)."
    m = _BMI.match(f)
    if m:
        h, w = int(m.group(1) or m.group(3)), _num(m.group(2) or m.group(4))
        if not 100 <= h <= 250 or not 25 <= w <= 300:
            return None
        bmi = w / (h / 100) ** 2
        band = "zayıf" if bmi < 18.5 else "normal kilolu" if bmi < 25 else "fazla kilolu" if bmi < 30 else "obez aralığında"
        return f"Vücut kitle indeksin {bmi:.1f} — genel sınıflamada {band}. Bu yalnızca bir göstergedir, tıbbi değerlendirme yerine geçmez."
    m = _TIP.match(f)
    if m:
        total, tip = _num(m.group(1)), int(m.group(2) or m.group(3))
        if total <= 0 or tip > 50:
            return None
        return f"Hesap {_fmt(total)} TL, %{tip} bahşiş {_fmt(total * tip / 100)} TL; toplam {_fmt(total * (1 + tip / 100))} TL."
    m = _BILL.match(f)
    if m:
        total = _num(m.group(1))
        people = int(m.group(2) or m.group(5) or 1)
        tip = int(m.group(3) or m.group(4) or 0)
        if total <= 0 or not 1 <= people <= 50 or tip > 50:
            return None
        if people == 1 and not tip:
            return None
        grand = total * (1 + tip / 100)
        parts = [f"Hesap {_fmt(total)} TL"] + ([f"%{tip} bahşişle {_fmt(grand)} TL"] if tip else [])
        if people > 1:
            parts.append(f"{people} kişiye kişi başı {_fmt(grand / people)} TL")
        return ", ".join(parts) + "."
    return None
