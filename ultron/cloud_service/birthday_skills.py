"""Birthdays and anniversaries: "Ahmet'in doğum günü 3 Mart", "doğum günlerim", "doğum günüm 5 mayıs".

Stored as two yearly reminders (the day before at 19:00 and the day itself at 09:00) so the existing
delivery, push and re-scheduling machinery does the work.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

if __package__:
    from .text_normalization import fold_turkish
    from .reminders import fold_with_map, next_occurrence, HOME_TZ, _MONTHS_FOLDED, _MONTH_NAMES
else:
    from text_normalization import fold_turkish
    from reminders import fold_with_map, next_occurrence, HOME_TZ, _MONTHS_FOLDED, _MONTH_NAMES

MARK = "🎂"
_MON = "|".join(_MONTHS_FOLDED)
_NAME_A = re.compile(r"^\s*(?:lutfen\s+)?(.+?)'?(?:in|nin|un|nun)\s+dogum gunu(?:nu)?\s+(\d{1,2})\s+(" + _MON + r")(?:\s+\d{4})?\s*(?:ekle|kaydet|hatirla|unutma)?\s*$")
_NAME_N = re.compile(r"^\s*(?:lutfen\s+)?(.+?)'?(?:in|nin|un|nun)\s+dogum gunu(?:nu)?\s+(\d{1,2})[./](\d{1,2})(?:[./]\d{2,4})?\s*(?:ekle|kaydet|hatirla|unutma)?\s*$")
_ADD_B = re.compile(r"^\s*dogum gunu\s+(?:ekle|kaydet)\s*[:\-]?\s*(.+?)\s+(\d{1,2})\s+(" + _MON + r")\s*$")
_MINE = re.compile(r"^\s*dogum gunum\s+(\d{1,2})\s+(" + _MON + r")\s*(?:ekle|kaydet)?\s*$")
_LIST = re.compile(r"^\s*(?:yaklasan\s+)?dogum gunlerim(?:i)?(?:\s+(?:goster|listele|neler))?\s*\??\s*$|^\s*yaklasan dogum gunleri\s*\??\s*$|^\s*kimin dogum gunu yaklasiyor\s*\??\s*$")
_UNTIL = re.compile(r"^\s*(.+?)'?(?:in|nin|un|nun)\s+dogum gunune\s+kac gun\s+(?:var|kaldi)\s*\??\s*$|^\s*dogum gunume\s+kac gun\s+(?:var|kaldi)\s*\??\s*$")
_REMOVE = re.compile(r"^\s*(.+?)'?(?:in|nin|un|nun)\s+dogum gunu(?:nu)?\s+(?:sil|kaldir|iptal et)\s*$")


_MEMORY_PREFIX = re.compile(r"^\s*(?:lutfen\s+)?(?:hatirla|hafizana kaydet|hafizaya kaydet|unut|not al|aklinda tut|kaydet)\s*[:\-–,]")


def wants_birthdays(text: str) -> bool:
    f = fold_turkish(text)
    if _MEMORY_PREFIX.match(f):          # "hatırla: annemin doğum günü 3 mart" is an explicit memory command
        return False
    return len(f) <= 120 and any(p.match(f) for p in (_NAME_A, _NAME_N, _ADD_B, _MINE, _LIST, _REMOVE, _UNTIL))


def _display(original: str, idx: list[int], span: tuple[int, int]) -> str:
    return re.sub(r"\s+", " ", original[idx[span[0]]: idx[span[1] - 1] + 1]).strip(" '’")[:40]


def genitive(name: str) -> str:
    """Ahmet → Ahmet'in, Murat → Murat'ın, Ayşe → Ayşe'nin, Ömer → Ömer'in (vowel harmony)."""
    low = name.replace("I", "ı").replace("İ", "i").lower()
    vowels = [c for c in low if c in "aıoueiöü"]
    last = vowels[-1] if vowels else "e"
    base = {"a": "ı", "ı": "ı", "e": "i", "i": "i", "o": "u", "u": "u", "ö": "ü", "ü": "ü"}[last]
    ends_vowel = low[-1] in "aıoueiöü"
    return f"{name}'{'n' if ends_vowel else ''}{base}n"


def _valid(day: int, month: int) -> bool:
    return 1 <= month <= 12 and 1 <= day <= (29 if month == 2 else 30 if month in (4, 6, 9, 11) else 31)


async def _save(pool: Any, user_id: str, label: str, day: int, month: int, now: datetime) -> str:
    rule = f"yearly:{month:02d}-{day:02d}"
    local = now.astimezone(HOME_TZ)
    on_day = f"{MARK} {label} doğum günü bugün!"
    before = f"{MARK} Yarın {label} doğum günü."
    existing = await pool.fetchval("SELECT COUNT(*) FROM owner_reminders WHERE user_id=$1 AND status='pending' AND text=$2 AND repeat_rule=$3", user_id, on_day, rule)
    if int(existing or 0):
        return f"{label} doğum günü zaten kayıtlı ({day} {_MONTH_NAMES[month - 1]})."
    first = next_occurrence(rule, 9, 0, local)
    eve_rule = (datetime(2000, month, day) - timedelta(days=1))
    eve = f"yearly:{eve_rule.month:02d}-{eve_rule.day:02d}"
    for text, r, hour in ((on_day, rule, 9), (before, eve, 19)):
        due = next_occurrence(r, hour, 0, local)
        await pool.execute("INSERT INTO owner_reminders(user_id,text,due_at,repeat_rule) VALUES($1,$2,$3,$4)", user_id, text, due, r)
    return (f"Tamam, {label} doğum günü: {day} {_MONTH_NAMES[month - 1]}. Her yıl o sabah 09:00'da ve bir önceki akşam 19:00'da hatırlatacağım "
            f"(sıradaki: {first.day}.{first.month:02d}.{first.year}).")


async def handle(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    if pool is None or not wants_birthdays(text):
        return None
    now = now or datetime.now(timezone.utc)
    f, idx = fold_with_map(text)
    f = f.strip()
    for pattern, kind in ((_NAME_A, "text"), (_NAME_N, "num"), (_ADD_B, "text")):
        m = pattern.match(f)
        if m:
            if pattern is _ADD_B:
                label_span, d_g, mon_g = m.span(1), int(m.group(2)), m.group(3)
            else:
                label_span, d_g, mon_g = m.span(1), int(m.group(2)), m.group(3)
            month = _MONTHS_FOLDED.index(mon_g) + 1 if kind == "text" else int(mon_g)
            if not _valid(d_g, month):
                return "Bu tarih geçerli görünmüyor; örneğin “Ahmet'in doğum günü 3 Mart” yazabilirsin."
            label = _display(text, idx, label_span)
            if not label:
                return None
            label = label[:1].upper() + label[1:]
            return await _save(pool, user_id, genitive(label), d_g, month, now)
    m = _MINE.match(f)
    if m:
        day, month = int(m.group(1)), _MONTHS_FOLDED.index(m.group(2)) + 1
        if not _valid(day, month):
            return "Bu tarih geçerli görünmüyor."
        return await _save(pool, user_id, "Senin", day, month, now)
    m = _UNTIL.match(f)
    if m:
        who = _display(text, idx, m.span(1)) if m.group(1) else "Senin"
        rows = await pool.fetch("SELECT text,due_at FROM owner_reminders WHERE user_id=$1 AND status='pending' AND repeat_rule LIKE 'yearly:%' "
                                "AND text LIKE '%doğum günü bugün!' AND text LIKE $2 ORDER BY due_at LIMIT 1", user_id, f"{MARK}%{who[:1].upper() + who[1:]}%")
        if not rows:
            return f"{who} için kayıtlı bir doğum günü bulamadım."
        due = rows[0]["due_at"].astimezone(HOME_TZ)
        days = (due.date() - now.astimezone(HOME_TZ).date()).days
        return (f"{who} doğum günü bugün! 🎉" if days == 0 else f"{who} doğum gününe {days} gün var ({due.day} {_MONTH_NAMES[due.month - 1]}).")
    m = _REMOVE.match(f)
    if m:
        label = _display(text, idx, m.span(1))
        rows = await pool.fetch("SELECT id,text FROM owner_reminders WHERE user_id=$1 AND status='pending' AND text LIKE $2 AND repeat_rule LIKE 'yearly:%'",
                                user_id, f"{MARK}%{label[:1].upper() + label[1:]}%")
        if not rows:
            return f"{label} için kayıtlı doğum günü bulamadım."
        for r in rows:
            await pool.execute("UPDATE owner_reminders SET status='cancelled' WHERE id=$1 AND user_id=$2", r["id"], user_id)
        return f"{label} doğum günü hatırlatıcılarını sildim."
    # list
    rows = await pool.fetch("SELECT text,due_at,repeat_rule FROM owner_reminders WHERE user_id=$1 AND status='pending' AND repeat_rule LIKE 'yearly:%' "
                            "AND text LIKE $2 AND text LIKE '%doğum günü bugün!' ORDER BY due_at LIMIT 12", user_id, f"{MARK}%")
    if not rows:
        return "Kayıtlı doğum günü yok. Örn. “Ahmet'in doğum günü 3 Mart”."
    local = now.astimezone(HOME_TZ).date()
    lines = []
    for r in rows:
        due = r["due_at"].astimezone(HOME_TZ)
        name = r["text"][len(MARK):].strip().replace(" doğum günü bugün!", "")
        lines.append(f"• {due.day} {_MONTH_NAMES[due.month - 1]} — {name} ({(due.date() - local).days} gün sonra)")
    return "Yaklaşan doğum günleri:\n" + "\n".join(lines)
