"""A toolbox of exact, offline calculators and converters (no model, no network, no database).

Money: loan instalment, compound interest, VAT, discount, percentage change, fuel cost, bill maths.
Numbers: lists (sum/average/median), primes, factorial, gcd/lcm, Fibonacci, number words, Roman numerals, bases.
Text: case, reverse, counts, palindrome, Base64, Morse.  Colour: hex ↔ rgb.
Life: bedtime for a wake-up time, week/day of year, business days, next public holiday, zodiac signs,
running pace, daily calorie estimate, recipe scaling, kitchen conversions, time zones.

Every pattern is anchored and requires a keyword so ordinary chat is never intercepted. Results state their
assumptions; health figures are estimates, not advice.
"""
from __future__ import annotations

import base64
import math
import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

if __package__:
    from .text_normalization import fold_turkish
else:
    from text_normalization import fold_turkish

HOME_TZ = ZoneInfo("Europe/Istanbul")
_AMT = r"(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)"
_MONTHS = {"ocak": 1, "subat": 2, "mart": 3, "nisan": 4, "mayis": 5, "haziran": 6, "temmuz": 7, "agustos": 8, "eylul": 9, "ekim": 10, "kasim": 11, "aralik": 12}
_MON = "|".join(_MONTHS)
_TR_MONTHS = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
_TR_DAYS = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")


def num(raw: str) -> float:
    raw = raw.strip()
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", raw):
        return float(raw.replace(".", "").replace(",", "."))
    return float(raw.replace(",", "."))


def money(v: float) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s[:-3] + " ₺" if s.endswith(",00") else s + " ₺"


def n2(v: float, d: int = 2) -> str:
    s = f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s.rstrip("0").rstrip(",") if "," in s else s


# ── money ────────────────────────────────────────────────────────────────────

def _loan(m):
    amount, months, kind, rate = num(m.group(1)), int(m.group(2)), m.group(3), num(m.group(4))
    if not (100 <= amount <= 1e9 and 1 <= months <= 480 and 0 <= rate <= 100):
        return None
    monthly = rate / 100 if kind == "aylik" else (1 + rate / 100) ** (1 / 12) - 1
    pay = amount / months if monthly == 0 else amount * monthly / (1 - (1 + monthly) ** -months)
    total = pay * months
    basis = f"aylık %{n2(monthly * 100, 3)}" + ("" if kind == "aylik" else " (yıllık %" + n2(rate) + " bileşik)")
    return (f"Kredi {money(amount)}, {months} ay, {basis}: aylık taksit {money(pay)}, toplam geri ödeme {money(total)}, toplam faiz {money(total - amount)}. "
            "Vergi ve masraflar (KKDF/BSMV, dosya ücreti) dahil değildir.")


def _compound(m):
    amount, rate, years = num(m.group(1)), num(m.group(2)), int(m.group(3))
    if not (1 <= amount <= 1e12 and 0 <= rate <= 1000 and 1 <= years <= 60):
        return None
    final = amount * (1 + rate / 100) ** years
    return f"{money(amount)} yıllık %{n2(rate)} bileşik faizle {years} yılda {money(final)} olur (getiri {money(final - amount)}). Vergi/stopaj dahil değildir."


def _vat_add(m):
    amount, rate = num(m.group(1)), num(m.group(2) or "20")
    if not (0 < amount <= 1e12 and 0 <= rate <= 100):
        return None
    return f"{money(amount)} + %{n2(rate)} KDV = {money(amount * (1 + rate / 100))} (KDV {money(amount * rate / 100)})."


def _vat_split(m):
    gross, rate = num(m.group(1)), num(m.group(2) or "20")
    if not (0 < gross <= 1e12 and 0 <= rate <= 100):
        return None
    net = gross / (1 + rate / 100)
    return f"{money(gross)} KDV dahil → KDV hariç {money(net)}, KDV (%{n2(rate)}) {money(gross - net)}."


def _discount(m):
    price, pct = num(m.group(1)), num(m.group(2))
    if not (0 < price <= 1e12 and 0 <= pct <= 100):
        return None
    return f"{money(price)} fiyatta %{n2(pct)} indirim: {money(price * pct / 100)} indirim, ödenecek {money(price * (1 - pct / 100))}."


def _pct_change(m):
    a, b = num(m.group(1)), num(m.group(2))
    if a == 0:
        return None
    change = (b - a) / abs(a) * 100
    return f"{n2(a)}'den {n2(b)}'e %{n2(abs(change))} {'artış' if change > 0 else 'azalış' if change < 0 else 'değişim yok'}."


def _fuel(m):
    km, liters, price = num(m.group(1)), num(m.group(2)), num(m.group(3))
    if not (0 < km <= 100000 and 0 < liters <= 5000 and 0 < price <= 10000):
        return None
    return (f"{n2(km)} km için {n2(liters)} litre, {money(price)}/litre: toplam {money(liters * price)}; km başı {money(liters * price / km)}; "
            f"tüketim {n2(liters / km * 100)} lt/100 km.")


# ── numbers ──────────────────────────────────────────────────────────────────

def _list_stat(m):
    kind = m.group(1)
    values = [num(x) for x in re.findall(r"-?\d+(?:[.,]\d+)?", m.group(2))]
    if not 1 <= len(values) <= 200:
        return None
    s = sorted(values)
    mid = len(s) // 2
    result = {"toplam": sum(values), "ortalama": sum(values) / len(values),
              "medyan": s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2,
              "en buyuk": s[-1], "en kucuk": s[0]}[kind]
    return f"{len(values)} sayının {kind.replace('buyuk', 'büyük').replace('kucuk', 'küçük')}: {n2(result)}."


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def _prime(m):
    n = int(m.group(1))
    return f"{n} asal bir sayı." if _is_prime(n) else f"{n} asal değil" + (f" (en küçük böleni {next(i for i in range(2, n + 1) if n % i == 0)})." if n > 1 else ".")


def _factors(m):
    n = int(m.group(1))
    if not 2 <= n <= 10**12:
        return None
    out, d, x = [], 2, n
    while d * d <= x:
        while x % d == 0:
            out.append(d)
            x //= d
        d += 1
    if x > 1:
        out.append(x)
    return f"{n} = " + " × ".join(map(str, out)) if len(out) > 1 else f"{n} asal bir sayı."


def _factorial(m):
    n = int(m.group(1) or m.group(2))
    if not 0 <= n <= 170:
        return "Faktöriyel için 0–170 arası bir sayı yaz."
    v = math.factorial(n)
    return f"{n}! = {v:,}".replace(",", ".") if v < 10**18 else f"{n}! ≈ {v:.4e}".replace(".", ",")


def _gcd_lcm(m):
    a, b, kind = int(m.group(1)), int(m.group(2)), m.group(3)
    if not (1 <= a <= 10**15 and 1 <= b <= 10**15):
        return None
    return f"{a} ve {b} için EBOB = {math.gcd(a, b)}" if kind == "ebob" else f"{a} ve {b} için EKOK = {a * b // math.gcd(a, b)}"


def _fibonacci(m):
    n = int(m.group(1))
    if not 1 <= n <= 300:
        return "Fibonacci için 1–300 arası bir sıra yaz."
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return f"Fibonacci dizisinin {n}. terimi: {b if n > 1 else 1}."


_ONES = ("", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz")
_TENS = ("", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan")
_BIG = ("", "bin", "milyon", "milyar", "trilyon")


def number_words(n: int) -> str:
    if n == 0:
        return "sıfır"
    groups, parts = [], []
    while n:
        groups.append(n % 1000)
        n //= 1000
    for idx in range(len(groups) - 1, -1, -1):
        g = groups[idx]
        if not g:
            continue
        h, t, o = g // 100, g // 10 % 10, g % 10
        words = (("yüz" if h == 1 else _ONES[h] + " yüz") if h else "") + (" " + _TENS[t] if t else "") + (" " + _ONES[o] if o else "")
        words = words.strip()
        if idx == 1 and g == 1:
            words = ""                      # "bin", not "bir bin"
        parts.append((words + " " + _BIG[idx]).strip())
    return " ".join(parts)


def _words(m):
    n = int(m.group(1))
    return f"{n:,}".replace(",", ".") + " = " + number_words(n) if n < 10**15 else None


_ROMAN = (("M", 1000), ("CM", 900), ("D", 500), ("CD", 400), ("C", 100), ("XC", 90), ("L", 50), ("XL", 40), ("X", 10), ("IX", 9), ("V", 5), ("IV", 4), ("I", 1))


def _to_roman(m):
    n = int(m.group(1))
    if not 1 <= n <= 3999:
        return "Roma rakamları 1–3999 arasını yazar."
    out = ""
    for sym, val in _ROMAN:
        while n >= val:
            out += sym
            n -= val
    return f"{m.group(1)} = {out}"


def _from_roman(m):
    s = m.group(1).upper()
    total, prev = 0, 0
    for ch in reversed(s):
        v = dict(_ROMAN_SINGLE)[ch]
        total += -v if v < prev else v
        prev = max(prev, v)
    back = ""
    n = total
    for sym, val in _ROMAN:
        while n >= val:
            back += sym
            n -= val
    return f"{s} = {total}" if back == s else f"“{s}” geçerli bir Roma rakamı değil."


_ROMAN_SINGLE = (("I", 1), ("V", 5), ("X", 10), ("L", 50), ("C", 100), ("D", 500), ("M", 1000))


def _to_base(m):
    n, base = int(m.group(1)), m.group(2)
    if n > 10**18:
        return None
    name, fmt = (("ikilik", bin), ("onaltılık", hex), ("sekizlik", oct))[("ikilik", "onaltilik", "sekizlik").index(base)]
    return f"{n} → {name}: {fmt(n)[2:].upper()}"


def _from_base(m):
    kind, digits = m.group(1), m.group(2)
    base = {"ikilik": 2, "binary": 2, "onaltilik": 16, "hex": 16, "sekizlik": 8}[kind]
    try:
        return f"{digits} ({kind}) = {int(digits, base)}"
    except ValueError:
        return f"“{digits}” {kind} bir sayı değil."


# ── life ─────────────────────────────────────────────────────────────────────

def _bedtime(m):
    hh, mm = int(m.group(1)), int(m.group(2) or 0)
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    wake = datetime.combine(date(2000, 1, 2), time(hh, mm))
    times = [(wake - timedelta(minutes=90 * c + 14)).strftime("%H:%M") for c in (6, 5, 4)]
    return (f"{hh:02d}:{mm:02d}'de uyanmak için yaklaşık {times[0]} (9 saat), {times[1]} (7,5 saat) ya da {times[2]} (6 saat) civarında uyumuş ol. "
            "90 dakikalık uyku döngüleri ve ~14 dk uykuya dalma payı varsayıldı; kişiden kişiye değişir.")


def _week_info(today: date):
    iso = today.isocalendar()
    return f"Bugün yılın {today.timetuple().tm_yday}. günü, ISO {iso[1]}. hafta (yılda {366 if today.year % 4 == 0 and (today.year % 100 or today.year % 400 == 0) else 365} gün)."


_FIXED_HOLIDAYS = ((1, 1, "Yılbaşı"), (4, 23, "Ulusal Egemenlik ve Çocuk Bayramı"), (5, 1, "Emek ve Dayanışma Günü"), (5, 19, "Atatürk'ü Anma, Gençlik ve Spor Bayramı"),
                   (7, 15, "Demokrasi ve Millî Birlik Günü"), (8, 30, "Zafer Bayramı"), (10, 29, "Cumhuriyet Bayramı"))


def _holidays(today: date, upcoming_only: bool):
    items = []
    for year in (today.year, today.year + 1):
        for mo, d, name in _FIXED_HOLIDAYS:
            day = date(year, mo, d)
            if day >= today:
                items.append((day, name))
    if upcoming_only:
        day, name = items[0]
        diff = (day - today).days
        return f"Sıradaki sabit resmî tatil: {name} — {day.day} {_TR_MONTHS[day.month - 1]} {_TR_DAYS[day.weekday()]} ({'bugün' if diff == 0 else str(diff) + ' gün sonra'}). Dinî bayramlar (tarihleri her yıl değişir) bu listede yok."
    return "Sabit resmî tatiller:\n" + "\n".join(f"• {d:%d.%m} — {n}" for d, n in sorted(((date(today.year, mo, d), n) for mo, d, n in _FIXED_HOLIDAYS))) + "\nDinî bayramlar (Ramazan/Kurban) her yıl değiştiği için dahil değil."


def _business_days(m, today: date):
    def parse(day, mon, year):
        return date(int(year) if year else today.year, _MONTHS[mon], int(day))
    try:
        a, b = parse(m.group(1), m.group(2), m.group(3)), parse(m.group(4), m.group(5), m.group(6))
    except ValueError:
        return None
    if a > b:
        a, b = b, a
    if (b - a).days > 3660:
        return None
    holidays = {date(y, mo, d) for y in range(a.year, b.year + 1) for mo, d, _ in _FIXED_HOLIDAYS}
    n = sum(1 for i in range((b - a).days + 1) if (a + timedelta(days=i)).weekday() < 5 and (a + timedelta(days=i)) not in holidays)
    return f"{a:%d.%m.%Y} – {b:%d.%m.%Y} arasında {n} iş günü var (hafta sonları ve sabit resmî tatiller çıkarıldı; dinî bayramlar dahil değil)."


_ZODIAC = ((1, 20, "Oğlak", "toprak"), (2, 19, "Kova", "hava"), (3, 21, "Balık", "su"), (4, 20, "Koç", "ateş"), (5, 21, "Boğa", "toprak"), (6, 21, "İkizler", "hava"),
           (7, 23, "Yengeç", "su"), (8, 23, "Aslan", "ateş"), (9, 23, "Başak", "toprak"), (10, 23, "Terazi", "hava"), (11, 22, "Akrep", "su"), (12, 22, "Yay", "ateş"))


def zodiac(day: int, month: int):
    sign = None
    for (m1, d1, name, element) in _ZODIAC:
        if (month, day) < (m1, d1):
            sign = (name, element)
            break
    return sign or ("Oğlak", "toprak")


def _zodiac(m):
    d, mon = int(m.group(1)), _MONTHS[m.group(2)]
    try:
        date(2000, mon, d)
    except ValueError:
        return None
    name, element = zodiac(d, mon)
    return f"{d} {_TR_MONTHS[mon - 1]} doğumlular {name} burcu ({element} elementi). Eğlence amaçlı bir sınıflamadır."


_CHINESE = ("Maymun", "Horoz", "Köpek", "Domuz", "Fare", "Öküz", "Kaplan", "Tavşan", "Ejderha", "Yılan", "At", "Koyun")


def _chinese(m):
    y = int(m.group(1))
    return f"{y} Çin zodyağında {_CHINESE[y % 12]} yılıdır (Çin yeni yılı Ocak sonu/Şubat başında değiştiği için ocak doğumlular bir önceki hayvana ait olabilir)." if 1900 <= y <= 2100 else None


def _pace(m):
    km, minutes = num(m.group(1)), num(m.group(2))
    if not (0 < km <= 1000 and 0 < minutes <= 6000):
        return None
    pace = minutes / km
    return f"{n2(km)} km / {n2(minutes)} dk → tempo {int(pace)}:{round(pace % 1 * 60):02d} dk/km, hız {n2(km / (minutes / 60))} km/sa."


def _bmr(m):
    age, kg, cm, sex = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
    if not (15 <= age <= 100 and 30 <= kg <= 300 and 120 <= cm <= 230):
        return None
    bmr = 10 * kg + 6.25 * cm - 5 * age + (5 if sex == "erkek" else -161)
    return (f"Tahmini bazal metabolizma {round(bmr)} kcal; az hareketli günlük ihtiyaç ≈ {round(bmr * 1.375)}, orta hareketli ≈ {round(bmr * 1.55)} kcal "
            "(Mifflin–St Jeor). Bu bir tahmindir, tıbbi/diyet tavsiyesi değildir.")


def _recipe(m, original: str):
    a, b = int(m.group(1)), int(m.group(2))
    if not (1 <= a <= 100 and 1 <= b <= 100):
        return None
    tail = original.split(":", 1)[-1]
    factor = b / a

    def scale(mo):
        value = num(mo.group(0))
        return n2(value * factor, 2)
    scaled = re.sub(r"\d+(?:[.,]\d+)?", scale, tail).strip()
    return f"{b} kişilik tarif (×{n2(factor)}): {scaled}"[:600]


_KITCHEN = {"un": 125, "seker": 200, "toz seker": 200, "pudra sekeri": 130, "tereyag": 227, "tereyagi": 227, "sivi yag": 220, "yag": 220, "sut": 240, "su": 240,
            "pirinc": 200, "bulgur": 170, "nisasta": 150, "bal": 340, "tuz": 290}
_UNIT_RATIO = {"bardak": 1.0, "su bardagi": 1.0, "yemek kasigi": 1 / 16, "tatli kasigi": 1 / 32, "cay kasigi": 1 / 48}


def _kitchen(m):
    qty, unit, item = num(m.group(1)), m.group(2), m.group(3)
    grams = qty * _UNIT_RATIO[unit] * _KITCHEN[item]
    return f"{n2(qty)} {unit} {item} ≈ {n2(grams, 0)} gram (ortalama değerlerdir; ürüne ve sıkıştırmaya göre ±10 %)."


_CITIES = {"istanbul": "Europe/Istanbul", "ankara": "Europe/Istanbul", "izmir": "Europe/Istanbul", "londra": "Europe/London", "new york": "America/New_York",
           "los angeles": "America/Los_Angeles", "tokyo": "Asia/Tokyo", "paris": "Europe/Paris", "berlin": "Europe/Berlin", "roma": "Europe/Rome",
           "dubai": "Asia/Dubai", "moskova": "Europe/Moscow", "pekin": "Asia/Shanghai", "sanghay": "Asia/Shanghai", "sydney": "Australia/Sydney",
           "toronto": "America/Toronto", "chicago": "America/Chicago", "madrid": "Europe/Madrid", "amsterdam": "Europe/Amsterdam", "seul": "Asia/Seoul"}
_CITY_RX = "|".join(sorted(_CITIES, key=len, reverse=True))


def _city(name: str) -> str:
    return " ".join(("İ" if w[:1] == "i" else w[:1].upper()) + w[1:] for w in name.split())


def _tz(m, today: date):
    src, hh, mm, dst = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    t = datetime.combine(today, time(hh, mm), tzinfo=ZoneInfo(_CITIES[src])).astimezone(ZoneInfo(_CITIES[dst]))
    day = "" if t.date() == today else (" (ertesi gün)" if t.date() > today else " (önceki gün)")
    return f"{_city(src)} {hh:02d}:{mm:02d} → {_city(dst)} {t:%H:%M}{day}."


# ── calendar facts ───────────────────────────────────────────────────────────

def _is_leap(y: int) -> bool:
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _leap(m, today: date):
    year = int(m.group(1)) if m.group(1) else today.year
    if not 1 <= year <= 9999:
        return None
    return f"{year} artık yıl, Şubat 29 gün çeker." if _is_leap(year) else f"{year} artık yıl değil, Şubat 28 gün çeker."


def _month_days(m, today: date):
    name = m.group(1)
    month = _MONTHS[name] if name else today.month
    year = int(m.group(2)) if m.group(2) else today.year
    if not 1 <= year <= 9999:
        return None
    days = (date(year + (month == 12), month % 12 + 1, 1) - date(year, month, 1)).days
    return f"{_TR_MONTHS[month - 1]} {year} {days} gün çeker."


def _year_progress(today: date):
    total = 366 if _is_leap(today.year) else 365
    doy = today.timetuple().tm_yday
    return f"{today.year} yılının %{n2(doy / total * 100, 1)}'i geçti ({doy}/{total} gün), {total - doy} gün ({n2((total - doy) / 7, 1)} hafta) kaldı."


def _tz_diff(m, today: date):
    a, b = m.group(1), m.group(2)
    noon = datetime.combine(today, time(12, 0))
    offset = lambda city: ZoneInfo(_CITIES[city]).utcoffset(noon)  # noqa: E731
    diff = (offset(b) - offset(a)).total_seconds() / 3600
    if diff == 0:
        return f"{_city(a)} ile {_city(b)} arasında saat farkı yok."
    return f"{_city(b)}, {_city(a)}'dan {n2(abs(diff), 1)} saat {'ileride' if diff > 0 else 'geride'} (bugünün yaz/kış saati dikkate alındı)."


# ── text, colour, codes ──────────────────────────────────────────────────────

def _upper_tr(s: str) -> str:
    return s.replace("i", "İ").replace("ı", "I").upper()


def _lower_tr(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


def _text_tool(kind: str, payload: str) -> str | None:
    payload = payload.strip()
    if not payload or len(payload) > 500:
        return None
    if kind == "buyuk harf yap":
        return _upper_tr(payload)
    if kind == "kucuk harf yap":
        return _lower_tr(payload)
    if kind == "ters cevir":
        return payload[::-1]
    if kind == "kelime say":
        compact = "".join(payload.split())
        return f"{len(payload.split())} kelime, {len(payload)} karakter ({len(compact)} boşluksuz)."
    if kind == "harf say":
        letters = [c for c in payload if c.isalpha()]
        return f"{len(letters)} harf, {len(set(_lower_tr(c) for c in letters))} farklı harf."
    cleaned = re.sub(r"[^a-z0-9]", "", fold_turkish(payload))
    return f"“{payload}” palindrom." if cleaned and cleaned == cleaned[::-1] else f"“{payload}” palindrom değil."


def _base64(kind: str, payload: str) -> str | None:
    payload = payload.strip()
    if not payload or len(payload) > 600:
        return None
    if kind == "kodla":
        return base64.b64encode(payload.encode()).decode()
    try:
        return base64.b64decode(payload.encode(), validate=True).decode("utf-8")
    except Exception:
        return "Bu geçerli bir Base64 metni değil."


_MORSE = {"a": ".-", "b": "-...", "c": "-.-.", "d": "-..", "e": ".", "f": "..-.", "g": "--.", "h": "....", "i": "..", "j": ".---", "k": "-.-", "l": ".-..", "m": "--",
          "n": "-.", "o": "---", "p": ".--.", "q": "--.-", "r": ".-.", "s": "...", "t": "-", "u": "..-", "v": "...-", "w": ".--", "x": "-..-", "y": "-.--", "z": "--..",
          "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----."}


def _morse(payload: str) -> str | None:
    payload = fold_turkish(payload).strip()
    if not payload or len(payload) > 80:
        return None
    return " ".join("/" if ch == " " else _MORSE.get(ch, "?") for ch in payload)


def _hex_rgb(m):
    h = m.group(1)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"#{h.upper()} = rgb({r}, {g}, {b})"


def _rgb_hex(m):
    r, g, b = (int(m.group(i)) for i in (1, 2, 3))
    if max(r, g, b) > 255:
        return None
    return f"rgb({r}, {g}, {b}) = #{r:02X}{g:02X}{b:02X}"


# ── dispatcher ───────────────────────────────────────────────────────────────

_RULES = (
    ("loan", re.compile(rf"^kredi\s+(?:taksit\w*\s*)?[:\-]?\s*{_AMT}\s*(?:tl|lira)?\s+(\d{{1,3}})\s*ay\s+(aylik|yillik)\s*%?\s*(\d+(?:[.,]\d+)?)\s*(?:faiz\w*)?\s*$"), _loan),
    ("compound", re.compile(rf"^{_AMT}\s*(?:tl|lira)?\s+yillik\s*%?\s*(\d+(?:[.,]\d+)?)\s*(?:faiz\w*|getiri\w*)\s+(\d{{1,2}})\s*yil\w*\s*(?:getiri\w*|sonra\w*|kazanc\w*)?\s*\??$"), _compound),
    ("vat_add", re.compile(rf"^{_AMT}\s*(?:tl|lira)?\s*(?:ye|ya)?\s*kdv\s+(?:ekle|hesapla)(?:\s*%\s*(\d{{1,2}}))?\s*$"), _vat_add),
    ("vat_split", re.compile(rf"^{_AMT}\s*(?:tl|lira)?\s*kdv\s+dahil\s*(?:kdv\s+)?(?:ayir|cikar|hesapla)?(?:\s*%\s*(\d{{1,2}}))?\s*$"), _vat_split),
    ("discount", re.compile(rf"^{_AMT}\s*(?:tl|lira)?\s*%\s*(\d{{1,3}}(?:[.,]\d+)?)\s*indirim\w*\s*(?:ne\s+kadar|kac\s+tl|hesapla)?\s*\??$"), _discount),
    ("pct_change", re.compile(r"^(-?\d+(?:[.,]\d+)?)\s*'?(?:den|dan|ten|tan)\s*(-?\d+(?:[.,]\d+)?)\s*'?(?:ye|ya|e|a)\s*yuzde\s+kac\s+(?:artis|azalis|degisim|fark)\w*\s*\??$"), _pct_change),
    ("fuel", re.compile(rf"^yakit\s+maliyet\w*\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*km\s+(\d+(?:[.,]\d+)?)\s*(?:litre|lt|l)\s+{_AMT}\s*(?:tl|lira)\s*$"), _fuel),
    ("stat", re.compile(r"^(ortalama|toplam|medyan|en buyuk|en kucuk)\s*[:\-]\s*((?:-?\d+(?:[.,]\d+)?[\s,;]*)+)$"), _list_stat),
    ("prime", re.compile(r"^(\d{1,12})\s+asal\s+mi\s*\??$"), _prime),
    ("factors", re.compile(r"^(\d{2,13})\s+(?:sayisinin\s+)?asal\s+carpan\w*\s*\??$"), _factors),
    ("factorial", re.compile(r"^(?:(\d{1,3})\s+faktoriyel\w*|(\d{1,3})!)\s*\??$"), _factorial),
    ("gcd_lcm", re.compile(r"^(\d{1,15})\s+(?:ile|ve)\s+(\d{1,15})\s+(?:sayisinin\s+)?(ebob|ekok)\w*\s*\??$"), _gcd_lcm),
    ("fibonacci", re.compile(r"^fibonacci\s+(\d{1,3})\s*\??$"), _fibonacci),
    ("words", re.compile(r"^(\d{1,15})\s+yaziyla\s*(?:nasil\s+yazilir)?\s*\??$"), _words),
    ("to_roman", re.compile(r"^(\d{1,4})\s+(?:roma|romen)\s+rakam\w*\s*(?:kac|nedir|ile)?\s*\??$"), _to_roman),
    ("from_roman", re.compile(r"^(?:roma|romen)\s+rakam\w*\s+([ivxlcdm]{1,15})\s*\??$"), _from_roman),
    ("to_base", re.compile(r"^(\d{1,18})\s+(ikilik|onaltilik|sekizlik)\w*\s*(?:kac|cevir|sistemde|tabanda)?\s*\??$"), _to_base),
    ("from_base", re.compile(r"^(ikilik|binary|onaltilik|hex|sekizlik)\s+([0-9a-f]{1,20})\s+(?:kac|ondalik|cevir)\w*\s*\??$"), _from_base),
    ("bedtime", re.compile(r"^(?:sabah\s+)?(\d{1,2})(?:[:.](\d{2}))?\s*'?(?:de|da|te|ta)?\s*uyanmak\s+icin\s+(?:ne\s+zaman|saat\s+kacta)\s+yatmaliyim\s*\??$"), _bedtime),
    ("zodiac", re.compile(rf"^(?:burcum\s+ne\s+)?(\d{{1,2}})\s+({_MON})\s+(?:dogumlu\s+)?burc\w*\s*(?:ne|hangisi)?\s*\??$|^burcum\s+ne\s+(\d{{1,2}})\s+({_MON})\s*\??$"), None),
    ("chinese", re.compile(r"^(\d{4})\s+cin\s+(?:burcu|zodyagi)\w*\s*\??$"), _chinese),
    ("pace", re.compile(r"^(\d+(?:[.,]\d+)?)\s*km\s+(\d+(?:[.,]\d+)?)\s*(?:dakika|dk)\s+(?:tempo|hiz)\w*\s*\??$"), _pace),
    ("bmr", re.compile(r"^gunluk\s+kalori\s+ihtiyac\w*\s*[:\-]?\s*(\d{1,3})\s*yas\w*\s+(\d{2,3})\s*kilo\w*\s+(\d{3})\s*(?:cm\s+|boy\w*\s+)?(erkek|kadin)\s*$"), _bmr),
    ("kitchen", re.compile(r"^(\d+(?:[.,]\d+)?)\s*(su bardagi|bardak|yemek kasigi|tatli kasigi|cay kasigi)\s+(toz seker|pudra sekeri|sivi yag|tereyagi|tereyag|un|seker|yag|sut|su|pirinc|bulgur|nisasta|bal|tuz)\s+kac\s+gram\s*\??$"), _kitchen),
    ("tz", re.compile(rf"^({_CITY_RX})\s+(\d{{1,2}})[:.](\d{{2}})\s+(?:saati\s+)?({_CITY_RX})\s+(?:saati\s+)?(?:kac|ne)\w*\s*\??$"), None),
    ("business", re.compile(rf"^(\d{{1,2}})\s+({_MON})(?:\s+(\d{{4}}))?\s+(?:ile|ve)\s+(\d{{1,2}})\s+({_MON})(?:\s+(\d{{4}}))?\s+arasi(?:nda)?\s+kac\s+is\s+gunu\s*\??$"), None),
)
_TEXT = re.compile(r"^(buyuk harf yap|kucuk harf yap|ters cevir|kelime say|harf say|palindrom mu)\s*[:\-]\s*(.+)$", re.S)
_B64 = re.compile(r"^base64\s+(kodla|coz)\s*[:\-]\s*(.+)$", re.S)
_MORSE_RX = re.compile(r"^mors(?:\s+(?:cevir|kodu))?\s*[:\-]\s*(.+)$", re.S)
_HEX_RGB = re.compile(r"^#?([0-9a-f]{6})\s+(?:rgb|renk)\w*(?:\s+kac)?\s*\??$")
_RGB_HEX = re.compile(r"^rgb\s*\(?\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*\)?\s*(?:hex|kac)?\s*\??$")
_RECIPE = re.compile(r"^tarif\s+(\d{1,3})\s*kisilik\w*\s*(?:dan|den|ten|tan)?\s*(\d{1,3})\s*kisilig\w*\s*[:\-]\s*(.+)$", re.S)
_WEEK = re.compile(r"^(?:bugun\s+)?yilin\s+kacinci\s+(?:gunu|haftasi)\w*\s*\??$|^hafta\s+kac\s*\??$|^bu\s+hafta\s+kacinci\s+hafta\s*\??$")
_LEAP_RX = re.compile(r"^(?:(\d{4})|bu\s+yil)\s+(?:artik\s+yil\s+mi|subat\s+kac\s+cekiyor)\s*\??$")
_MONTH_DAYS_RX = re.compile(rf"^(?:({_MON})(?:\s+ayi)?(?:\s+(\d{{4}}))?\s+kac\s+(?:gun(?:\s+cek\w*)?|cek\w*)|bu\s+ay\s+kac\s+gun\s+var)\s*\??$")
_YEAR_PROGRESS_RX = re.compile(r"^yilin\s+(?:yuzde\s+kaci\s+gecti|ne\s+kadari\s+gecti)\s*\??$|^yil\s+sonuna\s+kac\s+(?:gun|hafta)\s+(?:kaldi|var)\s*\??$|^yilin\s+bitmesine\s+kac\s+gun\s+(?:kaldi|var)\s*\??$")
_TZDIFF_RX = re.compile(rf"^({_CITY_RX})\s+(?:ile|ve)\s+({_CITY_RX})\s+arasinda\s+saat\s+farki\s+(?:kac|ne\s+kadar)\s*\??$")
_HOLIDAY = re.compile(r"^(?:(?:siradaki|sonraki|bir\s+sonraki)\s+resmi\s+tatil\w*(?:\s+ne\s+zaman|\s+ne)?|resmi\s+tatiller\w*(?:\s+neler)?)\s*\??$")


def answer(text: str, now: datetime | None = None) -> str | None:
    raw = str(text or "").strip()
    if not raw or len(raw) > 700:
        return None
    f = fold_turkish(raw).strip()
    today = (now or datetime.now(timezone.utc)).astimezone(HOME_TZ).date()
    try:
        m = _TEXT.match(f)
        if m:
            return _text_tool(m.group(1), raw.split(":", 1)[-1] if ":" in raw else raw.split("-", 1)[-1] if "-" in raw else m.group(2))
        m = _B64.match(f)
        if m:
            return _base64(m.group(1), raw.split(":", 1)[-1] if ":" in raw else raw.split("-", 1)[-1])
        m = _MORSE_RX.match(f)
        if m:
            return _morse(raw.split(":", 1)[-1] if ":" in raw else raw.split("-", 1)[-1])
        m = _RECIPE.match(f)
        if m:
            return _recipe(m, raw)
        if len(f) > 160:
            return None
        if _WEEK.match(f):
            return _week_info(today)
        m = _LEAP_RX.match(f)
        if m:
            return _leap(m, today)
        m = _MONTH_DAYS_RX.match(f)
        if m:
            return _month_days(m, today)
        if _YEAR_PROGRESS_RX.match(f):
            return _year_progress(today)
        m = _TZDIFF_RX.match(f)
        if m:
            return _tz_diff(m, today)
        m = _HOLIDAY.match(f)
        if m:
            return _holidays(today, "siradaki" in f or "sonraki" in f)
        for name, rx, fn in _RULES:
            m = rx.match(f)
            if not m:
                continue
            if name == "zodiac":
                g = m.groups()
                day, mon = (g[0], g[1]) if g[0] else (g[2], g[3])
                return _zodiac(type("M", (), {"group": lambda self, i, d=day, mo=mon: d if i == 1 else mo})())
            if name == "tz":
                return _tz(m, today)
            if name == "business":
                return _business_days(m, today)
            return fn(m)
        m = _HEX_RGB.match(f)
        if m:
            return _hex_rgb(m)
        m = _RGB_HEX.match(f)
        if m:
            return _rgb_hex(m)
    except (ValueError, OverflowError, ZeroDivisionError, KeyError):
        return None
    return None


def wants_calc(text: str) -> bool:
    return answer(text) is not None
