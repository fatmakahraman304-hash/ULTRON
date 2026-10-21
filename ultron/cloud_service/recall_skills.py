"""Recall over what GÖLGE already knows: saved memories and past conversation.

"ahmet hakkında ne biliyorsun", "dün ne konuştuk", "geçen hafta ne konuştuk",
"kahve hakkında ne konuşmuştuk", "hafıza özeti". Read-only, owner-scoped, no model call:
answers are quoted from the owner's own rows and say so when nothing matches.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

if __package__:
    from .text_normalization import fold_turkish
    from .reminders import HOME_TZ
else:
    from text_normalization import fold_turkish
    from reminders import HOME_TZ

_ABOUT_KNOW = re.compile(r"^(?:peki\s+)?(.{2,40}?)\s+(?:hakkinda|ile ilgili|icin)\s+(?:bana\s+)?ne\s+(?:biliyorsun|hatirliyorsun|biliyon|hatirlıyon)\s*\??$")
_ABOUT_TALK = re.compile(r"^(?:peki\s+)?(.{2,40}?)\s+(?:hakkinda|ile ilgili|konusunda)\s+(?:ne\s+)?(?:konusmustuk|konustuk|konusmustuk|konusmustum|yazmistik|demistim|soylemistim)\s*\??$|^(?:peki\s+)?(.{2,40}?)\s+(?:hakkinda|ile ilgili)\s+ne\s+(?:konusmustuk|konustuk|demistim|soylemistim)\s*\??$")
_WHEN_TALK = re.compile(r"^(?:peki\s+)?(bugun|dun|evvelsi gun|onceki gun|bu hafta|gecen hafta|son bir hafta|son 7 gun)\s+(?:biz\s+)?ne\s+(?:konustuk|konusmustuk|yaptik|sordum|sormustum)\s*\??$|^(?:peki\s+)?(?:biz\s+)?ne\s+(?:konustuk|konusmustuk)\s+(bugun|dun|bu hafta|gecen hafta)\s*\??$")
_SUMMARY = re.compile(r"^(?:hafiza\s+ozeti|hafiza\s+ozetin|hafizanin\s+ozeti|hafiza\s+durumu|neler\s+biliyorsun\s+ozetle)\s*\??$")
_SELF = {"ben", "benim", "beni", "bu", "su", "o", "bunlar", "sen", "seni", "kendin", "kendini"}
MAX_SCAN = 600


def wants_recall(text: str) -> bool:
    f = fold_turkish(text)
    if len(f) > 90:
        return False
    for rx in (_ABOUT_KNOW, _ABOUT_TALK):
        m = rx.match(f)
        if m and _topic(m) not in _SELF:
            return True
    return bool(_WHEN_TALK.match(f) or _SUMMARY.match(f))


def _topic(m: re.Match) -> str:
    return next((g for g in m.groups() if g), "").strip()


def _window(word: str, now: datetime) -> tuple[datetime, datetime, str]:
    local = now.astimezone(HOME_TZ)
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if word == "bugun":
        return midnight, midnight + timedelta(days=1), "Bugün"
    if word == "dun":
        return midnight - timedelta(days=1), midnight, "Dün"
    if word in ("evvelsi gun", "onceki gun"):
        return midnight - timedelta(days=2), midnight - timedelta(days=1), "Evvelsi gün"
    if word == "bu hafta":
        return midnight - timedelta(days=local.weekday()), midnight + timedelta(days=1), "Bu hafta"
    start_this = midnight - timedelta(days=local.weekday())
    if word == "gecen hafta":
        return start_this - timedelta(days=7), start_this, "Geçen hafta"
    return midnight - timedelta(days=7), midnight + timedelta(days=1), "Son 7 gün"


def _clip(text: str, n: int = 90) -> str:
    one = " ".join(str(text).split())
    return one if len(one) <= n else one[: n - 1] + "…"


async def _memories(pool, user_id, topic):
    rows = await pool.fetch(
        "SELECT category,key,value,updated_at FROM memories WHERE user_id=$1 ORDER BY updated_at DESC LIMIT 400", user_id)
    needle = fold_turkish(topic)
    return [r for r in rows if needle in fold_turkish(f"{r['key']} {r['value']}")]


async def _past_messages(pool, user_id, *, since=None, until=None, limit=MAX_SCAN):
    return await pool.fetch(
        "SELECT content,created_at FROM messages WHERE user_id=$1 AND role='user' "
        "AND ($2::timestamptz IS NULL OR created_at>=$2) AND ($3::timestamptz IS NULL OR created_at<$3) "
        "ORDER BY id DESC LIMIT $4", user_id, since, until, limit)


def _is_recall_query(content: str) -> bool:
    return wants_recall(content)


def _day(dt: datetime) -> str:
    return dt.astimezone(HOME_TZ).strftime("%d.%m %H:%M")


async def handle(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    if pool is None or not wants_recall(text):
        return None
    f = fold_turkish(text)
    now = now or datetime.now(timezone.utc)
    if _SUMMARY.match(f):
        rows = await pool.fetch("SELECT category,COUNT(*) AS n FROM memories WHERE user_id=$1 GROUP BY category ORDER BY n DESC", user_id)
        if not rows:
            return "Hafızamda henüz kayıtlı bir şey yok. “hatırla: …” diyerek bir şey ekleyebilirsin."
        total = sum(int(r["n"]) for r in rows)
        cats = ", ".join(f"{r['category'].lower()} ({r['n']})" for r in rows[:6])
        return f"Hafızamda {total} kayıt var: {cats}. Ayrıntı için “neler hatırlıyorsun” ya da “… hakkında ne biliyorsun” de."
    m = _WHEN_TALK.match(f)
    if m:
        start, end, label = _window(_topic(m), now)
        rows = [r for r in await _past_messages(pool, user_id, since=start, until=end) if not _is_recall_query(r["content"])]
        if not rows:
            return f"{label} benimle yazılı/sesli bir konuşma kaydı bulamadım."
        rows = list(reversed(rows))
        shown = rows[:6]
        lines = "\n".join(f"• {_day(r['created_at'])} — {_clip(r['content'])}" for r in shown)
        more = f"\n(+{len(rows) - len(shown)} mesaj daha)" if len(rows) > len(shown) else ""
        return f"{label} {len(rows)} mesaj yazmışsın. Öne çıkanlar:\n{lines}{more}"
    m = _ABOUT_KNOW.match(f)
    if m:
        topic = _topic(m)
        mems = await _memories(pool, user_id, topic)
        msgs = [r for r in await _past_messages(pool, user_id) if fold_turkish(topic) in fold_turkish(r["content"]) and not _is_recall_query(r["content"])]
        if not mems and not msgs:
            return None  # general knowledge question ("Atatürk hakkında ne biliyorsun") → normal model answer
        out = []
        if mems:
            out.append(f"Hafızamda “{topic}” ile ilgili {len(mems)} kayıt var:\n" + "\n".join(f"• {_clip(r['value'], 110)}" for r in mems[:4]))
        if msgs:
            out.append(f"Geçmiş konuşmalarda {len(msgs)} kez geçmiş; en yenisi ({_day(msgs[0]['created_at'])}): {_clip(msgs[0]['content'])}")
        return "\n".join(out)
    m = _ABOUT_TALK.match(f)
    topic = _topic(m)
    msgs = [r for r in await _past_messages(pool, user_id) if fold_turkish(topic) in fold_turkish(r["content"]) and not _is_recall_query(r["content"])]
    if not msgs:
        return f"“{topic}” hakkında geçmiş konuşmalarda bir şey bulamadım."
    days = Counter(_day(r["created_at"])[:5] for r in msgs)
    lines = "\n".join(f"• {_day(r['created_at'])} — {_clip(r['content'])}" for r in reversed(msgs[:4]))
    return f"“{topic}” {len(msgs)} mesajda geçiyor ({len(days)} farklı gün). Son mesajlar:\n{lines}"
