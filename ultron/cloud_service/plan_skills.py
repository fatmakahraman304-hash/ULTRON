"""Plans from chat: "yarın 15:00 toplantı ekle", "planlarım", "diş randevusu planını tamamla/sil"."""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

if __package__:
    from .text_normalization import fold_turkish
    from .reminders import parse_reminder, HOME_TZ, _DOW_NAMES, _WEEKDAYS
    from . import calendar_feed
else:
    from text_normalization import fold_turkish
    from reminders import parse_reminder, HOME_TZ, _DOW_NAMES, _WEEKDAYS
    import calendar_feed

_ADD = re.compile(r"\b(?:plan\w*|takvim\w*|ajanda\w*|program\w*)\b.*\b(?:ekle|olustur|yaz|kaydet|koy|ayarla)\b"
                  r"|\b(?:ekle|olustur|yaz|kaydet|koy)\b.*\b(?:plan\w*|takvim\w*|ajanda\w*)\b")
_LIST = re.compile(r"\bplanlarim(?:i)?(?: neler| ne| goster| listele| var)?\b|\byaklasan planlar\w*\b|\bplanlarimi (?:goster|listele)\b")
_DONE = re.compile(r"\bplan\w*\b.*\b(?:tamamla\w*|bitir\w*|bitti|yaptim)\b|\b(?:tamamla\w*|bitir\w*)\b.*\bplan\w*\b")
_DEL = re.compile(r"\bplan\w*\b.*\b(?:sil|silelim|kaldir|iptal et)\b|\b(?:sil|kaldir)\b.*\bplan\w*\b")
_NOT_A_PLAN = re.compile(r"\b(?:uygulama\w*|kod\w*|script\w*|yazilim\w*|site\w*|makale\w*|rapor\w*|odev\w*|program yaz\w*|ders plani|plan yap\w*)\b")
_NOISE = re.compile(r"\b(?:plan\w*|takvim\w*|ajanda\w*|program\w*|ekle|olustur|yaz|kaydet|koy|ayarla|tamamla\w*|bitir\w*|bitti|yaptim|"
                    r"sil\w*|kaldir\w*|iptal|et|lutfen|bana|benim|bir|icin|su|sunu|bunu)\b")


_FREE_Q = re.compile(r"\b(?:bugun|yarin|obur gun|pazartesi|sali|carsamba|persembe|cuma|cumartesi|pazar|bu hafta)\b.*\b(?:bos|musait)(?:um|im|sin)?\b"
                    r"|\bne zaman (?:bos|musait)(?:um|im)\b|\b(?:bos|musait) (?:zaman|saat)\w*\b")
_FREE_SKIP = re.compile(r"\b(?:ne yapabilirim|ne yapsam|olursa|olunca|gidelim|yapalim|istiyorum|kalmak|olmak|degerlendir\w*|oner\w*|nasil|neden)\b")
WORK_START, WORK_END, PLAN_MINUTES, MIN_SLOT = 9 * 60, 18 * 60, 60, 30


def _day_for(folded: str, today: date) -> tuple[date, str]:
    if "yarin" in folded:
        return today + timedelta(days=1), "Yarın"
    if "obur gun" in folded:
        return today + timedelta(days=2), "Öbür gün"
    for name, wd in _WEEKDAYS.items():
        if re.search(r"\b" + name + r"\b", folded):
            ahead = (wd - today.weekday()) % 7 or 7
            d = today + timedelta(days=ahead)
            return d, _DOW_NAMES[wd]
    return today, "Bugün"


def free_slots(busy: list[tuple[int, int]], start: int = WORK_START, end: int = WORK_END, minimum: int = MIN_SLOT) -> list[tuple[int, int]]:
    """Free (start, end) minute blocks inside [start, end] after removing busy intervals."""
    slots, cursor = [], start
    for b_start, b_end in sorted(busy):
        if b_start > cursor and b_start - cursor >= minimum:
            slots.append((cursor, min(b_start, end)))
        cursor = max(cursor, b_end)
        if cursor >= end:
            break
    if end - cursor >= minimum and cursor < end:
        slots.append((cursor, end))
    return [(a, b) for a, b in slots if b - a >= minimum]


def _hm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


async def busy_intervals(pool: Any, user_id: str, day: date) -> tuple[list[tuple[int, int]], list[str]]:
    """Timed plans (1 h assumed) and timed calendar events on `day`, as minute intervals."""
    busy, notes = [], []
    rows = await pool.fetch("SELECT title,scheduled_time FROM owner_plans WHERE user_id=$1 AND is_done=FALSE AND scheduled_date=$2 AND scheduled_time IS NOT NULL", user_id, day)
    for r in rows:
        s = r["scheduled_time"].hour * 60 + r["scheduled_time"].minute
        busy.append((s, s + PLAN_MINUTES))
    try:
        events = await calendar_feed.events_between(pool, user_id, day, day)
        for e in events or []:
            if e["all_day"]:
                continue
            s = datetime.fromisoformat(e["start"])
            en = datetime.fromisoformat(e["end"]) if e.get("end") else s + timedelta(minutes=PLAN_MINUTES)
            busy.append((s.hour * 60 + s.minute, max(s.hour * 60 + s.minute + 15, en.hour * 60 + en.minute if en.date() == s.date() else 24 * 60)))
    except Exception:
        notes.append("Takvim okunamadığı için yalnızca GÖLGE planlarına baktım.")
    return busy, notes


async def conflicts_for(pool: Any, user_id: str, day: date, clock: time) -> list[str]:
    """Timed plans/events within an hour of `clock` on `day`."""
    start = clock.hour * 60 + clock.minute
    found = []
    rows = await pool.fetch("SELECT title,scheduled_time FROM owner_plans WHERE user_id=$1 AND is_done=FALSE AND scheduled_date=$2 AND scheduled_time IS NOT NULL", user_id, day)
    for r in rows:
        s = r["scheduled_time"].hour * 60 + r["scheduled_time"].minute
        if abs(s - start) < PLAN_MINUTES:
            found.append(f"{_hm(s)} — {str(r['title'])[:60]}")
    try:
        for e in await calendar_feed.events_between(pool, user_id, day, day) or []:
            if not e["all_day"]:
                s = datetime.fromisoformat(e["start"])
                m = s.hour * 60 + s.minute
                if abs(m - start) < PLAN_MINUTES:
                    found.append(f"{_hm(m)} — {e['title'][:60]} (takvim)")
    except Exception:
        pass
    return found


def _title(text: str, consumed: str) -> str:
    return re.sub(r"\s+", " ", consumed).strip(" .:-'’,")


def _needle(text: str) -> str:
    return re.sub(r"\s+", " ", _NOISE.sub(" ", fold_turkish(text))).strip(" .:-'’,")


def _fmt(day, clock) -> str:
    base = f"{day.day}.{day.month:02d}.{day.year} {_DOW_NAMES[day.weekday()]}"
    return base + (f" {clock:%H:%M}" if clock else "")


def _strip_plan_words(message: str) -> str:
    out = []
    for word in message.split():
        if _NOISE.fullmatch(fold_turkish(word).strip(".,:;!?'’")):
            continue
        out.append(word)
    return _title(message, " ".join(out))


async def handle(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    if pool is None or len(text) > 400:
        return None
    folded = fold_turkish(text)
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(HOME_TZ).date()

    if _LIST.search(folded) and not _ADD.search(folded) and not re.search(r"\b(?:bugun|yarin|hafta)\b", folded):
        rows = await pool.fetch(
            "SELECT title,scheduled_date,scheduled_time FROM owner_plans WHERE user_id=$1 AND is_done=FALSE "
            "AND scheduled_date>=$2 ORDER BY scheduled_date, scheduled_time NULLS LAST LIMIT 15", user_id, today)
        if not rows:
            return "Önümüzdeki günler için açık planın yok. “yarın 15:00 toplantı ekle” gibi yazarak ekleyebilirsin."
        return "Yaklaşan planların:\n" + "\n".join(f"• {_fmt(r['scheduled_date'], r['scheduled_time'])} — {str(r['title'])[:80]}" for r in rows)

    if _FREE_Q.search(folded) and not _FREE_SKIP.search(folded) and not _ADD.search(folded) and len(folded) <= 60:
        day, label = _day_for(folded, today)
        busy, notes = await busy_intervals(pool, user_id, day)
        slots = free_slots(busy)
        head = f"{label} ({day.day}.{day.month:02d}.{day.year} {_DOW_NAMES[day.weekday()]}) 09:00–18:00 arasında"
        if not slots:
            body = f"{head} boş bir zamanın görünmüyor."
        elif not busy:
            body = f"{head} kayıtlı bir şey yok; bütün gün müsaitsin."
        else:
            body = f"{head} boş zamanların:\n" + "\n".join(f"• {_hm(a)}–{_hm(b)} ({(b - a) // 60} sa {(b - a) % 60} dk)" for a, b in slots)
        return body + "\n(Saatli planlar 1 saat sürer diye sayıldı." + (" " + " ".join(notes) if notes else "") + ")"

    if _DEL.search(folded) or _DONE.search(folded):
        deleting = bool(_DEL.search(folded)) and not _DONE.search(folded)
        needle = _needle(text)
        if len(needle) < 2:
            return "Hangi planı kastettiğini anlayamadım; planın adını da yazar mısın?"
        rows = await pool.fetch(
            "SELECT id,title,scheduled_date,scheduled_time FROM owner_plans WHERE user_id=$1 AND is_done=FALSE "
            "ORDER BY scheduled_date, scheduled_time NULLS LAST LIMIT 100", user_id)
        hits = [r for r in rows if needle in fold_turkish(r["title"])]
        if not hits:
            return f"“{needle[:60]}” ile eşleşen açık bir plan bulamadım."
        if len(hits) > 1:
            return (f"“{needle[:50]}” ile {len(hits)} plan eşleşiyor, hiçbirine dokunmadım. Daha belirgin yazar mısın?\n"
                    + "\n".join(f"• {_fmt(r['scheduled_date'], r['scheduled_time'])} — {str(r['title'])[:70]}" for r in hits[:5]))
        hit = hits[0]
        if deleting:
            await pool.execute("DELETE FROM owner_plans WHERE id=$1 AND user_id=$2", hit["id"], user_id)
            return f"Planı sildim: {str(hit['title'])[:80]}"
        await pool.execute("UPDATE owner_plans SET is_done=TRUE,updated_at=NOW() WHERE id=$1 AND user_id=$2", hit["id"], user_id)
        return f"Planı tamamlandı olarak işaretledim: {str(hit['title'])[:80]} ✓"

    if _ADD.search(folded) and not _NOT_A_PLAN.search(folded):
        parsed = parse_reminder(text, now, require_intent=False)
        if parsed is None or parsed.get("error") == "no_time":
            return "Planı hangi gün ve saate ekleyeyim? Örneğin “yarın 15:00 diş randevusu planına ekle”."
        if parsed.get("error") == "past":
            return "Bu tarih geçmişte kaldı; gelecekte bir gün söyler misin?"
        if "error" in parsed:
            return "Bir yıldan uzak plan ekleyemiyorum."
        title = _strip_plan_words(parsed["text"] if parsed["text"] != "Hatırlatıcı" else "")
        if not title:
            return "Planın adı ne olsun? Örneğin “yarın 15:00 diş randevusu planına ekle”."
        day, clock = parsed["due"].date(), (parsed["due"].timetz().replace(tzinfo=None) if parsed["has_clock"] else None)
        clock = clock.replace(second=0, microsecond=0) if clock else None
        dup = await pool.fetchval(
            "SELECT id FROM owner_plans WHERE user_id=$1 AND title=$2 AND scheduled_date=$3 "
            "AND scheduled_time IS NOT DISTINCT FROM $4 AND is_done=FALSE", user_id, title[:140], day, clock)
        if dup:
            return f"Bu plan zaten ekli: {_fmt(day, clock)} — {title[:80]}"
        clashes = await conflicts_for(pool, user_id, day, clock) if clock else []
        await pool.fetchval(
            "INSERT INTO owner_plans(user_id,title,scheduled_date,scheduled_time,note) VALUES($1,$2,$3,$4,'') RETURNING id",
            user_id, title[:140], day, clock)
        warn = ("\n⚠ Dikkat, bu saate yakın başka kayıt var: " + "; ".join(clashes)) if clashes else ""
        return (f"Planına ekledim: {_fmt(day, clock)} — {title[:80]}{warn}\n"
                "İstersen “10 dakika önce hatırlat” diyerek ayrıca hatırlatıcı da kurabilirim; "
                "yaklaşan planlar için zaten önceden bildirim gönderiyorum.")
    return None
