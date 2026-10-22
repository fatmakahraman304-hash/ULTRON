"""Navigation helpers that open real maps: directions, "yakınımda …", traffic.

No routes or ETAs are invented: the reply is a prefilled Apple Maps / Google Maps link (the phone uses
its own location when none is sent). Phone coordinates arrive rounded to ~1 km and are never stored.
"""
from __future__ import annotations

import re
from urllib.parse import quote, urlencode

if __package__:
    from .text_normalization import fold_turkish
    from .reminders import fold_with_map
else:
    from text_normalization import fold_turkish
    from reminders import fold_with_map

_DIR_KW = r"(?:yol tarifi|yol tarif\w*|rota\w*|nasil giderim|nasil gidilir|nasil gidebilirim|navigasyon\w*)"
_MODE = (("walking", r"yuruyerek|yaya"), ("transit", r"toplu tasima|otobus|metro|tren|vapur"), ("bicycling", r"bisikletle|bisiklet"), ("driving", r"arabayla|araba|aracla|otomobil"))
_FROM_TO = re.compile(r"^\s*(?:lutfen\s+)?([a-z][a-z ]{1,30}?)'?(?:dan|den|tan|ten)\s+([a-z][a-z ]{1,30}?)'?(?:ya|ye|a|e|na|ne)\s+(?:\w+\s+){0,2}" + _DIR_KW + r"\s*(?:ver|goster|al|lazim)?\s*\??\s*$")
_TO = re.compile(r"^\s*(?:lutfen\s+)?([a-z][a-z ]{1,30}?)'?(?:ya|ye|a|e|na|ne)\s+(?:\w+\s+){0,2}" + _DIR_KW + r"\s*(?:ver|goster|al|lazim)?\s*\??\s*$")
_TO_B = re.compile(r"^\s*" + _DIR_KW + r"\s*[:\-]?\s*([a-z][a-z ]{1,30}?)(?:'(?:ya|ye|a|e|na|ne))?\s*\??\s*$")
_NEARBY = re.compile(r"^\s*(?:lutfen\s+)?(?:en\s+)?(?:yakin(?:imda(?:ki)?|daki|da)?|etrafimda(?:ki)?)\s+(?:bir\s+)?([a-z][a-z ]{2,28}?)(?:\s+(?:var mi|nerede|goster|bul|ara))?\s*\??\s*$"
                     r"|^\s*(?:lutfen\s+)?([a-z][a-z ]{2,28}?)\s+(?:nerede|bul)\s+yakin\w*\s*\??\s*$")
_TRAFFIC = re.compile(r"^\s*(?:trafik(?: durumu)?(?: nasil)?|yollar nasil|trafikte durum ne)\s*\??\s*$")
_PLACE_STOP = {"ev", "eve", "buraya", "buradan", "burasi", "bugun", "yarin", "simdi", "lutfen", "bana"}
_QUESTION_WORDS = re.compile(r"\b(?:nasil|nedir|neden|niye|ne|hangi|kim|nerede|kac|alinir|yapilir|yazilir|yaz\w*|uygulama\w*|plan\w*|kod\w*|program\w*|ac|oner\w*)\b")
_POI = {"eczane", "hastane", "market", "benzin", "akaryakit", "kafe", "kahve", "restoran", "lokanta", "atm", "banka", "otopark", "sarj", "park", "cami",
        "okul", "avm", "alisveris", "firin", "berber", "kuafor", "otel", "sinema", "postane", "tamirci", "veteriner", "doktor", "bakkal", "manav",
        "kasap", "pastane", "taksi", "durak", "metro", "tuvalet", "polis", "itfaiye", "kutuphane", "muze", "spor", "gym", "camasirhane", "kirtasiye", "noter"}


def _mode(f: str) -> str:
    return next((m for m, pat in _MODE if re.search(r"\b(?:" + pat + r")\b", f)), "driving")


def _place(original: str, idx: list[int], span: tuple[int, int]) -> str:
    raw = original[idx[span[0]]: idx[span[1] - 1] + 1]
    return re.sub(r"\s+", " ", raw).strip(" '’")[:40]


def wants_navigation(text: str) -> bool:
    return len(text) <= 100 and answer(text) is not None


def answer(text: str, location: dict | None = None) -> str | None:
    f, idx = fold_with_map(text)
    f = f.strip()
    if len(f) > 100:
        return None
    if _TRAFFIC.match(f):
        center = f"{location['lat']},{location['lon']}" if location else "35.13,33.43"
        url = "https://www.google.com/maps/@?" + urlencode({"api": 1, "map_action": "map", "center": center, "zoom": 11, "layer": "traffic"}, safe=",")
        return ("Canlı trafik haritası:\n" + url + ("" if location else "\n(Konum izni vermediğin için varsayılan şehir merkezini açtım.)"))
    m = _FROM_TO.match(f)
    if m:
        origin, dest = _place(text, idx, m.span(1)), _place(text, idx, m.span(2))
    else:
        m = _TO.match(f) or _TO_B.match(f)
        if not m:
            m = _NEARBY.match(f)
            if not m:
                return None
            term = _place(text, idx, m.span(1) if m.group(1) else m.span(2))
            if not term or not (set(fold_turkish(term).split()) & _POI):
                return None          # only real place categories; "yakın arkadaşım" is chat
            q = {"q": term}
            if location:
                q["sll"] = f"{location['lat']},{location['lon']}"
            apple = "https://maps.apple.com/?" + urlencode(q, safe=",")
            google = "https://www.google.com/maps/search/?" + urlencode({"api": 1, "query": term})
            where = "bulunduğun konumun çevresinde" if location else "telefonunun konumuna göre"
            return f"“{term}” için {where} harita araması:\nApple Haritalar: {apple}\nGoogle Haritalar: {google}"
        origin, dest = "", _place(text, idx, m.span(1))
    if not dest or len(dest.split()) > 3 or fold_turkish(dest) in _PLACE_STOP or _QUESTION_WORDS.search(fold_turkish(dest)):
        return None
    mode = _mode(f)
    google_params = {"api": 1, "destination": dest, "travelmode": mode}
    apple_params = {"daddr": dest, "dirflg": {"driving": "d", "walking": "w", "transit": "r", "bicycling": "w"}[mode]}
    if origin:
        google_params["origin"], apple_params["saddr"] = origin, origin
    elif location:
        google_params["origin"] = apple_params["saddr"] = f"{location['lat']},{location['lon']}"
    label = {"driving": "araba", "walking": "yürüyerek", "transit": "toplu taşıma", "bicycling": "bisiklet"}[mode]
    start = origin or ("bulunduğun konum" if location else "mevcut konumun")
    return (f"{start} → {dest} ({label}) için yol tarifi:\nApple Haritalar: https://maps.apple.com/?{urlencode(apple_params, quote_via=quote)}\n"
            f"Google Haritalar: https://www.google.com/maps/dir/?{urlencode(google_params, quote_via=quote)}\n"
            "Süre ve trafik bilgisini harita uygulaması canlı gösterir; ben tahmin yürütmüyorum.")
