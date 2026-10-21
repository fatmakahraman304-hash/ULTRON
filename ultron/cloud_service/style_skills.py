"""Persistent conversation style: "kısa cevap ver", "samimi ol", "bana sen de", "bana Murat diye hitap et".

The style lives in owner_prefs["style"] and is appended to the chat and live-voice
system instructions, so it applies on every device. It only changes tone and length —
never safety rules, approvals or tool permissions.
"""
from __future__ import annotations

import re
from typing import Any

if __package__:
    from .text_normalization import fold_turkish
    from . import proactive
else:
    from text_normalization import fold_turkish
    import proactive

KEY = "style"
LENGTHS = {"short": "kısa", "medium": "orta uzunlukta", "long": "ayrıntılı"}
TONES = {"warm": "samimi", "formal": "resmî", "witty": "esprili", "serious": "ciddi"}

_LEN = re.compile(r"^(?:lutfen\s+)?(?:artik\s+)?(?:(kisa|kisaca|ozet|ozetle|orta|ortalama|detayli|ayrintili|uzun)\s+(?:cevap\w*|yanit\w*|konus\w*|anlat\w*)(?:\s+(?:ver|yaz|ol))?|(?:cevap\w*|yanit\w*)\s+(kisa|orta|detayli|ayrintili|uzun)\s+(?:ver|olsun|tut)|(kisa|detayli|ayrintili)\s+(?:ol|anlat))$")
_TONE = re.compile(r"^(?:lutfen\s+)?(?:artik\s+)?(?:biraz\s+|daha\s+)?(samimi|resmi|esprili|saka\w*|mizahi|ciddi)\s+(?:ol|konus|cevap\w*\s+ver|davran)\w*$")
_ADDR = re.compile(r"^(?:lutfen\s+)?(?:bana\s+)?(sen|siz)\s+(?:diye\s+hitap\s+et|de|diye\s+konus|diye\s+seslen)\w*$|^(?:bana\s+)?(sen|siz)\s+diye\s+hitap\w*$|^(?:benimle\s+)?(sen|siz)\s+(?:diye\s+)?konus\w*$")
_EMOJI = re.compile(r"^(?:lutfen\s+)?emoji\w*\s+(kullanma|kullan|ekleme|ekle|yazma)\s*$|^(?:lutfen\s+)?emoji\s+(?:kullanma|kullan)\w*$")
_SHOW = re.compile(r"^(?:konusma\s+tarzim|tarzim|konusma\s+ayarlarim|nasil\s+konusuyorsun|konusma\s+tarzini\s+(?:goster|soyle))\s*(?:ne)?\s*\??$")
_RESET = re.compile(r"^(?:konusma\s+)?tarz\w*\s+(?:sifirla|varsayilana\s+don)\w*$|^(?:konusma\s+)?(?:ayarlarini|tarzini)\s+sifirla$")
_NAME = re.compile(r"\bbana\s+([^\W\d_]{2,20}(?:\s+[^\W\d_]{2,20})?)\s+diye\s+(?:hitap\s+et|seslen|cagir|[cç]a[gğ][iı]r)\w*", re.I)
_NAME_BAD = {"sen", "siz", "efendim"}  # address forms are handled by _ADDR, not names


def wants_style(text: str) -> bool:
    f = fold_turkish(text)
    if len(f) > 70:
        return False
    return bool(_LEN.match(f) or _TONE.match(f) or _ADDR.match(f) or _EMOJI.match(f)
                or _SHOW.match(f) or _RESET.match(f) or _NAME.search(f))


async def get_style(pool: Any, user_id: str) -> dict:
    if pool is None:
        return {}
    try:
        value = await proactive.get_extra(pool, user_id, KEY, {})
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def style_instruction(style: dict | None) -> str:
    """English instruction block for the model; empty when nothing was chosen."""
    s = style or {}
    lines = []
    length = s.get("length")
    if length == "short":
        lines.append("Keep answers very short: one or two sentences unless the owner asks for more.")
    elif length == "long":
        lines.append("Give thorough, step-by-step answers with useful detail.")
    elif length == "medium":
        lines.append("Keep answers moderately short and well structured.")
    lines.append({
        "warm": "Tone: warm, friendly and informal.",
        "formal": "Tone: polite and formal; no slang.",
        "witty": "Tone: light and witty; a short joke is welcome when the topic is not serious.",
        "serious": "Tone: serious and businesslike; no jokes.",
    }.get(s.get("tone"), ""))
    if s.get("address") == "siz":
        lines.append("Address the owner formally with 'siz' in Turkish.")
    elif s.get("address") == "sen":
        lines.append("Address the owner informally with 'sen' in Turkish.")
    if s.get("name"):
        lines.append(f"Call the owner “{str(s['name'])[:30]}” when addressing them.")
    if s.get("emoji") is False:
        lines.append("Do not use emoji.")
    elif s.get("emoji") is True:
        lines.append("A few fitting emoji are welcome.")
    lines = [x for x in lines if x]
    if not lines:
        return ""
    return ("\n\nOWNER STYLE PREFERENCES (chosen by the owner; they change tone and length only, "
            "never safety rules or approvals):\n- " + "\n- ".join(lines) + "\n")


def describe(style: dict) -> str:
    if not style:
        return "Henüz özel bir konuşma tarzı seçmedin. Örn. “kısa cevap ver”, “samimi ol”, “bana sen de”, “emoji kullanma”."
    parts = []
    if style.get("length"):
        parts.append(f"cevap uzunluğu: {LENGTHS.get(style['length'], style['length'])}")
    if style.get("tone"):
        parts.append(f"ton: {TONES.get(style['tone'], style['tone'])}")
    if style.get("address"):
        parts.append(f"hitap: {style['address']}")
    if style.get("name"):
        parts.append(f"sana “{style['name']}” diyorum")
    if "emoji" in style:
        parts.append("emoji: " + ("açık" if style["emoji"] else "kapalı"))
    return "Konuşma tarzın — " + ", ".join(parts) + ". Sıfırlamak için “tarzı sıfırla”."


async def _save(pool, user_id, **changes) -> dict:
    style = await get_style(pool, user_id)
    style.update(changes)
    await proactive.set_extra(pool, user_id, KEY, style)
    return style


async def handle(text: str, pool: Any, user_id: str) -> str | None:
    if pool is None or not wants_style(text):
        return None
    f = fold_turkish(text)
    if _RESET.match(f):
        await proactive.set_extra(pool, user_id, KEY, {})
        return "Konuşma tarzını varsayılana döndürdüm."
    if _SHOW.match(f):
        return describe(await get_style(pool, user_id))
    m = _NAME.search(text.strip())
    if m:
        name = " ".join(w.capitalize() if w.islower() else w for w in m.group(1).split())
        if fold_turkish(name) not in _NAME_BAD:
            await _save(pool, user_id, name=name)
            return f"Tamam, bundan sonra sana {name} diyeceğim."
    m = _LEN.match(f)
    if m:
        word = next(g for g in m.groups() if g)
        length = "short" if word.startswith(("kisa", "ozet")) else "long" if word in ("detayli", "ayrintili", "uzun") else "medium"
        await _save(pool, user_id, length=length)
        return {"short": "Tamam, kısa ve net konuşacağım.", "medium": "Tamam, orta uzunlukta cevap vereceğim.",
                "long": "Tamam, ayrıntılı anlatacağım."}[length]
    m = _TONE.match(f)
    if m:
        w = m.group(1)
        tone = "warm" if w == "samimi" else "formal" if w == "resmi" else "serious" if w == "ciddi" else "witty"
        await _save(pool, user_id, tone=tone)
        return f"Tamam, bundan sonra {TONES[tone]} olacağım."
    m = _ADDR.match(f)
    if m:
        addr = next(g for g in m.groups() if g)
        await _save(pool, user_id, address=addr)
        return "Tamam, sana “sen” diyeceğim." if addr == "sen" else "Tamam, sana “siz” diye hitap edeceğim."
    m = _EMOJI.match(f)
    if m:
        on = (m.group(1) or "kullan") in ("kullan", "ekle")
        await _save(pool, user_id, emoji=on)
        return "Tamam, emoji kullanacağım." if on else "Tamam, emoji kullanmayacağım."
    return None
