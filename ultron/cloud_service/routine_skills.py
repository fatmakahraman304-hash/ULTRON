"""Routines: ordered checklists with a name.

"akşam rutini: ilaç iç, su iç, yarını planla" saves, "akşam rutinini başlat" shows the steps and (when asked with
"hatırlatıcılarla") schedules one reminder per step, "rutinlerim" lists, "akşam rutinini sil" removes.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

if __package__:
    from .text_normalization import fold_turkish
else:
    from text_normalization import fold_turkish

MAX_ROUTINES, MAX_STEPS, MAX_STEP_LEN = 10, 12, 60
_SAVE = re.compile(r"^\s*(?:rutin\s+(?:kaydet|olustur|ekle)\s+)?([^\W\d_][\w ]{1,28}?)\s+rutin(?:i|im)?\s*[:\-]\s*(.+)$|^\s*rutin\s+(?:kaydet|olustur|ekle)\s+([^\W\d_][\w ]{1,28}?)\s*[:\-]\s*(.+)$", re.S)
_START = re.compile(r"^\s*([^\W\d_][\w ]{1,28}?)\s+rutin(?:ini|im|i)?\s+(?:(hatirlaticilarla)\s+)?(?:baslat|goster|oku|ac)\s*$|^\s*rutin\s+(?:baslat|goster)\s*:?\s*([^\W\d_][\w ]{1,28}?)(?:\s+(hatirlaticilarla))?\s*$")
_LIST = re.compile(r"^\s*rutinlerim(?:i)?(?:\s+(?:goster|listele))?\s*\??\s*$|^\s*hangi\s+rutinlerim\s+var\s*\??\s*$")
_DELETE = re.compile(r"^\s*([^\W\d_][\w ]{1,28}?)\s+rutin(?:ini|im|i)?\s+(?:sil|kaldir|iptal et)\s*$")


def wants_routines(text: str) -> bool:
    f = fold_turkish(text)
    return len(f) <= 400 and bool(_SAVE.match(f) or _START.match(f) or _LIST.match(f) or _DELETE.match(f))


def _split_steps(raw: str) -> list[str]:
    parts = [" ".join(p.split()) for p in re.split(r"[,;\n]|\s+sonra\s+|\s+ardindan\s+", raw) if p.strip()]
    return [p[:MAX_STEP_LEN] for p in parts]


def _name(group: str) -> str:
    return " ".join(group.split()).strip().replace("I", "ı").replace("İ", "i").lower()[:30]


def _orig(text: str, folded: str, m: re.Match, *groups: int) -> str:
    """The owner's own spelling of a matched name (fold_turkish keeps one character per character)."""
    g = next(i for i in groups if m.group(i) is not None)
    return _name(text[m.start(g):m.end(g)] if len(folded) == len(text) else m.group(g))


async def _find(pool, user_id: str, name: str):
    rows = await pool.fetch("SELECT name,steps FROM owner_routines WHERE user_id=$1", user_id)
    return next((r for r in rows if fold_turkish(r["name"]) == fold_turkish(name)), None), rows


async def handle(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    if pool is None or not wants_routines(text):
        return None
    f = fold_turkish(text)
    m = _SAVE.match(f)
    if m:
        name = _orig(text, f, m, 1, 3)
        # keep the owner's own characters for the steps (folded text has the same length for Turkish input)
        tail = m.group(2) if m.group(2) is not None else m.group(4)
        start = m.start(2) if m.group(2) is not None else m.start(4)
        original = text[start:start + len(tail)] if len(f) == len(text) else tail
        steps = _split_steps(original)
        if not 1 <= len(steps) <= MAX_STEPS:
            return f"Bir rutinde 1–{MAX_STEPS} adım olabilir; adımları virgülle ayır. Örn. “akşam rutini: ilaç iç, su iç, yarını planla”."
        existing, rows = await _find(pool, user_id, name)
        if existing is None and len(rows) >= MAX_ROUTINES:
            return f"En fazla {MAX_ROUTINES} rutin tutabilirim; birini silip tekrar dene."
        if existing is not None:
            name = existing["name"]
        await pool.execute(
            "INSERT INTO owner_routines(user_id,name,steps) VALUES($1,$2,$3) "
            "ON CONFLICT(user_id,name) DO UPDATE SET steps=EXCLUDED.steps,updated_at=NOW()", user_id, name, steps)
        return f"“{name}” rutinini kaydettim ({len(steps)} adım). Başlatmak için “{name} rutinini başlat”."
    if _LIST.match(f):
        rows = await pool.fetch("SELECT name,steps FROM owner_routines WHERE user_id=$1 ORDER BY name", user_id)
        if not rows:
            return "Kayıtlı rutinin yok. Örn. “sabah rutini: su iç, ilaç al, planına bak”."
        return "Rutinlerin:\n" + "\n".join(f"• {r['name']}: {len(r['steps'])} adım" for r in rows)
    m = _DELETE.match(f)
    if m:
        name = _orig(text, f, m, 1)
        found, _ = await _find(pool, user_id, name)
        if not found:
            return f"“{name}” adında bir rutin bulamadım."
        await pool.execute("DELETE FROM owner_routines WHERE user_id=$1 AND name=$2", user_id, found["name"])
        return f"“{found['name']}” rutinini sildim."
    m = _START.match(f)
    name = _orig(text, f, m, 1, 3)
    with_reminders = bool(m.group(2) or m.group(4))
    row, _ = await _find(pool, user_id, name)
    if not row:
        return f"“{name}” adında bir rutin bulamadım. “rutinlerim” ile kayıtlı olanları görebilirsin."
    name = row["name"]
    steps = list(row["steps"])
    body = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    if not with_reminders:
        return f"▶ {name} rutini:\n{body}\nHer adım için hatırlatıcı istersen “{name} rutinini hatırlatıcılarla başlat” de."
    start = (now or datetime.now(timezone.utc)) + timedelta(minutes=1)
    for i, s in enumerate(steps):
        await pool.execute("INSERT INTO owner_reminders(user_id,text,due_at) VALUES($1,$2,$3)", user_id, f"▶ {name} {i + 1}/{len(steps)}: {s}", start + timedelta(minutes=10 * i))
    return f"▶ {name} rutini başladı; her adım için 10 dakika arayla hatırlatıcı kurdum:\n{body}"
