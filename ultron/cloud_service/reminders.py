"""Owner reminders: natural Turkish parsing, storage and in-app delivery.

Reminders fire while a GÖLGE page/app is open (it polls /api/reminders/due);
there is no server-side OS push, and the chat reply says so honestly.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from aiohttp import web

if __package__:
    from .text_normalization import fold_turkish
else:
    from text_normalization import fold_turkish

HOME_TZ = ZoneInfo("Europe/Istanbul")
MAX_PENDING = 50
MAX_AHEAD = timedelta(days=366)
_WORD_NUM = {"bir": 1, "iki": 2, "uc": 3, "dort": 4, "bes": 5, "alti": 6, "yedi": 7, "sekiz": 8,
             "dokuz": 9, "on": 10, "onbes": 15, "yirmi": 20, "otuz": 30, "kirk": 40, "elli": 50}
_WEEKDAYS = {"pazartesi": 0, "sali": 1, "carsamba": 2, "persembe": 3, "cuma": 4, "cumartesi": 5, "pazar": 6}
_PART_DEFAULT = {"sabah": 8, "ogle": 12, "ogleden sonra": 15, "aksam": 19, "gece": 22}
_UNIT_SECONDS = {"saniye": 1, "sn": 1, "dakika": 60, "dk": 60, "saat": 3600, "sa": 3600,
                 "gun": 86400, "hafta": 604800}


def fold_with_map(text: str) -> tuple[str, list[int]]:
    """Fold char-by-char, remembering each folded char's original index."""
    out, index = [], []
    for i, ch in enumerate(str(text)):
        piece = fold_turkish(ch)
        out.append(piece)
        index.extend([i] * len(piece))
    return "".join(out), index


def _num(token: str) -> int | None:
    token = token.strip()
    return int(token) if token.isdigit() else _WORD_NUM.get(token)


_REL = re.compile(r"\b(\d{1,4}|yarim|" + "|".join(sorted(_WORD_NUM, key=len, reverse=True)) +
                  r")(?: buçuk| bucuk)? ?(saniye|sn|dakika|dk|saat|sa|gun|hafta) (sonra|icinde)\b")
_CLOCK_COLON = re.compile(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b")
_CLOCK_SAAT = re.compile(r"\bsaat ([01]?\d|2[0-3])(?:[:.]([0-5]\d))?(?:'?(?:da|de|ta|te|dan|den))?\b(?! ?(?:dakika|dk|saat|sn))")
_CLOCK_SUFFIX = re.compile(r"\b([01]?\d|2[0-3])'?(?:da|de|ta|te)\b")
_DAY_WORDS = re.compile(r"\b(bugun|yarin|obur gun|ertesi gun|" + "|".join(_WEEKDAYS) + r")(?:'?(?:da|de|ta|te|ye|ya))?\b")
_PART = re.compile(r"\b(ogleden sonra|sabah|ogle|aksam|gece)\b")
_ASK = re.compile(r"\bhatirla(?:t|tir|r misin|yin|ma)\w*|\bhatirlatici\b|\bhatirlat\b|\balarm kur\b|\bremind me\b")
_FILLER = re.compile(r"\b(?:bana|lutfen|diye|tekrar|bir|hatirlat\w*|hatirlatici\w*|alarm kur|kur|remind me to|remind me|"
                     r"olustur|ekle|kaydet|ayarla)\b")


def has_reminder_intent(text: str) -> bool:
    folded = fold_turkish(text)
    return bool(_ASK.search(folded)) and not re.search(r"\b(?:hatirlatici(?:lar)?(?:im| ne| neler| var| listesi)|iptal|sil|kaldir)\b", folded)


def parse_reminder(text: str, now: datetime | None = None) -> dict | None:
    """Return {"due": aware datetime, "text": str, "when": str} or {"error": ...}."""
    if not has_reminder_intent(text):
        return None
    local_now = (now or datetime.now(timezone.utc)).astimezone(HOME_TZ)
    folded, idx = fold_with_map(text)
    cut: list[tuple[int, int]] = []
    due: datetime | None = None
    if re.search(r"\b(?:dun|evvelsi gun|geen gun)\b", folded):
        return {"error": "past"}

    rel = _REL.search(folded)
    if rel:
        amount = 0.5 if rel.group(1) == "yarim" else _num(rel.group(1))
        if amount is None:
            return None
        if "buc" in rel.group(0):
            amount += 0.5
        seconds = amount * _UNIT_SECONDS[rel.group(2)]
        due = local_now + timedelta(seconds=seconds)
        cut.append(rel.span())
    else:
        day_offset, weekday = None, None
        day = _DAY_WORDS.search(folded)
        if day:
            word = day.group(1)
            if word == "bugun":
                day_offset = 0
            elif word == "yarin":
                day_offset = 1
            elif word in ("obur gun", "ertesi gun"):
                day_offset = 2
            else:
                weekday = _WEEKDAYS[word]
            cut.append(day.span())
        part = _PART.search(folded)
        hour = minute = None
        for pattern in (_CLOCK_COLON, _CLOCK_SAAT, _CLOCK_SUFFIX):
            m = pattern.search(folded)
            if m:
                hour = int(m.group(1))
                minute = int(m.group(2)) if m.lastindex and m.lastindex >= 2 and m.group(2) else 0
                cut.append(m.span())
                break
        if part:
            cut.append(part.span())
            if hour is None:
                hour, minute = _PART_DEFAULT[part.group(1)], 0
            elif part.group(1) in ("aksam", "gece", "ogleden sonra") and hour < 12:
                hour += 12
            elif part.group(1) == "ogle" and hour < 11:
                hour += 12
        if hour is None and day_offset is None and weekday is None:
            return {"error": "no_time"}
        if hour is None:
            hour, minute = 9, 0
        base = local_now.date()
        if weekday is not None:
            ahead = (weekday - base.weekday()) % 7 or 7
            target_date = base + timedelta(days=ahead)
        else:
            target_date = base + timedelta(days=day_offset or 0)
        due = datetime(target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=HOME_TZ)
        if day_offset is None and weekday is None and due <= local_now:
            due += timedelta(days=1)  # "saat 8'de" said at 20:00 means tomorrow
    if due is None or due <= local_now:
        return {"error": "past"}
    if due - local_now > MAX_AHEAD:
        return {"error": "too_far"}

    keep = list(folded)
    for a, b in cut:
        for i in range(a, b):
            keep[i] = None
    for m in _FILLER.finditer(folded):
        for i in range(*m.span()):
            keep[i] = None
    picked = sorted({idx[i] for i, c in enumerate(keep) if c is not None and i < len(idx)})
    message = "".join(text[i] for i in picked)
    message = re.sub(r"\s+", " ", re.sub(r"[?!,;:]+|(?<!\w)['’]+|['’]+(?!\w)", " ", message)).strip(" .-'’")
    message = re.sub(r"^(?:da|de|ta|te|ki)\s+", "", message, flags=re.IGNORECASE).strip()
    return {"due": due, "text": (message or "Hatırlatıcı")[:200], "when": describe_when(due, local_now)}


def describe_when(due: datetime, now: datetime) -> str:
    due, now = due.astimezone(HOME_TZ), now.astimezone(HOME_TZ)
    delta = due - now
    if delta < timedelta(hours=1):
        minutes = max(1, round(delta.total_seconds() / 60))
        return f"{minutes} dakika sonra ({due:%H:%M})"
    days = (due.date() - now.date()).days
    day = {0: "bugün", 1: "yarın"}.get(days)
    if day is None:
        names = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")
        day = f"{due.day}.{due.month:02d}.{due.year} {names[due.weekday()]}"
    return f"{day} {due:%H:%M}"


async def add_reminder(pool: Any, user_id: str, parsed: dict) -> int | None:
    count = await pool.fetchval("SELECT COUNT(*) FROM owner_reminders WHERE user_id=$1 AND status='pending'", user_id)
    if int(count or 0) >= MAX_PENDING:
        return None
    return await pool.fetchval(
        "INSERT INTO owner_reminders(user_id,text,due_at) VALUES($1,$2,$3) RETURNING id",
        user_id, parsed["text"], parsed["due"])


async def create_from_chat(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    parsed = parse_reminder(text, now)
    if parsed is None:
        return None
    if "error" in parsed:
        return {"no_time": "Ne zaman hatırlatayım? Örneğin “20 dakika sonra”, “yarın 09:00'da” ya da “bugün 18:30'da” diyebilirsin.",
                "past": "Bu zaman geçmişte kaldı. Gelecekte bir zaman söyler misin?",
                "too_far": "Bir yıldan uzak hatırlatıcı kuramıyorum."}[parsed["error"]]
    rid = await add_reminder(pool, user_id, parsed)
    if rid is None:
        return f"En fazla {MAX_PENDING} bekleyen hatırlatıcı tutabiliyorum; önce bazılarını iptal edelim."
    return (f"Tamam, {parsed['when']} “{parsed['text']}” diye hatırlatacağım. "
            "Not: Hatırlatıcı GÖLGE sayfası/uygulaması açıkken ses ve bildirimle gelir; "
            "telefon kilitliyken sistem bildirimi gönderemiyorum.")


_LIST_Q = re.compile(r"\bhatirlaticilar(?:im| neler| ne| var| listesi| goster)|\bhatirlaticilari (?:goster|listele|say)|\bne hatirlatacaksin\b|\bhangi hatirlatici")
_CANCEL_Q = re.compile(r"\bhatirlaticilari(?:mi)? (?:iptal|sil|kaldir|temizle)|\btum hatirlaticilari\b.*\b(?:iptal|sil)|\bhatirlaticilar(?:i)? (?:iptal|sil)")


async def list_pending(pool: Any, user_id: str, limit: int = 8) -> list[dict]:
    rows = await pool.fetch(
        "SELECT id,text,due_at FROM owner_reminders WHERE user_id=$1 AND status='pending' ORDER BY due_at LIMIT $2",
        user_id, limit)
    return [dict(r) for r in rows]


async def manage_from_chat(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    folded = fold_turkish(text)
    local_now = (now or datetime.now(timezone.utc)).astimezone(HOME_TZ)
    if _CANCEL_Q.search(folded):
        count = await pool.fetchval(
            "WITH c AS (UPDATE owner_reminders SET status='cancelled' WHERE user_id=$1 AND status='pending' RETURNING 1) SELECT COUNT(*) FROM c",
            user_id)
        return f"{int(count or 0)} bekleyen hatırlatıcıyı iptal ettim." if count else "İptal edilecek bekleyen hatırlatıcı yok."
    if _LIST_Q.search(folded):
        items = await list_pending(pool, user_id)
        if not items:
            return "Bekleyen hatırlatıcın yok."
        lines = [f"• {describe_when(r['due_at'], local_now)} — {r['text']}" for r in items]
        return "Bekleyen hatırlatıcıların:\n" + "\n".join(lines)
    return None


# ── HTTP: in-app delivery ───────────────────────────────────────────────────

def _check_origin(request: web.Request) -> None:
    if request.method in ("POST", "DELETE") and request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
        raise web.HTTPForbidden(text='{"error":"cross_origin_denied"}', content_type="application/json")


async def due_reminders(request: web.Request) -> web.Response:
    rows = await request.app["db"].fetch(
        "UPDATE owner_reminders SET status='delivered',delivered_at=NOW() "
        "WHERE id IN (SELECT id FROM owner_reminders WHERE user_id=$1 AND status='pending' AND due_at<=NOW() "
        "ORDER BY due_at LIMIT 10 FOR UPDATE SKIP LOCKED) "
        "RETURNING id,text,due_at,(NOW()-due_at) > INTERVAL '10 minutes' AS late",
        request["user_id"])
    try:
        if __package__:
            from .proactive import due_notifications
        else:
            from proactive import due_notifications
        notes = await due_notifications(request.app["db"], request["user_id"])
    except Exception:
        notes = []
    return web.json_response({"due": [{"id": r["id"], "text": r["text"], "due_at": r["due_at"].isoformat(),
                                       "late": bool(r["late"])} for r in rows],
                              "notifications": notes})


async def pending_reminders(request: web.Request) -> web.Response:
    items = await list_pending(request.app["db"], request["user_id"], 50)
    return web.json_response({"reminders": [{"id": r["id"], "text": r["text"], "due_at": r["due_at"].isoformat()} for r in items]})


async def cancel_reminder(request: web.Request) -> web.Response:
    _check_origin(request)
    raw = request.match_info.get("id", "")
    if not re.fullmatch(r"[1-9]\d{0,17}", raw):
        raise web.HTTPBadRequest(text='{"error":"invalid_id"}', content_type="application/json")
    row = await request.app["db"].fetchrow(
        "UPDATE owner_reminders SET status='cancelled' WHERE id=$1 AND user_id=$2 AND status='pending' RETURNING id",
        int(raw), request["user_id"])
    if row is None:
        raise web.HTTPNotFound(text='{"error":"not_found"}', content_type="application/json")
    return web.json_response({"cancelled": True, "id": int(raw)})


async def snooze_reminder(request: web.Request) -> web.Response:
    """Re-create a delivered reminder N minutes from now (owner tapped 'ertele')."""
    _check_origin(request)
    raw = request.match_info.get("id", "")
    if not re.fullmatch(r"[1-9]\d{0,17}", raw):
        raise web.HTTPBadRequest(text='{"error":"invalid_id"}', content_type="application/json")
    try:
        minutes = int((await request.json()).get("minutes", 10))
    except (ValueError, TypeError, AttributeError):
        minutes = 10
    minutes = max(1, min(minutes, 24 * 60))
    row = await request.app["db"].fetchrow(
        "UPDATE owner_reminders SET status='pending',delivered_at=NULL,due_at=NOW()+make_interval(mins=>$3) "
        "WHERE id=$1 AND user_id=$2 AND status='delivered' RETURNING id,due_at",
        int(raw), request["user_id"], minutes)
    if row is None:
        raise web.HTTPNotFound(text='{"error":"not_found"}', content_type="application/json")
    return web.json_response({"snoozed": True, "id": row["id"], "due_at": row["due_at"].isoformat()})


def register_routes(app: web.Application) -> None:
    app.router.add_get("/api/reminders", pending_reminders)
    app.router.add_get("/api/reminders/due", due_reminders)
    app.router.add_delete("/api/reminders/{id}", cancel_reminder)
    app.router.add_post("/api/reminders/{id}/snooze", snooze_reminder)
