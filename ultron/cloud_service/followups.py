"""Short follow-ups after a skill answer: "peki yarın?", "ya Londra?", "ya euro?", "spor?".

Only applied when the previous assistant message was a skill reply (device_id 'golge-skill:<name>')
AND the new message is a very short question carrying an explicit follow-up marker. The text is
rewritten into the full request and still goes through the normal skill router; if no skill takes
it, the original message continues to the language model unchanged.
"""
from __future__ import annotations

import re

if __package__:
    from .text_normalization import fold_turkish
    from .reminders import fold_with_map
else:
    from text_normalization import fold_turkish
    from reminders import fold_with_map

SKILL_PREFIX = "golge-skill:"
_MARK = re.compile(r"^\s*(?:peki|ya|ya da|bir de|ayrica|bide)\b[\s,]*(.+?)\s*\??\s*$|^\s*(.{2,40}?)\s*\?\s*$", re.S)
_CHAT_WORDS = {"tesekkurler", "tamam", "evet", "hayir", "harika", "super", "anladim", "sagol", "merhaba", "olur", "iyi", "guzel",
               "nasilsin", "ne", "neden", "nasil", "kim", "nerede", "nezaman", "ok", "peki", "ya", "bu", "su", "o", "hmm", "yok", "var",
               "bilmiyorum", "emin", "misin", "mi", "mu", "sence", "gercekten", "ciddi", "ciddi misin", "sen", "ben", "biz", "siz", "onlar", "bunlar", "hepsi", "hicbiri", "hangisi", "kim", "kimin"}
_DAY = re.compile(r"^(bugun|yarin|obur gun|haftaya|bu hafta)$")
_NEWS_TOPICS = ("teknoloji", "spor", "ekonomi", "dunya", "bilim", "saglik", "magazin", "turkiye", "gundem")
_FX = {"dolar": "dolar kaç tl", "euro": "euro kaç tl", "avro": "euro kaç tl", "sterlin": "sterlin kaç tl", "usd": "dolar kaç tl", "eur": "euro kaç tl"}
_COINS = ("bitcoin", "btc", "ethereum", "eth", "solana", "sol", "dogecoin", "doge", "xrp", "bnb", "cardano", "litecoin")


def _core(text: str) -> tuple[str, str] | None:
    """Return (original-case core phrase, folded core phrase) for a marked short follow-up."""
    m = _MARK.match(text)
    if not m:
        return None
    marked = m.group(1) is not None
    core = (m.group(1) or m.group(2) or "").strip(" ?!.,")
    folded = fold_turkish(core)
    words = folded.split()
    if not 1 <= len(words) <= 3 or folded in _CHAT_WORDS or any(w in _CHAT_WORDS for w in words[:1]) and len(words) == 1:
        return None
    if not marked and "?" not in text:
        return None
    return core, folded


def _place(core: str, folded: str) -> str | None:
    if not re.fullmatch(r"[a-z]{3,}(?: [a-z]{3,})?(?:'?(?:da|de|ta|te|nda|nde|icin))?", folded):
        return None
    return re.sub(r"'?(?:da|de|ta|te|nda|nde|için|icin)$", "", core.strip(), flags=re.IGNORECASE).strip("' ")


def resolve(text: str, previous_device_id: str | None) -> str | None:
    """Return the explicit request for a follow-up, or None."""
    if not previous_device_id or not previous_device_id.startswith(SKILL_PREFIX):
        return None
    skill = previous_device_id[len(SKILL_PREFIX):]
    got = _core(text)
    if got is None:
        return None
    core, folded = got
    if skill == "weather":
        if _DAY.match(folded):
            return f"{core} hava nasıl"
        place = _place(core, folded)
        return f"{place}'da hava nasıl" if place else None
    if skill in ("currency", "crypto"):
        key = folded.split()[0]
        if key in _FX:
            return _FX[key]
        if key in _COINS:
            return f"{core.split()[0]} fiyatı"
        return None
    if skill == "news":
        for topic in _NEWS_TOPICS:
            if folded.startswith(topic):
                return f"{topic if topic != 'gundem' else 'gündem'} haberleri"
        return None
    if skill == "clock":
        place = _place(core, folded)
        return f"{place}'da saat kaç" if place else None
    if skill == "prayer":
        place = _place(core, folded)
        return f"{place}'da namaz vakitleri" if place else None
    if skill == "sun_moon" and _DAY.match(folded):
        return f"{core} gün doğumu kaçta"
    return None
