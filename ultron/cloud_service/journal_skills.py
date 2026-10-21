"""Private journal: "günlüğe yaz: bugün çok verimliydim", "günlüğüm", "dünkü günlüğüm", "günlüğümde kahve geçenler",
"son günlük kaydını sil". Owner-scoped; secrets are refused like in memory."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

if __package__:
    from .text_normalization import fold_turkish
    from .reminders import HOME_TZ
    from .memory_safety import contains_common_secret
else:
    from text_normalization import fold_turkish
    from reminders import HOME_TZ
    from memory_safety import contains_common_secret

_WRITE = re.compile(r"^\s*(?:(?:gunluge|gunlugume)\s+(?:yaz|ekle|kaydet)\s*[:\-–,]|(?:gunluk|gunluk\s+girdisi|gunluk\s+notu)\s*:)\s*(.+)$", re.S)
_READ = re.compile(r"^(?:(bugunku|dunku|bu haftaki|gecen haftaki|son)\s+)?gunlu[gk]\w*(?:\s+(?:goster|oku|listele))?\s*\??$|^gunlugum(?:u)?\s+(?:goster|oku|listele)$")
_SEARCH = re.compile(r"^gunlug\w*\s+(.{2,30}?)\s+(?:gecen(?:ler|leri)?|ara)\s*\??$|^gunlukte\s+(.{2,30}?)\s+ara\s*\??$")
_DELETE = re.compile(r"^son\s+gunluk\s+(?:kayd\w*|girdi\w*|not\w*)\s*(?:sil|kaldir)\w*$|^gunlugumun\s+sonuncusunu\s+sil$")


def wants_journal(text: str) -> bool:
    f = fold_turkish(text)
    return len(f) <= 1100 and bool(_WRITE.match(f) or _READ.match(f) or _SEARCH.match(f) or _DELETE.match(f))


def _tail(text: str, folded: str, m: re.Match) -> str:
    return (text[m.start(1):m.end(1)] if len(folded) == len(text) else m.group(1)).strip()


def _fmt(row) -> str:
    return f"• {row['day']:%d.%m} — {str(row['entry'])[:140]}"


async def handle(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    if pool is None or not wants_journal(text):
        return None
    f = fold_turkish(text)
    today = (now or datetime.now(timezone.utc)).astimezone(HOME_TZ).date()
    m = _WRITE.match(f)
    if m:
        entry = _tail(text, f, m)
        if not entry:
            return None
        if contains_common_secret(entry):
            return "Şifre, anahtar ya da gizli kod gibi bilgileri günlüğe yazmıyorum. Gizli kısmı çıkarıp tekrar söyleyebilirsin."
        if len(entry) > 1000:
            return "Günlük girdisi en fazla 1000 karakter olabilir; biraz kısaltır mısın?"
        await pool.execute("INSERT INTO owner_journal(user_id,entry,day) VALUES($1,$2,$3)", user_id, entry, today)
        n = await pool.fetchval("SELECT COUNT(*) FROM owner_journal WHERE user_id=$1 AND day=$2", user_id, today)
        return f"Günlüğe yazdım: “{entry[:120]}”. Bugün {n} girdin var."
    if _DELETE.match(f):
        row = await pool.fetchrow("DELETE FROM owner_journal WHERE id=(SELECT id FROM owner_journal WHERE user_id=$1 ORDER BY id DESC LIMIT 1) AND user_id=$1 RETURNING entry", user_id)
        return f"Son girdiyi sildim: “{str(row['entry'])[:80]}”." if row else "Silinecek günlük girdisi yok."
    m = _SEARCH.match(f)
    if m:
        needle = (m.group(1) or m.group(2)).strip()
        rows = [r for r in await pool.fetch("SELECT day,entry FROM owner_journal WHERE user_id=$1 ORDER BY id DESC LIMIT 300", user_id)
                if needle in fold_turkish(r["entry"])]
        if not rows:
            return f"Günlüğünde “{needle}” geçen bir girdi bulamadım."
        return f"Günlüğünde “{needle}” geçen {len(rows)} girdi:\n" + "\n".join(_fmt(r) for r in rows[:6])
    m = _READ.match(f)
    if m:
        word = m.group(1) or "son"
        lo, hi = {"bugunku": (today, today), "dunku": (today - timedelta(days=1),) * 2,
                  "bu haftaki": (today - timedelta(days=today.weekday()), today),
                  "gecen haftaki": (today - timedelta(days=today.weekday() + 7), today - timedelta(days=today.weekday() + 1)),
                  "son": (today - timedelta(days=30), today)}[word]
        rows = await pool.fetch("SELECT day,entry FROM owner_journal WHERE user_id=$1 AND day BETWEEN $2 AND $3 ORDER BY day DESC, id DESC LIMIT 8", user_id, lo, hi)
        if not rows:
            return "Bu aralıkta günlük girdin yok. “günlüğe yaz: …” ile ekleyebilirsin."
        return "Günlüğün:\n" + "\n".join(_fmt(r) for r in rows)
    return None
