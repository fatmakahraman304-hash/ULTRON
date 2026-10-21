"""Expense log from chat (TRY): "150 lira market harcaması ekle", "bugün kahveye 80 tl harcadım",
"bu ay ne kadar harcadım", "harcamalarım", "son harcamayı sil"."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

if __package__:
    from .text_normalization import fold_turkish
    from .reminders import fold_with_map
else:
    from text_normalization import fold_turkish
    from reminders import fold_with_map

HOME_TZ = ZoneInfo("Europe/Istanbul")
_AMOUNT = re.compile(r"(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)\s*(?:tl|lira\w*|₺|try)\b")
_BARE = re.compile(r"\bharcama\w*\s+(?:ekle|kaydet|gir|yaz)\s+(\d+(?:[.,]\d{1,2})?)\b")
_ADD = re.compile(r"\bharcama\w*\s+(?:ekle|kaydet|gir|yaz)\b|\bharcadim\b|\bharcadik\b|\bode(?:dim|di)\b.*\b(?:tl|lira)\b|\bverdim\b")
_SUMMARY = re.compile(r"\b(?:bu ay|bugun|bu hafta|gecen ay|dun)\b.*\b(?:ne kadar|kac)\b.*\b(?:harcadim|harcadik|harcama\w*)\b|\bharcama\w*\s*(?:ozeti|raporu|listesi)?\b.*\b(?:bu ay|bugun|bu hafta|gecen ay)\b"
                      r"|\b(?:bu ay|bugun|bu hafta|gecen ay|dun)\b\s+harcama\w*\s*(?:ozeti|raporu|listesi)?\s*\??\s*$|^\s*harcamalarim\s*\??\s*$|\bne kadar harcadim\b|\btoplam harcama\w*\b")
_UNDO = re.compile(r"\bson harcama\w*\s*(?:yi|i)?\s*(?:sil|geri al|iptal)\b|\bharcamayi geri al\b")
_STOP = {"icin", "bugun", "dun", "ekle", "kaydet", "gir", "yaz", "harcama", "harcamasi", "harcamasini", "harcadim", "harcadik", "verdim", "odedim",
         "ode", "lira", "tl", "bir", "su", "sunu", "bana", "benim", "toplam", "da", "de", "ta", "te", "icin", "ile", "ve", "bu", "ay", "hafta"}


def _num(raw: str) -> float | None:
    raw = raw.strip()
    try:
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?", raw):
            return float(raw.replace(".", "").replace(",", "."))
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def _money(value: float) -> str:
    return f"{value:,.2f}".rstrip("0").rstrip(".").replace(",", "X").replace(".", ",").replace("X", ".") + " ₺"


def _stem(word: str) -> str:
    w = word.replace("I", "ı").replace("İ", "i").lower()
    if len(w) >= 5 and w.endswith(("ye", "ya")):
        w = w[:-2]
    elif len(w) >= 7 and w.endswith(("te", "ta", "de", "da")):
        w = w[:-2]
    return w[:40] or "diğer"


def wants_expenses(text: str) -> bool:
    f = fold_turkish(text)
    return len(f) <= 120 and bool(_UNDO.search(f) or _SUMMARY.search(f) or (_ADD.search(f) and (_AMOUNT.search(f) or _BARE.search(f))))


def _period(f: str, today: date) -> tuple[date, date, str]:
    if "gecen ay" in f:
        first = today.replace(day=1)
        end = first - timedelta(days=1)
        return end.replace(day=1), end, "Geçen ay"
    if "bu hafta" in f:
        return today - timedelta(days=today.weekday()), today, "Bu hafta"
    if re.search(r"\bdun\b", f):
        return today - timedelta(days=1), today - timedelta(days=1), "Dün"
    if "bugun" in f:
        return today, today, "Bugün"
    return today.replace(day=1), today, "Bu ay"


async def handle(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    if pool is None or not wants_expenses(text):
        return None
    f, idx = fold_with_map(text)
    today = (now or datetime.now(timezone.utc)).astimezone(HOME_TZ).date()
    if _UNDO.search(f):
        row = await pool.fetchrow("DELETE FROM owner_expenses WHERE id=(SELECT id FROM owner_expenses WHERE user_id=$1 ORDER BY id DESC LIMIT 1) AND user_id=$1 "
                                  "RETURNING amount,category", user_id)
        return f"Son harcamayı sildim: {_money(float(row['amount']))} ({row['category']})" if row else "Silinecek bir harcama kaydı yok."
    m = _AMOUNT.search(f) or _BARE.search(f)
    if _ADD.search(f) and m and not _SUMMARY.search(f):
        amount = _num(m.group(1))
        if amount is None or not 0 < amount < 100_000_000:
            return "Tutarı anlayamadım; örneğin “150 lira market harcaması ekle” yazabilirsin."
        span = (idx[m.start()], idx[m.end() - 1] + 1)
        orig_words = [w.group(0) for w in re.finditer(r"[^\W\d_]+", text)
                      if not (span[0] <= w.start() < span[1]) and fold_turkish(w.group(0)) not in _STOP]
        category = _stem(orig_words[0]) if orig_words else "diğer"
        note = " ".join(orig_words[1:4])[:120]
        spent = today - timedelta(days=1) if re.search(r"\bdun\b", f) else today
        await pool.execute("INSERT INTO owner_expenses(user_id,amount,category,note,spent_on) VALUES($1,$2,$3,$4,$5)", user_id, round(amount, 2), category, note, spent)
        return f"Kaydettim: {_money(amount)} — {category}" + (f" ({note})" if note else "") + f" · {'dün' if spent != today else 'bugün'}"
    start, end, label = _period(f, today)
    rows = await pool.fetch("SELECT category, SUM(amount) AS total, COUNT(*) AS n FROM owner_expenses WHERE user_id=$1 AND spent_on BETWEEN $2 AND $3 "
                            "GROUP BY category ORDER BY total DESC LIMIT 8", user_id, start, end)
    if not rows:
        return f"{label} için kayıtlı harcama yok. “150 lira market harcaması ekle” diyerek ekleyebilirsin."
    total = sum(float(r["total"]) for r in rows)
    lines = [f"• {r['category']}: {_money(float(r['total']))} ({int(r['n'])} kayıt)" for r in rows]
    return f"{label} toplam harcama: {_money(total)}\n" + "\n".join(lines)
