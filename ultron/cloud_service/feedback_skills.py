"""Self-improvement loop: feedback on answers, usage counters and gentle suggestions.

"yanlış anladın" / "tam istediğim buydu" are stored against the previous exchange,
"en çok kullandığım komutlar" reads the per-day counters, and `maybe_suggest` offers at
most one data-backed tip per day (never a new permission or an action). Feedback is
exported for the routing corpus so real mis-routes become regression cases.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

if __package__:
    from .memory_safety import contains_common_secret
    from .text_normalization import fold_turkish
    from .reminders import HOME_TZ
    from . import proactive
else:
    from memory_safety import contains_common_secret
    from text_normalization import fold_turkish
    from reminders import HOME_TZ
    import proactive

_BAD = re.compile(r"^(?:hayir\s+)?(?:yanlis\s+anladin|yanlis\s+anlamissin|bunu\s+istemedim|istedigim\s+(?:bu\s+degil|bu\s+degildi)|bu\s+(?:yanlis|dogru\s+degil)|yanlis\s+cevap|olmadi|hatali\s+cevap|bu\s+hatali)\s*[.!]*$")
_GOOD = re.compile(r"^(?:evet\s+)?(?:dogru\s+anladin|tam\s+istedigim\s+(?:buydu|bu)|tam\s+istedigim\s+gibi|bu\s+(?:dogruydu|dogru)|dogru\s+cevap|cok\s+iyi\s+cevap|isime\s+yaradi|ise\s+yaradi|aferin)\s*[.!]*$")
_TOP = re.compile(r"^(?:en\s+cok\s+kullandigim\s+(?:komutlar|yetenekler|ozellikler)|kullanim\s+(?:istatistiklerim|ozetim)|ne\s+kadar\s+kullandim|en\s+cok\s+ne\s+soruyorum)\s*\??$")
_STATS = re.compile(r"^(?:geri\s+bildirim(?:lerim)?(?:\s+ozeti)?|geri\s+bildirimlerim\s+neler)\s*\??$")
_SUGGEST = re.compile(r"^(?:bana\s+)?(?:bir\s+)?(?:oneri(?:n)?(?:\s+var\s+mi|\s+ver)?|ne\s+onerirsin|neyi\s+gelistirebilirim|beni\s+nasil\s+daha\s+iyi\s+kullanirim)\s*\??$")
NAMES = {"weather": "hava durumu", "reminder": "hatırlatıcı kurma", "reminders": "hatırlatıcı yönetimi", "clock": "saat/tarih",
         "math": "hesaplama", "units": "birim çevirme", "currency": "döviz", "crypto": "kripto", "news": "haber", "wiki": "Vikipedi",
         "plans": "planlar", "memory": "hafıza", "lists": "listeler", "expenses": "harcamalar", "habits": "alışkanlıklar",
         "focus": "odak/pomodoro", "navigation": "yol tarifi", "briefing": "günlük özet", "agenda": "gündem", "prayer": "namaz vakti",
         "smart_home": "akıllı ev", "birthdays": "doğum günleri", "alerts": "uyarılar", "chat": "sohbet"}


def wants_feedback(text: str) -> bool:
    f = fold_turkish(text)
    return len(f) <= 60 and bool(_BAD.match(f) or _GOOD.match(f) or _TOP.match(f) or _STATS.match(f) or _SUGGEST.match(f))


def _local_day(now: datetime | None) -> date:
    return (now or datetime.now(timezone.utc)).astimezone(HOME_TZ).date()


async def record_usage(pool: Any, user_id: str, skill: str, now: datetime | None = None) -> None:
    if pool is None or not skill or skill == "feedback":
        return
    try:
        await pool.execute(
            "INSERT INTO skill_usage(user_id,day,skill) VALUES($1,$2,$3) "
            "ON CONFLICT(user_id,day,skill) DO UPDATE SET n=skill_usage.n+1",
            user_id, _local_day(now), skill[:40])
    except Exception:
        pass  # usage counters must never break an answer


async def usage_top(pool: Any, user_id: str, now: datetime | None = None, days: int = 30, limit: int = 5) -> list[tuple[str, int]]:
    since = _local_day(now) - timedelta(days=days)
    rows = await pool.fetch("SELECT skill,SUM(n)::int AS n FROM skill_usage WHERE user_id=$1 AND day>=$2 GROUP BY skill ORDER BY n DESC, skill LIMIT $3",
                            user_id, since, limit)
    return [(r["skill"], int(r["n"])) for r in rows]


async def _active_days(pool, user_id, skill, now, days=14) -> int:
    since = _local_day(now) - timedelta(days=days)
    return int(await pool.fetchval("SELECT COUNT(*) FROM skill_usage WHERE user_id=$1 AND skill=$2 AND day>=$3", user_id, skill, since) or 0)


async def _candidate(pool, user_id, now) -> tuple[str, str] | None:
    prefs = await proactive.get_prefs(pool, user_id)
    if await _active_days(pool, user_id, "weather", now) >= 3 and not prefs.get("morning_brief"):
        return "weather_brief", "Hava durumunu sık soruyorsun. “sabah brifingini aç” dersen her sabah hava ve gününün özeti kendiliğinden gelir."
    if (await _active_days(pool, user_id, "reminder", now) >= 3 or await _active_days(pool, user_id, "reminders", now) >= 3):
        has_push = await pool.fetchval("SELECT COUNT(*) FROM push_subscriptions WHERE user_id=$1", user_id)
        if not int(has_push or 0):
            return "enable_push", "Sık hatırlatıcı kuruyorsun ama bildirimler kapalı. GÖLGE’yi ana ekrana ekleyip bildirimleri açarsan telefon kilitliyken de çalarlar."
    if await _active_days(pool, user_id, "expenses", now) >= 3 and await _active_days(pool, user_id, "habits", now) == 0:
        return "habits", "Harcamalarını takip ediyorsun; istersen su, uyku ya da spor için de “2 bardak su içtim” gibi kayıt tutabilirim."
    return None


async def next_suggestion(pool: Any, user_id: str, now: datetime | None = None, *, force: bool = False) -> str | None:
    """One data-backed tip; unless `force`, at most one per day and each tip at most once a week."""
    cand = await _candidate(pool, user_id, now)
    if cand is None:
        return None
    key, tip = cand
    today = _local_day(now)
    state = await proactive.get_extra(pool, user_id, "suggested", {}) or {}
    if not force:
        if state.get("_last") == today.isoformat():
            return None
        seen = state.get(key)
        if seen and (today - date.fromisoformat(seen)).days < 7:
            return None
    state[key] = today.isoformat()
    state["_last"] = today.isoformat()
    await proactive.set_extra(pool, user_id, "suggested", state)
    return tip


async def maybe_suggest(pool: Any, user_id: str, now: datetime | None = None) -> str:
    try:
        tip = await next_suggestion(pool, user_id, now)
    except Exception:
        return ""
    return f"\n\n💡 {tip}" if tip else ""


async def record_feedback(pool: Any, user_id: str, rating: str, skill: str = "", user_text: str = "", reply: str = "") -> int:
    # Never keep secrets in the feedback table; the rating itself is still recorded.
    if contains_common_secret(f"{user_text}\n{reply}"):
        user_text, reply = "", ""
    duplicate = await pool.fetchval(
        "SELECT id FROM skill_feedback WHERE user_id=$1 AND rating=$2 AND user_text=$3 AND reply=$4 AND created_at>NOW()-INTERVAL '1 day' LIMIT 1",
        user_id, rating, str(user_text)[:300], str(reply)[:600])
    if duplicate:
        return int(duplicate)
    return int(await pool.fetchval(
        "INSERT INTO skill_feedback(user_id,rating,skill,user_text,reply) VALUES($1,$2,$3,$4,$5) RETURNING id",
        user_id, rating, str(skill)[:40], str(user_text)[:300], str(reply)[:600]))


async def handle(text: str, pool: Any, user_id: str, now: datetime | None = None, history: dict | None = None) -> str | None:
    """`history` = {"user", "reply", "skill"} of the previous exchange, supplied by /api/chat."""
    if pool is None or not wants_feedback(text):
        return None
    f = fold_turkish(text)
    rating = "bad" if _BAD.match(f) else "good" if _GOOD.match(f) else None
    if rating:
        h = history or {}
        if not h.get("user"):
            return "Hangi cevaptan bahsettiğini göremedim; önce bir şey sor, sonra “yanlış anladın” ya da “tam istediğim buydu” de."
        await record_feedback(pool, user_id, rating, h.get("skill", ""), h.get("user", ""), h.get("reply", ""))
        if rating == "good":
            return "Sevindim, bunu not aldım."
        quoted = str(h["user"])[:80]
        return f"Üzgünüm, “{quoted}” isteğini yanlış anlamışım. Kaydettim; biraz farklı söyleyerek tekrar dener misin?"
    if _TOP.match(f):
        top = await usage_top(pool, user_id, now)
        if not top:
            return "Henüz yeterli kullanım verisi yok; biraz kullandıkça burada görünür."
        lines = "\n".join(f"{i}. {NAMES.get(s, s)} — {n} kez" for i, (s, n) in enumerate(top, 1))
        return "Son 30 günde en çok kullandıkların:\n" + lines
    if _STATS.match(f):
        rows = await pool.fetch("SELECT rating,COUNT(*) AS n FROM skill_feedback WHERE user_id=$1 GROUP BY rating", user_id)
        c = {r["rating"]: int(r["n"]) for r in rows}
        if not c:
            return "Henüz geri bildirim vermedin. Bir cevap yanlışsa “yanlış anladın”, doğruysa “tam istediğim buydu” de."
        return f"Geri bildirimlerin: {c.get('good', 0)} olumlu, {c.get('bad', 0)} olumsuz. Olumsuzlar yönlendirme testlerime eklenmek üzere saklanıyor."
    tip = await next_suggestion(pool, user_id, now, force=True)
    return tip or "Şu an kullanımına göre özel bir önerim yok. Yapabildiklerimi görmek için “neler yapabilirsin” de."


def corpus_lines(rows: list[dict]) -> list[str]:
    """Turn exported feedback rows into routing-corpus candidates for a human to label and review."""
    out, seen = [], set()
    for r in rows:
        text = " ".join(str(r.get("user_text", "")).split())
        if r.get("rating") != "bad" or not text or text in seen:
            continue
        seen.add(text)
        out.append(f"    ({json.dumps(text, ensure_ascii=False)}, None),  # was routed to {r.get('skill') or 'chat'!r}: set the correct label")
    return out
