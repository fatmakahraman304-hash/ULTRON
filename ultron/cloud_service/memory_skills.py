"""Explicit memory commands in chat: "hatırla: …", "neler hatırlıyorsun", "unut: …".

Only an explicit owner request writes or deletes. Secrets are rejected by the
shared memory validator, and ambiguous "forget" requests never delete.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

if __package__:
    from .text_normalization import fold_turkish
    from .memory_history import upsert_owner_memory, delete_owner_memory
else:
    from text_normalization import fold_turkish
    from memory_history import upsert_owner_memory, delete_owner_memory

DEVICE = "golge-chat"
_REMEMBER = re.compile(
    r"^\s*(?:lutfen\s+)?(?:(?:su(?:nu)?|bunu)\s+)?(?:hafizana\s+(?:kaydet|ekle|yaz)|hafizaya\s+(?:kaydet|ekle|yaz)|"
    r"hatirla|aklinda\s+tut|not\s+al|unutma|kaydet)\s*[:\-–,]\s*(.+)$", re.S)
_REMEMBER_KI = re.compile(r"^\s*(?:lutfen\s+)?aklinda\s+tut\s+ki\s+(.+)$", re.S)
_LIST = re.compile(r"\b(?:neler|ne|nelerimi)\s+hatirliyorsun\b|\bhafizanda\s+ne\s+var\b|\bhafizami\s+(?:goster|listele)\b"
                   r"|\bbeni\s+(?:ne\s+kadar\s+)?taniyorsun\b|\bhakkimda\s+ne\s+biliyorsun\b|\bkayitli\s+bilgilerim\b")
_CORRECT = re.compile(r"^\s*(?:lutfen\s+)?(?:duzelt|guncelle|degistir)\s*[:\-–,]\s*(.{2,60}?)\s*(?:=>|->|→|=)\s*(.+)$", re.S)
_HISTORY = re.compile(r"^\s*(?:hafizada\s+)?(.{2,40}?)\s+(?:kaydimin|notumun|bilgimin)\s+(?:gecmisi|eski\s+hali)\s*\??\s*$|^\s*hafizada\s+(.{2,40}?)\s+(?:eskiden|onceden)\s+neydi\s*\??\s*$")
_FORGET = re.compile(r"^\s*(?:lutfen\s+)?(?:unut|hafizadan\s+sil|hafizandan\s+sil|hafizadan\s+cikar)\s*[:\-–,]\s*(.+)$", re.S)


def make_key(text: str) -> str:
    words = re.sub(r"[^\w\s]", " ", text).split()[:6]
    slug = " ".join(words)[:60].strip() or "not"
    return f"not: {slug} #{hashlib.sha1(text.strip().encode()).hexdigest()[:5]}"


def _original_tail(text: str, pattern: re.Pattern) -> str | None:
    """Apply `pattern` on folded text, but return the value in the owner's original characters."""
    folded = fold_turkish(text)
    m = pattern.match(folded)
    if not m:
        return None
    # fold_turkish keeps one output char per input char for Turkish text, so the group's
    # offset in the folded string is the same offset in the original.
    if len(folded) != len(text):
        return m.group(1).strip()
    return text[m.start(1):m.end(1)].strip()


async def handle(text: str, pool: Any, user_id: str) -> str | None:
    if pool is None or len(text) > 1200:
        return None
    value = _original_tail(text, _REMEMBER) or _original_tail(text, _REMEMBER_KI)
    if value:
        try:
            row = await upsert_owner_memory(pool, user_id, DEVICE, "NOTE", make_key(value), value)
        except ValueError as exc:
            if "sensitive" in str(exc):
                return "Şifre, anahtar ya da gizli kod gibi bilgileri hafızaya kaydetmiyorum. Gizli kısmı çıkarıp tekrar söyleyebilirsin."
            return "Bunu hafızaya kaydedemedim; biraz daha kısa ve net yazar mısın?"
        again = row.get("version", 1) > 1
        return f"{'Zaten kayıtlıydı, güncelledim' if again else 'Hafızaya kaydettim'}: “{value[:160]}”"
    if _LIST.search(fold_turkish(text)):
        rows = await pool.fetch(
            "SELECT category,key,value FROM memories WHERE user_id=$1 ORDER BY updated_at DESC LIMIT 10", user_id)
        if not rows:
            return "Hafızamda henüz senin için kayıtlı bir bilgi yok. “hatırla: …” diyerek bir şey öğretebilirsin."
        lines = [f"• {str(r['value'])[:110]}" if str(r["key"]).startswith("not:") else f"• {r['key']}: {str(r['value'])[:90]}"
                 for r in rows]
        return "Hafızamda en son şunlar var:\n" + "\n".join(lines)
    corr = _CORRECT.match(fold_turkish(text))
    if corr:
        needle = fold_turkish(corr.group(1)).strip()
        new_value = (text[corr.start(2):corr.end(2)] if len(fold_turkish(text)) == len(text) else corr.group(2)).strip()
        rows = await pool.fetch("SELECT category,key,value FROM memories WHERE user_id=$1 ORDER BY updated_at DESC LIMIT 200", user_id)
        hits = [r for r in rows if needle in fold_turkish(r["key"]) or needle in fold_turkish(r["value"])]
        if not hits:
            return f"“{needle[:60]}” ile eşleşen bir kayıt bulamadım; yeni bilgi için “hatırla: …” de."
        if len(hits) > 1:
            return (f"“{needle[:60]}” ile {len(hits)} kayıt eşleşiyor, hiçbirini değiştirmedim. Daha belirgin yazar mısın?\n"
                    + "\n".join(f"• {str(r['value'])[:90]}" for r in hits[:5]))
        try:
            await upsert_owner_memory(pool, user_id, DEVICE, hits[0]["category"], hits[0]["key"], new_value)
        except ValueError as exc:
            return "Şifre, anahtar ya da gizli kod gibi bilgileri hafızaya kaydetmiyorum." if "sensitive" in str(exc) else "Bunu kaydedemedim; biraz daha kısa ve net yazar mısın?"
        return f"Düzelttim. Eski: “{str(hits[0]['value'])[:90]}” → yeni: “{new_value[:120]}”. Eski hali geçmişte saklı."
    hist = _HISTORY.match(fold_turkish(text))
    if hist:
        needle = (hist.group(1) or hist.group(2)).strip()
        rows = await pool.fetch("SELECT key,value,version,valid_until FROM memory_history WHERE user_id=$1 ORDER BY valid_until DESC LIMIT 200", user_id)
        old = [r for r in rows if needle in fold_turkish(r["key"]) or needle in fold_turkish(r["value"])]
        if not old:
            return f"“{needle[:60]}” için eski bir sürüm kaydı yok."
        return f"“{needle[:60]}” için eski sürümler:\n" + "\n".join(f"• {r['valid_until']:%d.%m.%Y}'e kadar: {str(r['value'])[:100]}" for r in old[:5])
    target = _original_tail(text, _FORGET)
    if target:
        needle = fold_turkish(target)
        rows = await pool.fetch("SELECT key,value FROM memories WHERE user_id=$1 ORDER BY updated_at DESC LIMIT 200", user_id)
        hits = [r for r in rows if needle in fold_turkish(r["key"]) or needle in fold_turkish(r["value"])]
        if not hits:
            return f"“{target[:80]}” ile eşleşen bir kayıt bulamadım."
        if len(hits) > 1:
            return (f"“{target[:60]}” ile {len(hits)} kayıt eşleşiyor, hiçbirini silmedim. Daha belirgin yazar mısın?\n"
                    + "\n".join(f"• {str(r['value'])[:90]}" for r in hits[:5]))
        await delete_owner_memory(pool, user_id, hits[0]["key"])
        return f"Unuttum: “{str(hits[0]['value'])[:120]}”"
    return None
