"""Smart scheduling on top of the owner's plans and calendar.

"bugün şu işleri sığdır: rapor 2 saat, spor 1 saat, alışveriş 45 dk"  → proposes time blocks in the free windows;
"planı onayla" adds them to the plans, "planı vazgeç" drops the proposal.  Also: "toplantıya ne kadar kaldı",
"sıradaki planım", "diş randevusu planını yarına ertele".  Nothing is written without "planı onayla".
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

if __package__:
    from .text_normalization import fold_turkish
    from .reminders import fold_with_map, HOME_TZ
    from . import plan_skills
else:
    from text_normalization import fold_turkish
    from reminders import fold_with_map, HOME_TZ
    import plan_skills

DAY_START, DAY_END, BUFFER = 9 * 60, 21 * 60, 10
MAX_TASKS = 10
_FIT = re.compile(r"^(bugun|yarin)?\s*(?:su\s+)?islerimi?\s*(?:sigdir|planla|yerlestir)\s*[:\-]\s*(.+)$|^(bugun|yarin)\s+su\s+isleri\s+(?:sigdir|planla|yerlestir)\s*[:\-]\s*(.+)$|^su\s+isleri\s+(?:sigdir|planla|yerlestir)\s*[:\-]\s*(.+)$", re.S)
_CONFIRM = re.compile(r"^plan(?:i|imi)\s+onayla\s*$")
_CANCEL = re.compile(r"^plan(?:i|imi)\s+vazgec\s*$")
_LEFT = re.compile(r"^(.{2,40}?)'?(?:e|a|ye|ya|ne|na)\s+(?:ne\s+kadar|kac\s+(?:saat|gun|dakika))\s+kaldi\s*\??$")
_NEXT = re.compile(r"^(?:siradaki|sonraki|bir\s+sonraki)\s+planim\s*(?:ne)?\s*\??$|^siradaki\s+etkinligim\s*(?:ne)?\s*\??$")
_POSTPONE = re.compile(r"^(.{2,40}?)\s+plan(?:i|ini|imi)\s+(yarina|haftaya|(\d{1,2})\s*gun\s+sonraya)\s+ertele\s*$")
_DUR = re.compile(r"(\d+(?:[.,]\d+)?)\s*(saat|sa|dakika|dk)\b")


def wants_schedule(text: str) -> bool:
    f = fold_turkish(text)
    return len(f) <= 400 and bool(_FIT.match(f) or _CONFIRM.match(f) or _CANCEL.match(f) or _LEFT.match(f) or _NEXT.match(f) or _POSTPONE.match(f))


def parse_tasks(raw: str) -> list[tuple[str, int]]:
    """"rapor 2 saat, spor 1 saat" → [("rapor", 120), ("spor", 60)]; tasks without a duration get 60 minutes."""
    out = []
    for part in re.split(r"(?<!\d),(?!\d)|[;\n]", raw):
        part = " ".join(part.split())
        if not part:
            continue
        m = _DUR.search(fold_turkish(part))
        minutes = 60
        title = part
        if m:
            value = float(m.group(1).replace(",", "."))
            minutes = int(round(value * (60 if m.group(2) in ("saat", "sa") else 1)))
            title = " ".join((part[: m.start()] + " " + part[m.end():]).split()) if len(part) == len(fold_turkish(part)) else part
        minutes = max(10, min(minutes, 480))
        out.append((title.strip(" -:")[:60] or "iş", minutes))
    return out


def allocate(tasks: list[tuple[str, int]], busy: list[tuple[int, int]], start_at: int) -> tuple[list[tuple[str, int, int]], list[str]]:
    """First-fit placement of whole tasks into the free windows; returns (blocks, tasks that did not fit)."""
    slots = plan_skills.free_slots(busy, max(DAY_START, start_at), DAY_END, 10)
    blocks, left_out = [], []
    for title, minutes in tasks:
        placed = False
        for i, (a, b) in enumerate(slots):
            if b - a >= minutes:
                blocks.append((title, a, a + minutes))
                slots[i] = (a + minutes + BUFFER, b)
                placed = True
                break
        if not placed:
            left_out.append(title)
    return sorted(blocks, key=lambda x: x[1]), left_out


async def _get_proposal(pool, user_id):
    raw = await pool.fetchval("SELECT prefs->>'schedule_proposal' FROM owner_prefs WHERE user_id=$1", user_id)
    try:
        return json.loads(raw) if raw else None
    except ValueError:
        return None


async def _set_proposal(pool, user_id, value) -> None:
    payload = json.dumps(value) if value else "null"
    await pool.execute(
        "INSERT INTO owner_prefs(user_id,prefs) VALUES($1,jsonb_build_object('schedule_proposal',$2::jsonb)) "
        "ON CONFLICT(user_id) DO UPDATE SET prefs=COALESCE(owner_prefs.prefs,'{}'::jsonb)||jsonb_build_object('schedule_proposal',$2::jsonb),updated_at=NOW()",
        user_id, payload)


def _hm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


async def handle(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    if pool is None or not wants_schedule(text):
        return None
    f, idx = fold_with_map(text)
    f = f.strip()
    local = (now or datetime.now(timezone.utc)).astimezone(HOME_TZ)
    today = local.date()
    m = _FIT.match(f)
    if m:
        word = m.group(1) or m.group(3)
        tail_group = 2 if m.group(2) else 4 if m.group(4) else 5
        original = text[idx[m.start(tail_group)]:]
        tasks = parse_tasks(original)
        if not 1 <= len(tasks) <= MAX_TASKS:
            return f"1–{MAX_TASKS} iş yaz, virgülle ayır. Örn. “bugün şu işleri sığdır: rapor 2 saat, spor 1 saat”."
        day = today + timedelta(days=1) if word == "yarin" else today
        busy, notes = await plan_skills.busy_intervals(pool, user_id, day)
        start_at = ((local.hour * 60 + local.minute + 14) // 15) * 15 if day == today else DAY_START
        blocks, left_out = allocate(tasks, busy, start_at)
        if not blocks:
            return "Bu gün için uygun boş zaman bulamadım; yarın için deneyebilirsin."
        await _set_proposal(pool, user_id, {"day": day.isoformat(), "blocks": [{"title": t, "start": a, "end": b} for t, a, b in blocks]})
        lines = [f"• {_hm(a)}–{_hm(b)}  {t}" for t, a, b in blocks]
        extra = (f"\nSığmayanlar: {', '.join(left_out)}." if left_out else "") + ("".join("\n" + n for n in notes))
        return (f"📋 {day:%d.%m} için önerim (mevcut plan ve etkinliklerin çıkarıldı):\n" + "\n".join(lines) + extra +
                "\nPlanlarına eklemek için “planı onayla”, vazgeçmek için “planı vazgeç” de.")
    if _CONFIRM.match(f):
        proposal = await _get_proposal(pool, user_id)
        if not proposal or not proposal.get("blocks"):
            return "Onaylanacak bir öneri yok. Önce “bugün şu işleri sığdır: …” de."
        day = date.fromisoformat(proposal["day"])
        for b in proposal["blocks"]:
            await pool.execute("INSERT INTO owner_plans(user_id,title,scheduled_date,scheduled_time,note) VALUES($1,$2,$3,$4,$5)",
                               user_id, b["title"][:140], day, time(b["start"] // 60, b["start"] % 60), f"{_hm(b['start'])}–{_hm(b['end'])} (GÖLGE önerisi)")
        await _set_proposal(pool, user_id, None)
        return f"{len(proposal['blocks'])} bloğu {day:%d.%m} planlarına ekledim. “planlarım” ile görebilirsin."
    if _CANCEL.match(f):
        await _set_proposal(pool, user_id, None)
        return "Öneriyi bıraktım; hiçbir plan eklenmedi."
    if _NEXT.match(f):
        row = await pool.fetchrow(
            "SELECT title,scheduled_date,scheduled_time FROM owner_plans WHERE user_id=$1 AND is_done=FALSE AND scheduled_time IS NOT NULL "
            "AND (scheduled_date > $2 OR (scheduled_date=$2 AND scheduled_time >= $3)) ORDER BY scheduled_date,scheduled_time LIMIT 1",
            user_id, today, local.time().replace(second=0, microsecond=0))
        if not row:
            return "Saatli, yaklaşan bir planın görünmüyor."
        when = datetime.combine(row["scheduled_date"], row["scheduled_time"], tzinfo=HOME_TZ)
        mins = int((when - local).total_seconds() // 60)
        left = f"{mins // 60} sa {mins % 60} dk" if mins >= 60 else f"{mins} dk"
        return f"Sıradaki: {row['title']} — {when:%d.%m %H:%M} ({left} sonra)."
    m = _LEFT.match(f)
    if m:
        needle = fold_turkish(text[idx[m.start(1)]: idx[m.end(1) - 1] + 1]).strip(" '")
        rows = await pool.fetch(
            "SELECT title,scheduled_date,scheduled_time FROM owner_plans WHERE user_id=$1 AND is_done=FALSE AND scheduled_date >= $2 ORDER BY scheduled_date,scheduled_time NULLS LAST LIMIT 100",
            user_id, today)
        hit = next((r for r in rows if needle and needle in fold_turkish(r["title"])), None)
        if not hit:
            return None
        clock = hit["scheduled_time"] or time(0, 0)
        when = datetime.combine(hit["scheduled_date"], clock, tzinfo=HOME_TZ)
        delta = when - local
        if delta.total_seconds() < 0:
            return f"{hit['title']} zamanı geldi ya da geçti."
        days, rem = delta.days, delta.seconds
        parts = ([f"{days} gün"] if days else []) + ([f"{rem // 3600} saat"] if rem >= 3600 else []) + ([f"{rem % 3600 // 60} dakika"] if rem % 3600 >= 60 and not days else [])
        return f"{hit['title']} ({when:%d.%m}{' ' + clock.strftime('%H:%M') if hit['scheduled_time'] else ''}) için {' '.join(parts) or 'çok az'} kaldı."
    m = _POSTPONE.match(f)
    if m:
        needle = fold_turkish(text[idx[m.start(1)]: idx[m.end(1) - 1] + 1]).strip()
        shift = 1 if m.group(2) == "yarina" else 7 if m.group(2) == "haftaya" else int(m.group(3))
        rows = await pool.fetch("SELECT id,title,scheduled_date FROM owner_plans WHERE user_id=$1 AND is_done=FALSE ORDER BY scheduled_date LIMIT 200", user_id)
        hits = [r for r in rows if needle in fold_turkish(r["title"])]
        if not hits:
            return f"“{needle}” içeren bir planın yok."
        if len(hits) > 1:
            return f"“{needle}” ile {len(hits)} plan eşleşiyor, hiçbirini ertelemedim. Daha belirgin yazar mısın?\n" + "\n".join(f"• {r['title']}" for r in hits[:5])
        new_day = hits[0]["scheduled_date"] + timedelta(days=shift)
        await pool.execute("UPDATE owner_plans SET scheduled_date=$3,updated_at=NOW() WHERE id=$1 AND user_id=$2", hits[0]["id"], user_id, new_day)
        return f"“{hits[0]['title']}” planını {new_day:%d.%m.%Y} tarihine erteledim."
    return None
