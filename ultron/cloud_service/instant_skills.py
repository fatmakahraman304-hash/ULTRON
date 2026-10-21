"""GÖLGE instant skills: exact, JARVIS-style answers without a model call.

Each skill answers only an unambiguous request (clock, arithmetic, unit
conversion, countdown, weather, exchange rate, status report). Anything else
returns None and continues to the language model. Live data comes from
public, keyless sources; on failure the skill says so instead of guessing.
"""
from __future__ import annotations

import ast
import math
import operator
import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Awaitable, Callable
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

if __package__:
    from .text_normalization import fold_turkish
    from . import calendar_feed, reminders, memory_skills, phone_skills, proactive, plan_skills, smart_home, knowledge_skills, missions, alert_skills, list_skills, expense_skills, birthday_skills, habit_skills
else:
    from text_normalization import fold_turkish
    import calendar_feed
    import reminders
    import memory_skills
    import phone_skills
    import proactive
    import plan_skills
    import smart_home
    import knowledge_skills
    import missions
    import alert_skills
    import list_skills
    import expense_skills
    import birthday_skills
    import habit_skills

HOME_TZ = ZoneInfo("Europe/Istanbul")
# frankfurter.app permanently redirects here; redirects are never followed, so use the canonical host.
FX_URL = "https://api.frankfurter.dev/v1/latest?"
TR_DAYS = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")
TR_MONTHS = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
             "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
MAX_SKILL_TEXT = 220

FetchJson = Callable[[str, str, int], Awaitable[dict]]


# ── formatting ──────────────────────────────────────────────────────────────

def now_local(now: datetime | None = None, tz: ZoneInfo = HOME_TZ) -> datetime:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(tz)


def format_date_tr(value: date) -> str:
    return f"{value.day} {TR_MONTHS[value.month - 1]} {value.year} {TR_DAYS[value.weekday()]}"


def format_number_tr(value: float, max_decimals: int = 6) -> str:
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
        value = int(value)
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    if abs(value) >= 1e15 or (value and abs(value) < 1e-6):
        return f"{value:.6g}".replace(".", ",")
    text = f"{value:,.{max_decimals}f}".rstrip("0").rstrip(".")
    return text.replace(",", "\0").replace(".", ",").replace("\0", ".")


def clock_context(now: datetime | None = None) -> str:
    """One line so the model knows 'today' instead of guessing a date."""
    local = now_local(now)
    offset = local.strftime("%z")
    return (f"CURRENT DATE/TIME (owner's clock, Europe/Istanbul UTC{offset[:3]}:{offset[3:]}): "
            f"{format_date_tr(local.date())}, {local:%H:%M}. Use it for today/tomorrow, "
            "ages and countdowns; never invent a different current date.\n")


# ── clock & calendar ────────────────────────────────────────────────────────

CITY_TZ = {
    "istanbul": ("İstanbul", "Europe/Istanbul"), "ankara": ("Ankara", "Europe/Istanbul"),
    "izmir": ("İzmir", "Europe/Istanbul"), "turkiye": ("Türkiye", "Europe/Istanbul"),
    "lefkosa": ("Lefkoşa", "Asia/Nicosia"), "kibris": ("Kıbrıs", "Asia/Nicosia"),
    "londra": ("Londra", "Europe/London"), "london": ("Londra", "Europe/London"),
    "ingiltere": ("İngiltere", "Europe/London"), "paris": ("Paris", "Europe/Paris"),
    "fransa": ("Fransa", "Europe/Paris"), "berlin": ("Berlin", "Europe/Berlin"),
    "almanya": ("Almanya", "Europe/Berlin"), "amsterdam": ("Amsterdam", "Europe/Amsterdam"),
    "roma": ("Roma", "Europe/Rome"), "italya": ("İtalya", "Europe/Rome"),
    "madrid": ("Madrid", "Europe/Madrid"), "ispanya": ("İspanya", "Europe/Madrid"),
    "atina": ("Atina", "Europe/Athens"), "yunanistan": ("Yunanistan", "Europe/Athens"),
    "moskova": ("Moskova", "Europe/Moscow"), "rusya": ("Moskova", "Europe/Moscow"),
    "kiev": ("Kiev", "Europe/Kyiv"), "baku": ("Bakü", "Asia/Baku"),
    "tahran": ("Tahran", "Asia/Tehran"), "dubai": ("Dubai", "Asia/Dubai"),
    "riyad": ("Riyad", "Asia/Riyadh"), "kahire": ("Kahire", "Africa/Cairo"),
    "misir": ("Mısır", "Africa/Cairo"), "delhi": ("Yeni Delhi", "Asia/Kolkata"),
    "hindistan": ("Hindistan", "Asia/Kolkata"), "bangkok": ("Bangkok", "Asia/Bangkok"),
    "singapur": ("Singapur", "Asia/Singapore"), "hong kong": ("Hong Kong", "Asia/Hong_Kong"),
    "pekin": ("Pekin", "Asia/Shanghai"), "sanghay": ("Şanghay", "Asia/Shanghai"),
    "cin": ("Çin", "Asia/Shanghai"), "seul": ("Seul", "Asia/Seoul"),
    "tokyo": ("Tokyo", "Asia/Tokyo"), "japonya": ("Japonya", "Asia/Tokyo"),
    "sidney": ("Sidney", "Australia/Sydney"), "sydney": ("Sidney", "Australia/Sydney"),
    "new york": ("New York", "America/New_York"), "washington": ("Washington", "America/New_York"),
    "chicago": ("Chicago", "America/Chicago"), "toronto": ("Toronto", "America/Toronto"),
    "los angeles": ("Los Angeles", "America/Los_Angeles"),
    "san francisco": ("San Francisco", "America/Los_Angeles"),
    "meksika": ("Mexico City", "America/Mexico_City"), "sao paulo": ("São Paulo", "America/Sao_Paulo"),
    "brezilya": ("Brezilya", "America/Sao_Paulo"),
}
_TIME_Q = re.compile(r"\bsaat (?:kac|ka[cç]ta)\b|\bwhat time\b|\bsaati (?:soyle|ne)\b|\bsu an saat\b")
_DATE_Q = re.compile(r"\bbugun (?:gunlerden ne|ayin kaci|ne gun|hangi gun)|\bayin kaci\b"
                     r"|\b(?:bugunun|bugun|su an(?:ki)?|simdiki|guncel) tarih\w*|^\s*tarih(?:i)? (?:ne|nedir|kac)\s*\??\s*$"
                     r"|\bhangi gundeyiz\b|\bgunlerden ne\b|\bwhat(?:'s| is) (?:the )?date\b|\bwhat day is it\b")


def _city_for_clock(folded: str) -> tuple[str, str] | None:
    for key in sorted(CITY_TZ, key=len, reverse=True):
        if re.search(r"\b" + re.escape(key) + r"(?:'?(?:da|de|ta|te|nda|nde|in|nin|un|nun))?\b", folded):
            return CITY_TZ[key]
    return None


def answer_clock(text: str, now: datetime | None = None) -> str | None:
    folded = fold_turkish(text)
    asks_time, asks_date = bool(_TIME_Q.search(folded)), bool(_DATE_Q.search(folded))
    if not (asks_time or asks_date):
        return None
    city = _city_for_clock(folded) if asks_time else None
    if city and city[1] != "Europe/Istanbul":
        local = now_local(now, ZoneInfo(city[1]))
        home = now_local(now)
        diff = (local.utcoffset() - home.utcoffset()).total_seconds() / 3600
        rel = "Türkiye ile aynı saat" if diff == 0 else (
            f"Türkiye'den {format_number_tr(abs(diff))} saat {'ileri' if diff > 0 else 'geri'}")
        return (f"{city[0]}'da saat şu an {local:%H:%M} ({format_date_tr(local.date())}). {rel}.")
    local = now_local(now)
    if asks_time and not asks_date:
        return f"Saat {local:%H:%M}, efendim. Bugün {format_date_tr(local.date())}."
    return f"Bugün {format_date_tr(local.date())}. Saat {local:%H:%M}."


_MONTH_KEYS = {fold_turkish(m): i + 1 for i, m in enumerate(TR_MONTHS)}
_COUNTDOWN = re.compile(r"kac gun (?:var|kaldi)|kac gun sonra|ne kadar (?:var|kaldi)|how many days")
_NAMED_DAYS = {"yilbasi": (1, 1), "sevgililer gunu": (2, 14), "23 nisan": (4, 23),
               "19 mayis": (5, 19), "30 agustos": (8, 30), "cumhuriyet bayrami": (10, 29),
               "29 ekim": (10, 29), "noel": (12, 25)}


def _parse_target_date(folded: str, today: date) -> tuple[date, str] | None:
    numeric = re.search(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", folded)
    if numeric:
        d, m, y = map(int, numeric.groups())
        try:
            return date(y, m, d), f"{d} {TR_MONTHS[m - 1]} {y}"
        except (ValueError, IndexError):
            return None
    for name, (m, d) in _NAMED_DAYS.items():
        if name in folded:
            target = date(today.year, m, d)
            if target < today:
                target = date(today.year + 1, m, d)
            label = "Yılbaşı" if name == "yilbasi" else f"{d} {TR_MONTHS[m - 1]}"
            return target, f"{label} ({target.year})"
    named = re.search(r"\b(\d{1,2}) (" + "|".join(_MONTH_KEYS) + r")(?: (\d{4}))?", folded)
    if named:
        d, m = int(named.group(1)), _MONTH_KEYS[named.group(2)]
        y = int(named.group(3)) if named.group(3) else today.year
        try:
            target = date(y, m, d)
        except ValueError:
            return None
        if not named.group(3) and target < today:
            target = date(y + 1, m, d)
        return target, f"{d} {TR_MONTHS[m - 1]} {target.year}"
    return None


def answer_countdown(text: str, now: datetime | None = None) -> str | None:
    folded = fold_turkish(text)
    if not _COUNTDOWN.search(folded):
        return None
    today = now_local(now).date()
    parsed = _parse_target_date(folded, today)
    if not parsed:
        return None
    target, label = parsed
    days = (target - today).days
    if days == 0:
        return f"{label} bugün!"
    if days < 0:
        return f"{label} {abs(days)} gün önceydi ({format_date_tr(target)})."
    weeks, rest = divmod(days, 7)
    extra = f" (yaklaşık {weeks} hafta {rest} gün)" if weeks else ""
    return f"{label} için {days} gün kaldı{extra}. O gün {TR_DAYS[target.weekday()]}."


# ── calculator ──────────────────────────────────────────────────────────────

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod, ast.Pow: operator.pow}
_FUNCS = {"sqrt": math.sqrt}
_WORD_OPS = [
    (r"\bkarekok(?:u)?\s*(\d+(?:[.,]\d+)?)", r"sqrt(\1)"),
    (r"(\d+(?:[.,]\d+)?)\s*'?(?:in|nin|un|nun|[iıuü]n)?\s+karekok(?:u)?", r"sqrt(\1)"),
    (r"\barti\b|\bplus\b", "+"), (r"\beksi\b|\bminus\b", "-"),
    (r"\bcarpi\b|\btimes\b|\b[x×]\b|×", "*"), (r"\bbolu\b|÷|\bdivided by\b", "/"),
    (r"\buzeri\b|\bussu\b|\^", "**"), (r"\bmod\b", "%"),
]
_CALC_NOISE = re.compile(r"\b(?:hesapla|hesaplar misin|hesaplayin|kac eder|kac yapar|kactir|kac|eder|yapar|"
                         r"nedir|ne eder|sonuc|sonucu|esittir|calculate|what is|whats|lutfen)\b|[=?!]")


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _safe_eval(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _safe_eval(node.left), _safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 1e6):
            raise ValueError("exponent_too_large")
        result = _OPS[type(node.op)](left, right)
        if isinstance(result, complex) or abs(result) > 1e18:
            raise ValueError("result_out_of_range")
        return result
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS
            and len(node.args) == 1 and not node.keywords):
        return _FUNCS[node.func.id](_safe_eval(node.args[0]))
    raise ValueError("unsupported_expression")


def _normalize_numbers(expr: str) -> str:
    # Turkish: 1.250,5 → 1250.5 ; 3,5 → 3.5 ; 1.250 → 1250 (thousands group).
    expr = re.sub(r"\b(\d{1,3}(?:\.\d{3})+),(\d+)\b", lambda m: m.group(1).replace(".", "") + "." + m.group(2), expr)
    expr = re.sub(r"\b\d{1,3}(?:\.\d{3})+\b(?![.,]\d)", lambda m: m.group(0).replace(".", ""), expr)
    return re.sub(r"(\d),(\d)", r"\1.\2", expr)


def answer_math(text: str) -> str | None:
    folded = fold_turkish(text).strip()
    if len(folded) > 140:
        return None
    pct = re.fullmatch(r"\s*(?:hesapla\s*)?([\d.,]+)\s*'?\s*(?:[a-z]{0,3}n)?\s*(?:%|yuzde)\s*([\d.,]+)\s*'?\s*"
                       r"(?:[a-z]{1,3})?\s*(?:kac|kac eder|nedir|ne eder|ne kadar)?\s*[?]?\s*", folded)
    if pct:
        try:
            base = float(_normalize_numbers(pct.group(1)))
            rate = float(_normalize_numbers(pct.group(2)))
        except ValueError:
            return None
        result = base * rate / 100
        return (f"{format_number_tr(base)} sayısının %{format_number_tr(rate)}'i = {format_number_tr(result)}. "
                f"(Eklenince {format_number_tr(base + result)}, düşülünce {format_number_tr(base - result)}.)")
    expr = folded
    for pattern, repl in _WORD_OPS:
        expr = re.sub(pattern, repl, expr)
    expr = _CALC_NOISE.sub(" ", expr)
    expr = _normalize_numbers(expr).strip()
    if not expr or not re.fullmatch(r"[\d\s.+\-*/%()sqrt]+", expr):
        return None
    if not re.search(r"\d", expr) or not re.search(r"[+\-*/%]|sqrt", expr.lstrip("-+ ")):
        return None
    try:
        result = _safe_eval(ast.parse(expr, mode="eval"))
    except ZeroDivisionError:
        return "Sıfıra bölme tanımsız, efendim."
    except (SyntaxError, ValueError, TypeError, OverflowError):
        return None
    shown = re.sub(r"\d+(?:\.\d+)?", lambda m: format_number_tr(float(m.group(0))), expr)
    shown = re.sub(r"\s+", " ", shown).replace("**", "^").replace("*", "×").replace("/", "÷").replace("sqrt", "√")
    return f"{shown} = {format_number_tr(result)}"


# ── unit conversion ─────────────────────────────────────────────────────────

_UNITS: dict[str, tuple[str, float, str]] = {}


def _unit(kind: str, factor: float, label: str, *names: str) -> None:
    for name in names:
        _UNITS[name] = (kind, factor, label)


_unit("length", 0.001, "mm", "mm", "milimetre")
_unit("length", 0.01, "cm", "cm", "santim", "santimetre")
_unit("length", 1.0, "m", "m", "metre", "meter")
_unit("length", 1000.0, "km", "km", "kilometre")
_unit("length", 0.0254, "inç", "inc", "inch", "inches", "in")
_unit("length", 0.3048, "feet", "ft", "feet", "foot", "fit")
_unit("length", 0.9144, "yard", "yard", "yd")
_unit("length", 1609.344, "mil", "mil", "mile", "miles")
_unit("mass", 0.001, "g", "g", "gr", "gram")
_unit("mass", 1.0, "kg", "kg", "kilo", "kilogram")
_unit("mass", 1000.0, "ton", "ton")
_unit("mass", 0.45359237, "pound", "lb", "lbs", "pound", "libre")
_unit("mass", 0.028349523125, "ons", "oz", "ons", "ounce")
_unit("volume", 0.001, "ml", "ml", "mililitre")
_unit("volume", 1.0, "litre", "l", "lt", "litre", "liter")
_unit("volume", 3.785411784, "galon", "galon", "gallon")
_unit("speed", 1 / 3.6, "km/sa", "km/sa", "km/h", "kmh", "km/saat", "km/s")
_unit("speed", 0.44704, "mph", "mph")
_unit("speed", 1.0, "m/sn", "m/sn", "m/s")
_unit("speed", 0.514444, "knot", "knot", "kn", "deniz mili/sa")
_unit("data", 1.0, "MB", "mb", "megabayt", "megabyte")
_unit("data", 1024.0, "GB", "gb", "gigabayt", "gigabyte")
_unit("data", 1024.0 ** 2, "TB", "tb", "terabayt", "terabyte")
_unit("data", 1 / 1024, "KB", "kb", "kilobayt", "kilobyte")
_TEMP = {"c": "C", "°c": "C", "celsius": "C", "santigrat": "C", "derece": "C",
         "f": "F", "°f": "F", "fahrenheit": "F", "k": "K", "kelvin": "K"}

_UNIT_ALT = "|".join(sorted((re.escape(u) for u in list(_UNITS) + list(_TEMP)), key=len, reverse=True))
_CONVERT = re.compile(
    r"(-?\d+(?:[.,]\d+)?)\s*(" + _UNIT_ALT + r")\b\s*'?[a-z]{0,4}\s*"
    r"(?:kac|ne kadar|to|in|into|=|->|→|cinsinden)\s*(" + _UNIT_ALT + r")(?![a-z0-9/])")


def _convert_temp(value: float, src: str, dst: str) -> float:
    kelvin = {"C": value + 273.15, "F": (value - 32) * 5 / 9 + 273.15, "K": value}[src]
    return {"C": kelvin - 273.15, "F": (kelvin - 273.15) * 9 / 5 + 32, "K": kelvin}[dst]


def answer_units(text: str) -> str | None:
    folded = fold_turkish(text)
    match = _CONVERT.search(folded)
    if not match:
        return None
    value = float(match.group(1).replace(",", "."))
    src, dst = match.group(2), match.group(3)
    if src in _TEMP and dst in _TEMP:
        s, d = _TEMP[src], _TEMP[dst]
        if s == d:
            return None
        result = _convert_temp(value, s, d)
        if d == "K" and result < 0:
            return "Bu sıcaklık mutlak sıfırın altında; fiziksel olarak mümkün değil."
        sign = {"C": "°C", "F": "°F", "K": "K"}
        return f"{format_number_tr(value)} {sign[s]} = {format_number_tr(round(result, 2))} {sign[d]}"
    if src not in _UNITS or dst not in _UNITS:
        return None
    (kind_a, fa, la), (kind_b, fb, lb) = _UNITS[src], _UNITS[dst]
    if kind_a != kind_b or src == dst:
        return None
    result = value * fa / fb
    precision = 4 if abs(result) < 10 else 2
    return f"{format_number_tr(value)} {la} = {format_number_tr(round(result, precision))} {lb}"


# ── weather (Open-Meteo, keyless) ───────────────────────────────────────────

_WMO_TR = {
    0: "açık", 1: "çoğunlukla açık", 2: "parçalı bulutlu", 3: "kapalı",
    45: "sisli", 48: "kırağılı sis", 51: "hafif çisenti", 53: "çisenti", 55: "yoğun çisenti",
    56: "dondurucu çisenti", 57: "yoğun dondurucu çisenti", 61: "hafif yağmurlu", 63: "yağmurlu",
    65: "şiddetli yağmurlu", 66: "dondurucu yağmur", 67: "şiddetli dondurucu yağmur",
    71: "hafif kar yağışlı", 73: "kar yağışlı", 75: "yoğun kar yağışlı", 77: "kar taneli",
    80: "hafif sağanak", 81: "sağanak", 82: "şiddetli sağanak", 85: "hafif kar sağanağı",
    86: "yoğun kar sağanağı", 95: "gök gürültülü fırtına", 96: "dolulu fırtına", 99: "şiddetli dolulu fırtına",
}
_WEATHER_Q = re.compile(r"\bhava (?:durumu|nasil|nasildir|ne durumda|kac derece|sicak mi|soguk mu)"
                        r"|\b(?:yagmur|kar) yagacak mi\b|\bsemsiye\b|\bkac derece\b|\bweather\b")
_WEATHER_SKIP = re.compile(r"\b(?:neden|niye|nicin|why|iklim degisikligi|kuresel isinma|uygulama\w*|yaz|yazar|yazsana|kod\w*|program\w*|api|site\w*|widget|tasarla\w*)\b")
_NOT_PLACES = {"bugun", "yarin", "burada", "burasi", "disarida", "disari", "orada", "evde", "simdi",
               "su", "an", "hafta", "sonu", "aksam", "sabah", "gece", "bu", "ve", "acaba", "peki",
               "golge", "oralarda", "buralarda", "bizim", "senin", "benim", "nasil"}


def weather_place(text: str) -> str | None:
    """Return the place name the owner asked about, or None for 'here'."""
    cleaned = re.sub(r"[?!.,;:]", " ", str(text or ""))
    patterns = (
        r"([A-ZÇĞİÖŞÜa-zçğıöşü]+(?: [A-ZÇĞİÖŞÜ][a-zçğıöşü]+)?)'?(?:da|de|ta|te|nda|nde)\s+(?:bugün |yarın |şu an |şimdi )?(?:hava|yağmur|kar|kaç derece|şemsiye)",
        r"hava durumu\s+([A-ZÇĞİÖŞÜa-zçğıöşü]+(?: [A-ZÇĞİÖŞÜ][a-zçğıöşü]+)?)",
        r"([A-ZÇĞİÖŞÜa-zçğıöşü]+(?: [A-ZÇĞİÖŞÜ][a-zçğıöşü]+)?)\s+(?:için\s+)?hava durumu",
        r"weather in ([A-Za-z ]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if not match:
            continue
        words = [w for w in match.group(1).split() if fold_turkish(w) not in _NOT_PLACES]
        if words and len(words[-1]) >= 3:
            return " ".join(words).strip("'")
    return None


def home_location() -> tuple[str, float, float]:
    name = (os.getenv("GOLGE_HOME_CITY") or "Lefkoşa").strip()[:60] or "Lefkoşa"
    try:
        lat = float(os.getenv("GOLGE_HOME_LAT", "35.13"))
        lon = float(os.getenv("GOLGE_HOME_LON", "33.43"))
    except ValueError:
        lat, lon = 35.13, 33.43
    return name, lat, lon


async def answer_weather(text: str, fetch_json: FetchJson, now: datetime | None = None,
                         location: dict | None = None) -> str | None:
    folded = fold_turkish(text)
    if not _WEATHER_Q.search(folded) or _WEATHER_SKIP.search(folded):
        return None
    place = weather_place(text)
    try:
        if place:
            geo = await fetch_json(
                "https://geocoding-api.open-meteo.com/v1/search?"
                + urlencode({"name": place, "count": 1, "language": "tr", "format": "json"}),
                "geo:" + fold_turkish(place), 86400)
            hits = geo.get("results") or []
            if not hits:
                return f"“{place}” diye bir yer bulamadım. Şehir adını biraz daha açık yazar mısın?"
            hit = hits[0]
            label = str(hit.get("name") or place)
            lat, lon = float(hit["latitude"]), float(hit["longitude"])
        elif location:
            label, lat, lon = "Bulunduğun konum", location["lat"], location["lon"]
        else:
            label, lat, lon = home_location()
        lat, lon = round(lat, 2), round(lon, 2)
        data = await fetch_json(
            "https://api.open-meteo.com/v1/forecast?"
            + urlencode({"latitude": lat, "longitude": lon,
                         "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
                         "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                         "timezone": "auto", "forecast_days": 2}),
            f"skillweather:{lat}:{lon}", 600)
    except Exception:
        return ("Hava durumu kaynağına şu an ulaşamadım. Uydurmamak için tahmin vermiyorum; "
                "biraz sonra yeniden sorabilirsin.")
    current, daily = data.get("current") or {}, data.get("daily") or {}
    if current.get("temperature_2m") is None:
        return "Hava durumu verisi eksik geldi; doğrulanmış bir değer veremiyorum."
    tomorrow = "yarin" in folded or "tomorrow" in folded
    idx = 1 if tomorrow else 0

    def day_value(key: str):
        values = daily.get(key) or []
        return values[idx] if len(values) > idx else None

    hi, lo, rain = day_value("temperature_2m_max"), day_value("temperature_2m_min"), day_value("precipitation_probability_max")
    code = day_value("weather_code") if tomorrow else current.get("weather_code")
    desc = _WMO_TR.get(code if isinstance(code, int) else -1, "")
    t = lambda v: f"{format_number_tr(round(float(v)))}°C"
    if tomorrow:
        parts = [f"{label} için yarın" + (f" {desc}" if desc else "") + " bekleniyor"]
    else:
        parts = [(f"{label}'da şu an" if not location or place else "Bulunduğun konumda şu an") + f" {t(current['temperature_2m'])}" + (f", {desc}" if desc else "")]
        if current.get("apparent_temperature") is not None:
            parts.append(f"hissedilen {t(current['apparent_temperature'])}")
        if current.get("wind_speed_10m") is not None:
            parts.append(f"rüzgâr {format_number_tr(round(float(current['wind_speed_10m'])))} km/sa")
    if hi is not None and lo is not None:
        parts.append(f"{'yarın' if tomorrow else 'bugün'} en yüksek {t(hi)}, en düşük {t(lo)}")
    if rain is not None:
        parts.append(f"yağış olasılığı %{int(rain)}")
    advice = ""
    if rain is not None and rain >= 50:
        advice = " Şemsiyeni yanına almanı öneririm."
    elif hi is not None and float(hi) >= 33:
        advice = " Bol su içmeyi unutma."
    elif lo is not None and float(lo) <= 3:
        advice = " Sıkı giyinmekte fayda var."
    if not place and not tomorrow and not location:
        advice += " (Varsayılan konum; başka şehir için adını söyleyebilirsin.)"
    return "; ".join(parts) + "." + advice + " Kaynak: Open-Meteo."


# ── exchange rates (ECB reference via Frankfurter, keyless) ─────────────────

_CURRENCIES = {
    "dolar": "USD", "dolari": "USD", "usd": "USD", "$": "USD",
    "euro": "EUR", "avro": "EUR", "eur": "EUR", "€": "EUR",
    "sterlin": "GBP", "gbp": "GBP", "£": "GBP", "ingiliz sterlini": "GBP",
    "tl": "TRY", "lira": "TRY", "turk lirasi": "TRY", "try": "TRY", "₺": "TRY",
    "yen": "JPY", "jpy": "JPY", "frank": "CHF", "isvicre frangi": "CHF", "chf": "CHF",
    "yuan": "CNY", "cny": "CNY", "kanada dolari": "CAD", "cad": "CAD",
}
_CUR_ALT = "|".join(sorted((re.escape(c) for c in _CURRENCIES), key=len, reverse=True))
_CUR_TOKEN = re.compile(r"(?<![a-z])(" + _CUR_ALT + r")(?:'?[a-z]{0,3})?(?![a-z])")
_FX_Q = re.compile(r"\bkac\b|\bne kadar\b|\bkuru?\b|\bkac para\b|\bexchange rate\b|\bin\b|\bto\b")
_FX_SKIP = re.compile(r"\b(?:neden|niye|nicin|why|yorum|tahmin|analiz|yukselir mi|duser mi|alayim mi|satayim mi)\b")


async def answer_currency(text: str, fetch_json: FetchJson) -> str | None:
    folded = fold_turkish(text)
    if not _FX_Q.search(folded) or _FX_SKIP.search(folded) or len(folded) > 120:
        return None
    found = []
    for match in _CUR_TOKEN.finditer(folded):
        code = _CURRENCIES[match.group(1)]
        if code not in found:
            found.append(code)
    if not found or (found == ["TRY"]):
        return None
    if "doviz" not in folded and "kur" not in folded and not re.search(r"\d|kac|ne kadar", folded):
        return None
    src = found[0] if found[0] != "TRY" or len(found) == 1 else found[1]
    dst = next((c for c in found if c != src), "TRY")
    amount_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:" + _CUR_ALT + r")", folded)
    amount = float(amount_match.group(1).replace(",", ".")) if amount_match else 1.0
    if amount <= 0 or amount > 1e12:
        return None
    try:
        data = await fetch_json(FX_URL + urlencode({"base": src, "symbols": dst}),
                                f"fx:{src}:{dst}", 1800)
        rate = float((data.get("rates") or {})[dst])
    except Exception:
        return ("Döviz kaynağına şu an ulaşamadım; doğrulanmamış kur söylemek istemem. "
                "Biraz sonra yeniden deneyebilirsin.")
    day = str(data.get("date") or "")[:10]
    return (f"{format_number_tr(amount)} {src} = {format_number_tr(round(amount * rate, 4 if rate < 1 else 2))} {dst} "
            f"(Avrupa Merkez Bankası referans kuru{', ' + day if day else ''}). "
            "Banka ve anlık piyasa kurları biraz farklı olabilir.")


# ── status report ───────────────────────────────────────────────────────────

_STATUS_Q = re.compile(r"\b(?:durum raporu|sistem durumu|durum ozeti|rapor ver|genel durum|status report|"
                       r"sistemler nasil|her sey yolunda mi|neler oluyor)\b")


def _ago(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds} sn önce"
    if seconds < 3600:
        return f"{seconds // 60} dk önce"
    if seconds < 86400:
        return f"{seconds // 3600} sa önce"
    return f"{seconds // 86400} gün önce"


async def answer_status(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    if pool is None or not _STATUS_Q.search(fold_turkish(text)):
        return None
    local = now_local(now)
    lines = [f"Durum raporu — {format_date_tr(local.date())}, {local:%H:%M}:"]
    current = now or datetime.now(timezone.utc)
    try:
        desktop = await pool.fetchrow(
            "SELECT last_seen, (last_seen > NOW() - INTERVAL '15 seconds') AS online "
            "FROM device_presence WHERE user_id=$1 AND device='desktop'", user_id)
        if desktop and desktop["online"]:
            lines.append("• Bilgisayar: çevrimiçi, komutlara hazır.")
        elif desktop:
            lines.append(f"• Bilgisayar: çevrimdışı (son sinyal {_ago((current - desktop['last_seen']).total_seconds())}).")
        else:
            lines.append("• Bilgisayar: henüz hiç bağlanmadı.")
        queued = await pool.fetchval(
            "SELECT COUNT(*) FROM device_commands WHERE user_id=$1 AND target='desktop' AND status='queued'",
            user_id)
        lines.append(f"• Bekleyen bilgisayar komutu: {int(queued or 0)}")
        plans = await pool.fetch(
            "SELECT title, scheduled_time, is_done FROM owner_plans WHERE user_id=$1 AND scheduled_date=$2 "
            "ORDER BY scheduled_time NULLS LAST, id LIMIT 6", user_id, local.date())
        if plans:
            done = sum(1 for p in plans if p["is_done"])
            lines.append(f"• Bugünkü planlar: {len(plans)} ({done} tamamlandı)")
            for p in plans:
                if not p["is_done"]:
                    when = p["scheduled_time"].strftime("%H:%M") + " " if p["scheduled_time"] else ""
                    lines.append(f"   – {when}{str(p['title'])[:80]}")
        else:
            lines.append("• Bugün için kayıtlı plan yok.")
        memories = await pool.fetchval("SELECT COUNT(*) FROM memories WHERE user_id=$1", user_id)
        lines.append(f"• Kayıtlı hafıza: {int(memories or 0)} bilgi")
        errors = await pool.fetchval(
            "SELECT COUNT(*) FROM events WHERE user_id=$1 AND event_type LIKE '%error%' "
            "AND created_at > NOW() - INTERVAL '24 hours'", user_id)
        lines.append("• Son 24 saatte model hatası: " + (f"{int(errors)}" if errors else "yok"))
    except Exception:
        lines.append("• Bazı durum bilgilerini şu an okuyamadım; eksik bilgiyi tahmin etmiyorum.")
    return "\n".join(lines)


# ── agenda & morning briefing ───────────────────────────────────────────────

_AGENDA_Q = re.compile(r"\btakvim(?:im)?(?:de|imde)? ne var|\b(?:bugun|yarin|bu hafta|haftalik)\b.{0,25}\b(?:programim|ajandam|planim|planlarim|takvimim|toplantilarim|etkinliklerim)\b"
                       r"|\b(?:programim|ajandam|takvimim) ne\b|\bajanda\b|\b(?:bugun|yarin) ne var\b|\btoplantim var mi\b|\bnelerim var\b|\bsiradaki (?:toplanti|etkinlik)\b")
_BRIEF_Q = re.compile(r"\b(?:sabah|gunluk|gunun) (?:brifing\w*|ozet\w*|raporu)\b|\bbrifing\b|\bbriefing\b|\bgunu ozetle\b")
_GREETING = re.compile(r"\bgunaydin\b")


def _range_for(folded: str, today: date) -> tuple[date, date, str]:
    if "yarin" in folded:
        d = today + timedelta(days=1)
        return d, d, "Yarın"
    if "hafta" in folded:
        return today, today + timedelta(days=6), "Önümüzdeki 7 gün"
    return today, today, "Bugün"


async def agenda_lines(pool: Any, user_id: str, start: date, end: date) -> tuple[list[str], list[str]]:
    """Calendar + owner plans + pending reminders in [start, end]; plus honest notes."""
    lines: list[tuple[Any, str]] = []
    notes: list[str] = []
    try:
        events = await calendar_feed.events_between(pool, user_id, start, end)
        if events is None:
            notes.append("Takvim bağlı değil (Planlar bölümünden gizli iCal adresini ekleyebilirsin).")
        for e in events or []:
            day = datetime.fromisoformat(e["start"]).date() if not e["all_day"] else date.fromisoformat(e["start"])
            when = "" if start == end else f"{day.day} {TR_MONTHS[day.month - 1][:3]} · "
            lines.append(((day, e["start"]), f"{when}{calendar_feed.format_event(e)}"))
    except calendar_feed.FeedError:
        notes.append("Takvim kaynağına şu an ulaşamadım; takvim etkinliklerini okuyamadım.")
    except Exception:
        notes.append("Takvim bilgisi okunamadı.")
    try:
        plans = await pool.fetch(
            "SELECT title,scheduled_date,scheduled_time FROM owner_plans WHERE user_id=$1 AND is_done=FALSE "
            "AND scheduled_date BETWEEN $2 AND $3 ORDER BY scheduled_date, scheduled_time NULLS LAST LIMIT 12",
            user_id, start, end)
        for p in plans:
            clock = p["scheduled_time"].strftime("%H:%M") if p["scheduled_time"] else "Gün içinde"
            day = p["scheduled_date"]
            when = "" if start == end else f"{day.day} {TR_MONTHS[day.month - 1][:3]} · "
            key = (day, f"{day.isoformat()}T{clock}" if p["scheduled_time"] else f"{day.isoformat()}T99")
            lines.append((key, f"{when}{clock} — {str(p['title'])[:80]} (plan)"))
        rems = await pool.fetch(
            "SELECT text,due_at FROM owner_reminders WHERE user_id=$1 AND status='pending' "
            "AND (due_at AT TIME ZONE 'Europe/Istanbul')::date BETWEEN $2 AND $3 ORDER BY due_at LIMIT 10",
            user_id, start, end)
        for r in rems:
            due = r["due_at"].astimezone(HOME_TZ)
            when = "" if start == end else f"{due.day} {TR_MONTHS[due.month - 1][:3]} · "
            lines.append(((due.date(), due.isoformat()), f"{when}{due:%H:%M} — ⏰ {r['text']}"))
    except Exception:
        notes.append("Planlar okunamadı.")
    lines.sort(key=lambda item: (item[0][0], str(item[0][1])[11:] or ""))
    return [text for _, text in lines], notes


async def answer_agenda(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    folded = fold_turkish(text)
    if pool is None or not _AGENDA_Q.search(folded):
        return None
    today = now_local(now).date()
    start, end, label = _range_for(folded, today)
    lines, notes = await agenda_lines(pool, user_id, start, end)
    head = f"{label} ({format_date_tr(start) if start == end else format_date_tr(start) + ' – ' + format_date_tr(end)}):"
    if not lines:
        body = "Kayıtlı etkinlik, plan ya da hatırlatıcı görünmüyor."
    else:
        body = "\n".join("• " + l for l in lines)
    return "\n".join([head, body] + [f"ℹ {n}" for n in notes])


def _greeting(hour: int) -> str:
    return ("İyi geceler" if hour < 5 else "Günaydın" if hour < 12 else "İyi günler" if hour < 18 else "İyi akşamlar")


async def answer_briefing(text: str, pool: Any, user_id: str, fetch_json: FetchJson | None,
                          now: datetime | None = None, fetch_text=None) -> str | None:
    folded = fold_turkish(text)
    wants = bool(_BRIEF_Q.search(folded)) or (bool(_GREETING.search(folded)) and len(folded) <= 30)
    if pool is None or not wants:
        return None
    local = now_local(now)
    parts = [f"{_greeting(local.hour)}, efendim. {format_date_tr(local.date())}, saat {local:%H:%M}."]
    if fetch_json is not None:
        weather = await answer_weather("hava durumu", fetch_json, now)
        if weather and "ulaşamadım" not in weather and "eksik" not in weather:
            parts.append("🌤 " + weather.replace(" (Varsayılan konum; başka şehir için adını söyleyebilirsin.)", "").replace(" Kaynak: Open-Meteo.", ""))
    lines, notes = await agenda_lines(pool, user_id, local.date(), local.date())
    parts.append("📅 Bugün:\n" + "\n".join("• " + l for l in lines) if lines else "📅 Bugün için kayıtlı etkinlik ya da plan görünmüyor.")
    try:
        tomorrow = local.date() + timedelta(days=1)
        nxt, _ = await agenda_lines(pool, user_id, tomorrow, tomorrow)
        if nxt:
            parts.append(f"➡ Yarın: {len(nxt)} kayıt, ilki: {nxt[0]}")
    except Exception:
        pass
    try:
        desktop = await pool.fetchval("SELECT (last_seen > NOW() - INTERVAL '15 seconds') FROM device_presence WHERE user_id=$1 AND device='desktop'", user_id)
        parts.append("💻 Bilgisayar: " + ("çevrimiçi." if desktop else "çevrimdışı."))
    except Exception:
        pass
    try:
        news = await phone_skills.headlines(None, fetch_text, 3)
        if news:
            parts.append("📰 Gündem:\n" + "\n".join("• " + n["title"] for n in news))
    except Exception:
        pass
    if fetch_json is not None:
        fx = []
        for code in ("USD", "EUR"):
            try:
                data = await fetch_json(FX_URL + urlencode({"base": code, "symbols": "TRY"}), f"fx:{code}:TRY", 1800)
                fx.append(f"{code} {format_number_tr(round(float(data['rates']['TRY']), 2))} ₺")
            except Exception:
                pass
        if fx:
            parts.append("💱 " + " · ".join(fx) + " (AMB referans)")
    parts.extend(f"ℹ {n}" for n in notes)
    return "\n".join(parts)


# ── help ────────────────────────────────────────────────────────────────────

_HELP_Q = re.compile(r"\b(?:neler|ne) yapabilirsin\b|\byapabildiklerin\b|\bozelliklerin\b|\bkomutlar(?:in)?\b|\byetenekleri?n\b|\bnasil kullanilir\b|^\s*yardim\s*[?!.]*$")
HELP_TEXT = (
    "Yapabildiklerim (örnekler):\n"
    "⏰ Hatırlatıcı: “20 dakika sonra su içmeyi hatırlat”, “her gün 9'da ilaç hatırlat”\n"
    "📅 Plan/takvim: “yarın 15:00 diş randevusu planıma ekle”, “planlarım”, “bugün programım ne”\n"
    "🌤 Bilgi: hava (konumunla), haberler, döviz, bitcoin, namaz vakitleri, depremler, gün doğumu, ay evresi, “Atatürk kimdir”\n"
    "🧮 Hesap: “15 x 4 + 2”, “100 km kaç mil”, “yılbaşına kaç gün var”, saat/tarih/dünya saatleri\n"
    "🔔 Uyarılar: “bitcoin 70 bin dolara çıkarsa haber ver”, “sessiz saatler 23 ile 7”, “sabah brifingi bildirimi aç”\n"
    "💧 Alışkanlık: “2 bardak su içtim”, “7 saat uyudum”, “30 dakika yürüdüm”, “modum 4”, “sağlık özetim”, “bu hafta ne kadar spor yaptım”\n"
    "🎂 Doğum günü: “Ahmet'in doğum günü 3 Mart”, “doğum günlerim”, “her yıl 14 şubat sevgililer günü hatırlat”\n"
    "🛒 Liste/harcama: “alışveriş listesine süt ekle”, “150 lira market harcaması ekle”, “bu ay ne kadar harcadım”, “10 dakika zamanlayıcı kur”\n"
    "🧠 Hafıza: “hatırla: …”, “neler hatırlıyorsun”, “unut: …”\n"
    "🎯 Görev: “görev: yarınki hava ve haberlere göre günümü planla” (adım adım çalışır)\n"
    "💻 Laptop: “laptop: chrome aç”, “ekran analizi yap” (laptop açıkken)\n"
    "🏠 Akıllı ev: “salon ışığını aç”, “klimayı 24 dereceye ayarla” (Home Assistant bağlıysa)\n"
    "📷 Görme: + düğmesiyle fotoğraf, ekran görüntüsü veya PDF gönder; YouTube linki + “özetle”\n"
    "Sınırlarım: laptop kapalıyken bilgisayarı yönetemem, kapı kilidini açmam, bildirimler için uygulamayı Ana Ekrana eklemen gerekir; "
    "uçuşlarda fiyat çekmem, sadece arama bağlantısı veririm."
)


def answer_help(text: str) -> str | None:
    f = fold_turkish(text)
    return HELP_TEXT if len(f) <= 50 and _HELP_Q.search(f) else None


# ── dispatcher ──────────────────────────────────────────────────────────────

_SKIP_ALL = re.compile(r"\b(?:arastir|research|kaynak goster|makale yaz|kod yaz|hikaye)\b")


async def instant_reply(text: str, *, pool: Any = None, user_id: str = "",
                        fetch_json: FetchJson | None = None,
                        now: datetime | None = None, location: dict | None = None,
                        fetch_text=None, ha=None, read_only: bool = False) -> dict | None:
    """Return {"skill", "reply"} for an unambiguous skill request, else None."""
    text = str(text or "").strip()
    if not text or len(text) > MAX_SKILL_TEXT or _SKIP_ALL.search(fold_turkish(text)):
        return None
    if pool is not None and not read_only:
        reply = await habit_skills.handle(text, pool, user_id, now)
        if reply:
            return {"skill": "habits", "reply": reply}
        reply = await birthday_skills.handle(text, pool, user_id, now)
        if reply:
            return {"skill": "birthdays", "reply": reply}
        reply = await expense_skills.handle(text, pool, user_id, now)
        if reply:
            return {"skill": "expenses", "reply": reply}
        reply = await list_skills.handle(text, pool, user_id)
        if reply:
            return {"skill": "lists", "reply": reply}
        reply = await alert_skills.handle(text, pool, user_id, fetch_json)
        if reply:
            return {"skill": "alerts", "reply": reply}
        reply = await plan_skills.handle(text, pool, user_id, now)
        if reply:
            return {"skill": "plans", "reply": reply}
        reply = await proactive.handle_prefs(text, pool, user_id)
        if reply:
            return {"skill": "prefs", "reply": reply}
        reply = await memory_skills.handle(text, pool, user_id)
        if reply:
            return {"skill": "memory", "reply": reply}
        reply = await reminders.manage_from_chat(text, pool, user_id, now)
        if reply:
            return {"skill": "reminders", "reply": reply}
        if reminders.has_reminder_intent(text):
            reply = await reminders.create_from_chat(text, pool, user_id, now)
            if reply:
                return {"skill": "reminder", "reply": reply}
    reply = answer_help(text)
    if reply:
        return {"skill": "help", "reply": reply}
    reply = await answer_status(text, pool, user_id, now)
    if reply:
        return {"skill": "status", "reply": reply}
    reply = await answer_briefing(text, pool, user_id, fetch_json, now, fetch_text)
    if reply:
        return {"skill": "briefing", "reply": reply}
    reply = await answer_agenda(text, pool, user_id, now)
    if reply:
        return {"skill": "agenda", "reply": reply}
    if fetch_json is not None:
        reply = await answer_weather(text, fetch_json, now, location)
        if reply:
            return {"skill": "weather", "reply": reply}
    if fetch_json is not None:
        known = await knowledge_skills.answer(text, fetch_json, now, location)
        if known:
            return {"skill": known[0], "reply": known[1]}
    reply = phone_skills.answer_flight(text, now)
    if reply:
        return {"skill": "flight", "reply": reply}
    reply = await phone_skills.answer_news(text, fetch_text)
    if reply:
        return {"skill": "news", "reply": reply}
    if (fetch_json is not None or pool is not None or ha is not None) and not read_only:
        reply = await smart_home.handle(text, ha)
        if reply:
            return {"skill": "smart_home", "reply": reply}
    for skill, fn in (("units", answer_units), ("countdown", lambda t: answer_countdown(t, now)),
                      ("clock", lambda t: answer_clock(t, now)), ("math", answer_math)):
        reply = fn(text)
        if reply:
            return {"skill": skill, "reply": reply}
    if fetch_json is not None:
        reply = await answer_currency(text, fetch_json)
        if reply:
            return {"skill": "currency", "reply": reply}
    return None


SKILL_SUMMARY = (
    "GÖLGE INSTANT SKILLS (answered exactly, without the model): current time/date and world "
    "clocks, countdowns to dates, calculator and percentages, unit conversion, live weather "
    "(Open-Meteo, also for the phone's current location), ECB exchange rates, news headlines (Google News), flight-search links (Google Flights, no invented prices), YouTube link summaries, owner status report ('durum raporu'), reminders "
    "('20 dakika sonra ... hatırlat', delivered while the GÖLGE page is open), agenda from the owner's "
    "plans + read-only iCal calendar ('bugün programım'), and a morning briefing ('günaydın'/'brifing'). "
    "LAPTOP FROM PHONE CHAT: the owner can type 'laptop: <anything>', 'bilgisayarda chrome aç', "
    "'ekranıma bak' / 'ekran analizi yap' and the paired laptop GÖLGE runs it with all its tools "
    "(apps, files, web, screen analysis) and the real result returns to this chat; destructive "
    "requests need the 'laptop:' prefix and an offline laptop is reported, not queued. Photos, "
    "screenshots and PDFs can be sent with the + button for analysis. "
    "When the owner asks what you can do, mention these naturally. Never claim a reminder was set or a "
    "laptop action was done unless the skill/laptop reply says so.\n"
)


def wants_cloud_skill(text: str) -> bool:
    """Cheap, side-effect-free check: would instant_reply (or the YouTube summary) take this message?

    Used by the local-Qwen path to hand such messages to the cloud endpoint instead of the local model.
    """
    text = str(text or "").strip()
    if missions.mission_goal(text) is not None or (len(text) <= 60 and missions.is_cancel_request(text)):
        return True
    if not text or len(text) > MAX_SKILL_TEXT * 3 or _SKIP_ALL.search(fold_turkish(text)):
        return False
    folded = fold_turkish(text)
    if phone_skills.youtube_request(text) is not None:
        return True
    if len(text) > MAX_SKILL_TEXT:
        return False
    return bool(
        _WEATHER_Q.search(folded) and not _WEATHER_SKIP.search(folded)
        or _STATUS_Q.search(folded) or _AGENDA_Q.search(folded) or _BRIEF_Q.search(folded)
        or (_GREETING.search(folded) and len(folded) <= 30)
        or reminders.has_reminder_intent(text) or reminders._LIST_Q.search(folded) or reminders._CANCEL_Q.search(folded)
        or memory_skills._REMEMBER.match(folded) or memory_skills._REMEMBER_KI.match(folded)
        or memory_skills._LIST.search(folded) or memory_skills._FORGET.match(folded)
        or phone_skills.wants_news(text) or phone_skills.wants_flight(text) or smart_home.wants_smart_home(text) or knowledge_skills.wants_knowledge(text)
        or answer_help(text) or list_skills.wants_lists(text) or expense_skills.wants_expenses(text) or birthday_skills.wants_birthdays(text) or habit_skills.wants_habits(text)
        or alert_skills.parse_alert(text) or alert_skills._LIST.search(folded) or alert_skills._CANCEL.search(folded)
        or re.search(r"\baksam (?:ozet\w*|hazirlik\w*)\b", folded)
        or plan_skills._ADD.search(folded) or plan_skills._LIST.search(folded) or plan_skills._DONE.search(folded) or plan_skills._DEL.search(folded)
        or re.search(r"\bbildirim ayarlarim\b|\bproaktif\b|\bsessiz saat\w*\b|\bsabah (?:brifing\w*|ozet\w*)\b.*\bbildirim|\bkendiliginden uyar", folded)
        or (_FX_Q.search(folded) and _CUR_TOKEN.search(folded) and not _FX_SKIP.search(folded))
        or answer_clock(text) or answer_countdown(text) or answer_units(text) or answer_math(text))
