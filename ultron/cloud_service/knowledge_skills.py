"""Keyless knowledge skills: Wikipedia, prayer times, earthquakes, sun & moon, crypto prices.

Every answer names its source; any upstream failure says so instead of guessing.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

if __package__:
    from .text_normalization import fold_turkish
else:
    from text_normalization import fold_turkish

FetchJson = Callable[[str, str, int], Awaitable[dict]]
HOME_TZ = ZoneInfo("Europe/Istanbul")


def _home():
    if __package__:
        from .instant_skills import home_location
    else:
        from instant_skills import home_location
    return home_location()


def _fmt():
    if __package__:
        from .instant_skills import format_number_tr, format_date_tr
    else:
        from instant_skills import format_number_tr, format_date_tr
    return format_number_tr, format_date_tr


# ── Wikipedia ───────────────────────────────────────────────────────────────

_WIKI_Q = re.compile(r"^\s*(?:vikipedi(?:'?(?:de|den|ye))?[:,]?\s+(.+?)(?:\s+(?:hakkinda|nedir|kimdir|ara))?|(.+?)\s+vikipedi(?:'?de)?|"
                     r"(.+?)\s+kimdir|(.+?)\s+hakkinda\s+vikipedi\w*)\s*[?.!]*$")


def wiki_subject(text: str) -> str | None:
    f = fold_turkish(text)
    if len(f) > 90:
        return None
    m = _WIKI_Q.match(f)
    if not m:
        return None
    subject = next(g for g in m.groups() if g).strip(" '\"")
    subject = re.sub(r"\b(?:bana|lutfen|bir|su|hakkinda|bilgi|ver|anlat|soyle)\b", " ", subject)
    subject = re.sub(r"\s+", " ", subject).strip()
    if not 2 <= len(subject) <= 60 or re.search(r"\b(?:ben|sen|o|bu|su|bunu|sunu)\b$", subject):
        return None
    # recover the original capitalisation/diacritics for the lookup
    original = re.sub(r"(?i)\b(vikipedi\w*|kimdir|nedir|hakkinda|hakkında|ara|bana|lütfen|lutfen|bilgi|ver|anlat|söyle|soyle)\b|['’]?(de|den|ye)\b", " ", text)
    original = re.sub(r"[?.!:,]+", " ", original)
    original = re.sub(r"\s+", " ", original).strip()
    return original[:60] or subject


async def answer_wiki(text: str, fetch_json: FetchJson) -> str | None:
    subject = wiki_subject(text)
    if not subject:
        return None
    try:
        found = await fetch_json("https://tr.wikipedia.org/w/rest.php/v1/search/title?" + urlencode({"q": subject, "limit": 1}),
                                 "wiki-search:" + fold_turkish(subject), 3600)
        pages = found.get("pages") or []
        if not pages:
            return f"Vikipedi'de “{subject}” için bir madde bulamadım."
        title = str(pages[0].get("title") or subject)
        data = await fetch_json("https://tr.wikipedia.org/api/rest_v1/page/summary/" + quote(title.replace(" ", "_"), safe=""),
                                "wiki-summary:" + fold_turkish(title), 3600)
    except Exception:
        return "Vikipedi'ye şu an ulaşamadım; uydurma bilgi vermemek için bir şey söylemiyorum."
    extract = re.sub(r"\s+", " ", str(data.get("extract") or "")).strip()
    if data.get("type") == "disambiguation" or not extract:
        return f"“{title}” birden fazla anlama geliyor; hangisini kastettiğini biraz açar mısın?"
    sentences = re.split(r"(?<=[.!?])\s+", extract)
    short = ""
    for s in sentences:
        if len(short) + len(s) > 520:
            break
        short += (" " if short else "") + s
    short = short or extract[:520]
    link = ((data.get("content_urls") or {}).get("desktop") or {}).get("page", "")
    return f"{title}: {short}\nKaynak: Vikipedi {link}".strip()


# ── prayer times (Aladhan, Diyanet method 13) ───────────────────────────────

_PRAYER_Q = re.compile(r"\bnamaz vakit\w*|\bezan\w*\b.*\b(?:ne zaman|saat kac|kacta)\b|\bezan vakti\b|\b(?:iftar|sahur|imsak)\b.*\b(?:ne zaman|saat kac|kacta|vakti)\b|\bnamaz saati\b")
_PRAYERS = (("Fajr", "İmsak"), ("Sunrise", "Güneş"), ("Dhuhr", "Öğle"), ("Asr", "İkindi"), ("Maghrib", "Akşam"), ("Isha", "Yatsı"))


def wants_prayer(text: str) -> bool:
    return bool(_PRAYER_Q.search(fold_turkish(text))) and len(text) <= 100


async def answer_prayer(text: str, fetch_json: FetchJson, now: datetime | None = None, location: dict | None = None) -> str | None:
    if not wants_prayer(text):
        return None
    f = fold_turkish(text)
    label, lat, lon = _home()
    place = re.search(r"\b([a-z]{3,}(?: [a-z]{3,})?)'?(?:da|de|ta|te|nda|nde|icin)\b", f)
    try:
        if place and place.group(1) not in ("bugun", "yarin", "simdi", "burada", "bu", "su"):
            geo = await fetch_json("https://geocoding-api.open-meteo.com/v1/search?" + urlencode(
                {"name": place.group(1), "count": 1, "language": "tr", "format": "json"}), "geo:" + place.group(1), 86400)
            hit = (geo.get("results") or [None])[0]
            if hit:
                label, lat, lon = str(hit.get("name") or place.group(1)), float(hit["latitude"]), float(hit["longitude"])
        elif location:
            label, lat, lon = "Bulunduğun konum", location["lat"], location["lon"]
        data = await fetch_json(
            f"https://api.aladhan.com/v1/timings?latitude={round(lat, 2)}&longitude={round(lon, 2)}&method=13",
            f"prayer:{round(lat, 2)}:{round(lon, 2)}:{(now or datetime.now(timezone.utc)).date()}", 1800)
        timings = data["data"]["timings"]
        tz = ZoneInfo(data["data"]["meta"]["timezone"])
    except Exception:
        return "Namaz vakti kaynağına şu an ulaşamadım; yanlış saat vermemek için tahmin yürütmüyorum."
    local = (now or datetime.now(timezone.utc)).astimezone(tz)
    rows, upcoming = [], None
    for key, name in _PRAYERS:
        hh, mm = map(int, str(timings[key])[:5].split(":"))
        at = local.replace(hour=hh, minute=mm, second=0, microsecond=0)
        rows.append((name, f"{hh:02d}:{mm:02d}"))
        if upcoming is None and at > local:
            upcoming = (name, at)
    asked = next((n for n, pat in (("Akşam", r"iftar|aksam ezan"), ("İmsak", r"sahur|imsak"), ("Öğle", r"ogle ezan"), ("İkindi", r"ikindi"), ("Yatsı", r"yatsi"))
                  if re.search(pat, f)), None)
    if asked:
        t = dict(rows)[asked]
        extra = f" {'İftar' if asked == 'Akşam' and 'iftar' in f else 'Sahur bitişi (imsak)' if asked == 'İmsak' else asked + ' ezanı'} {t}."
        return f"{label} için bugün{extra} (Diyanet yöntemi, Aladhan)"
    nxt = f"\nSıradaki: {upcoming[0]} — {int((upcoming[1] - local).total_seconds() // 60)} dk sonra." if upcoming else "\nBugünün vakitleri bitti; yarın İmsak ile başlıyor."
    return f"{label} namaz vakitleri:\n" + "\n".join(f"• {n}: {t}" for n, t in rows) + nxt + "\nKaynak: Aladhan (Diyanet yöntemi)."


# ── earthquakes (USGS) ──────────────────────────────────────────────────────

_QUAKE_Q = re.compile(r"\bdeprem\w*\b")
_QUAKE_SKIP = re.compile(r"\b(?:nedir|nasil olusur|neden|sigorta\w*|canta\w*|hazirlik\w*|onlem\w*|tahmin\w*|olur mu|olacak mi|ne yapmaliyiz|ne yapilir|neler olmali)\b")


def wants_quake(text: str) -> bool:
    f = fold_turkish(text)
    return bool(_QUAKE_Q.search(f)) and not _QUAKE_SKIP.search(f) and len(f) <= 80


async def answer_quake(text: str, fetch_json: FetchJson, now: datetime | None = None) -> str | None:
    if not wants_quake(text):
        return None
    try:
        data = await fetch_json(
            "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minmagnitude=3.5&orderby=time&limit=6"
            "&minlatitude=34&maxlatitude=43&minlongitude=25&maxlongitude=46", "quakes:tr", 300)
        feats = data["features"]
    except Exception:
        return "Deprem kaynağına şu an ulaşamadım; bu yüzden bir şey söylemiyorum. Resmî bilgi için AFAD/Kandilli'ye bakabilirsin."
    if not feats:
        return "Son günlerde Türkiye ve çevresinde 3.5 üstü kayıtlı deprem görünmüyor (USGS)."
    lines = []
    for ft in feats[:5]:
        p = ft["properties"]
        when = datetime.fromtimestamp(p["time"] / 1000, timezone.utc).astimezone(HOME_TZ)
        lines.append(f"• M{p['mag']:.1f} — {str(p.get('place') or '?')[:60]} — {when:%d.%m %H:%M}")
    return "Son depremler (M3.5+, Türkiye ve çevresi):\n" + "\n".join(lines) + "\nKaynak: USGS. Resmî açıklama için AFAD/Kandilli esastır."


# ── sun & moon ──────────────────────────────────────────────────────────────

_SUN_Q = re.compile(r"\bgun (?:dogum|batim)\w*|\bgunes ne zaman (?:dogar|batar)\b|\bgunes (?:dogus|batis)\w*|\bne zaman (?:karanlik|aydinlik) olur\b|\bgun batimi\b")
_MOON_Q = re.compile(r"\bay evresi\b|\bay (?:ne durumda|hangi evrede)\b|\bdolunay\w*|\byeni ay\b|\bhilal\b|\bay kac gunluk\b")
_SYNODIC = 29.530588853
_NEW_MOON_REF = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)


def moon_phase(at: datetime) -> dict:
    age = ((at - _NEW_MOON_REF).total_seconds() / 86400) % _SYNODIC
    illum = (1 - math.cos(2 * math.pi * age / _SYNODIC)) / 2
    names = ("Yeni ay", "Hilal (büyüyen)", "İlk dördün", "Şişkin ay (büyüyen)", "Dolunay", "Şişkin ay (küçülen)", "Son dördün", "Hilal (küçülen)")
    name = names[int(((age / _SYNODIC) * 8 + 0.5) % 8)]
    to_full = (_SYNODIC / 2 - age) % _SYNODIC
    to_new = (_SYNODIC - age) % _SYNODIC
    return {"name": name, "illumination": round(illum * 100), "age_days": round(age, 1),
            "next_full": at + timedelta(days=to_full), "next_new": at + timedelta(days=to_new)}


def wants_sun_moon(text: str) -> bool:
    f = fold_turkish(text)
    return len(f) <= 90 and bool(_SUN_Q.search(f) or _MOON_Q.search(f))


async def answer_sun_moon(text: str, fetch_json: FetchJson, now: datetime | None = None, location: dict | None = None) -> str | None:
    f = fold_turkish(text)
    if len(f) > 90:
        return None
    format_number_tr, format_date_tr = _fmt()
    now = now or datetime.now(timezone.utc)
    if _MOON_Q.search(f):
        m = moon_phase(now)
        nf, nn = m["next_full"].astimezone(HOME_TZ), m["next_new"].astimezone(HOME_TZ)
        return (f"Ay şu an: {m['name']} — yüzde {m['illumination']} aydınlık, ayın {format_number_tr(m['age_days'])}. günü.\n"
                f"Sonraki dolunay: {format_date_tr(nf.date())}\nSonraki yeni ay: {format_date_tr(nn.date())}\n(Astronomik hesap; ±1 gün sapabilir.)")
    if not _SUN_Q.search(f):
        return None
    label, lat, lon = _home()
    if location:
        label, lat, lon = "Bulunduğun konum", location["lat"], location["lon"]
    try:
        data = await fetch_json("https://api.open-meteo.com/v1/forecast?" + urlencode(
            {"latitude": round(lat, 2), "longitude": round(lon, 2), "daily": "sunrise,sunset", "timezone": "auto", "forecast_days": 2}),
            f"sun:{round(lat, 2)}:{round(lon, 2)}:{now.date()}", 3600)
        rises, sets = data["daily"]["sunrise"], data["daily"]["sunset"]
    except Exception:
        return "Güneş saatleri kaynağına şu an ulaşamadım."
    idx = 1 if "yarin" in f else 0
    rise, sett = rises[idx][11:16], sets[idx][11:16]
    when = "Yarın" if idx else "Bugün"
    rh, rm = map(int, rise.split(":"))
    sh, sm = map(int, sett.split(":"))
    length = (sh * 60 + sm) - (rh * 60 + rm)
    return f"{label} — {when} gün doğumu {rise}, gün batımı {sett} (gün uzunluğu {length // 60} sa {length % 60} dk). Kaynak: Open-Meteo."


# ── crypto (CoinGecko) ──────────────────────────────────────────────────────

_COINS = {"bitcoin": "bitcoin", "btc": "bitcoin", "ethereum": "ethereum", "eth": "ethereum", "solana": "solana", "sol": "solana",
          "dogecoin": "dogecoin", "doge": "dogecoin", "xrp": "ripple", "ripple": "ripple", "bnb": "binancecoin",
          "cardano": "cardano", "ada": "cardano", "avalanche": "avalanche-2", "avax": "avalanche-2", "litecoin": "litecoin"}
_COIN_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, _COINS), key=len, reverse=True)) + r")\b")
_COIN_SKIP = re.compile(r"\b(?:neden|niye|nedir|alayim mi|satayim mi|yukselir mi|duser mi|tahmin|yorum|analiz|nasil)\b")


def wants_crypto(text: str) -> bool:
    f = fold_turkish(text)
    return len(f) <= 70 and bool(_COIN_RE.search(f)) and not _COIN_SKIP.search(f) and bool(re.search(r"\b(?:kac|fiyat\w*|ne kadar|kur\w*|deger\w*|dolar|tl)\b", f))


async def answer_crypto(text: str, fetch_json: FetchJson) -> str | None:
    if not wants_crypto(text):
        return None
    format_number_tr, _ = _fmt()
    f = fold_turkish(text)
    coin = _COINS[_COIN_RE.search(f).group(1)]
    try:
        data = await fetch_json("https://api.coingecko.com/api/v3/simple/price?" + urlencode(
            {"ids": coin, "vs_currencies": "usd,try", "include_24hr_change": "true"}), f"coin:{coin}", 120)
        row = data[coin]
        usd, try_, chg = float(row["usd"]), float(row["try"]), row.get("usd_24h_change")
    except Exception:
        return "Kripto fiyat kaynağına şu an ulaşamadım; yanlış fiyat vermemek için bir şey söylemiyorum."
    trend = f" Son 24 saatte {'+' if chg >= 0 else ''}{format_number_tr(round(float(chg), 1))}%." if chg is not None else ""
    return (f"{coin.capitalize()}: {format_number_tr(round(usd, 2))} $ (≈ {format_number_tr(round(try_))} ₺).{trend}\n"
            "Kaynak: CoinGecko — yatırım tavsiyesi değildir, fiyatlar anlık oynar.")


def wants_knowledge(text: str) -> bool:
    return wiki_subject(text) is not None or wants_prayer(text) or wants_quake(text) or wants_sun_moon(text) or wants_crypto(text)


async def answer(text: str, fetch_json: FetchJson, now: datetime | None = None, location: dict | None = None) -> tuple[str, str] | None:
    for name, coro in (("crypto", answer_crypto(text, fetch_json) if wants_crypto(text) else None),
                       ("prayer", answer_prayer(text, fetch_json, now, location) if wants_prayer(text) else None),
                       ("quake", answer_quake(text, fetch_json, now) if wants_quake(text) else None),
                       ("sun_moon", answer_sun_moon(text, fetch_json, now, location) if wants_sun_moon(text) else None),
                       ("wiki", answer_wiki(text, fetch_json) if wiki_subject(text) else None)):
        if coro is not None:
            reply = await coro
            if reply:
                return name, reply
    return None
