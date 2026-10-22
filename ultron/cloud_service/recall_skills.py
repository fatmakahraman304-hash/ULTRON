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

_ABOUT_KNOW = re.compile(r"^(?:peki\s+)?(.{2,40}?)\s+(?:hakkinda|ile ilgili|icin)\s+(?:bana\s+)?ne\s+(?:biliyorsun|hatirliyorsun|biliyon|hatirliyon)\s*\??$")
_ABOUT_TALK = re.compile(r"^(?:peki\s+)?(.{2,40}?)\s+(?:hakkinda|ile ilgili|konusunda)\s+(?:ne\s+)?(?:konusmustuk|konustuk|konusmustuk|konusmustum|yazmistik|demistim|soylemistim)\s*\??$|^(?:peki\s+)?(.{2,40}?)\s+(?:hakkinda|ile ilgili)\s+ne\s+(?:konusmustuk|konustuk|demistim|soylemistim)\s*\??$")
_WHEN_TALK = re.compile(r"^(?:peki\s+)?(bugun|dun|evvelsi gun|onceki gun|bu hafta|gecen hafta|son bir hafta|son 7 gun)\s+(?:biz\s+)?ne\s+(?:konustuk|konusmustuk|yaptik|sordum|sormustum)\s*\??$|^(?:peki\s+)?(?:biz\s+)?ne\s+(?:konustuk|konusmustuk)\s+(bugun|dun|bu hafta|gecen hafta)\s*\??$")
_SUMMARY = re.compile(r"^(?:hafiza\s+ozeti|hafiza\s+ozetin|hafizanin\s+ozeti|hafiza\s+durumu|neler\s+biliyorsun\s+ozetle)\s*\??$")
_RECENT = re.compile(r"^son\s+(?:(\d{1,2})\s+)?(?:notlarim|kayitlarim|kaydettiklerim|kayit|not)\s*\??$|^(bugun|dun|bu hafta|gecen hafta)\s+ne\s+(?:kaydettim|ekledim|not\s+aldim)\s*\??$")
_RESUME = re.compile(r"^(?:peki\s+)?(?:nerede\s+kalmistik|en\s+son\s+ne\s+konustuk|en\s+son\s+ne\s+konusmustuk|son\s+konusmamiz\s+neydi)\s*\??$")
_PROFILE = re.compile(r"^(?:bana\s+kendimi\s+anlat|beni\s+ozetle|profilim|beni\s+ne\s+kadar\s+taniyorsun\s+ozetle|kimim\s+ben)\s*\??$")
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
    return bool(_WHEN_TALK.match(f) or _SUMMARY.match(f) or _RECENT.match(f) or _RESUME.match(f) or _PROFILE.match(f))


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
    if _PROFILE.match(f):
        async def count(sql: str) -> int:
            return int(await pool.fetchval(sql, user_id) or 0)
        prefs = await pool.fetchval("SELECT prefs FROM owner_prefs WHERE user_id=$1", user_id)
        if isinstance(prefs, str):
            import json as _json
            try:
                prefs = _json.loads(prefs)
            except ValueError:
                prefs = {}
        style = (prefs or {}).get("style") or {}
        bits = []
        if style.get("name"):
            bits.append(f"Sana {style['name']} diyorum")
        mems = await count("SELECT COUNT(*) FROM memories WHERE user_id=$1")
        if mems:
            bits.append(f"{mems} şeyi hafızama kaydettim")
        for sql, label in (("SELECT COUNT(*) FROM owner_goals WHERE user_id=$1", "hedefin"), ("SELECT COUNT(*) FROM owner_routines WHERE user_id=$1", "rutinin"),
                           ("SELECT COUNT(*) FROM owner_contacts WHERE user_id=$1", "kişi kaydın"), ("SELECT COUNT(*) FROM kb_docs WHERE user_id=$1", "bilgi tabanı kaydın"),
                           ("SELECT COUNT(DISTINCT habit) FROM owner_habits WHERE user_id=$1", "takip ettiğin alışkanlık")):
            n = await count(sql)
            if n:
                bits.append(f"{n} {label} var")
        if (prefs or {}).get("budget"):
            bits.append("aylık bütçe takibi açık")
        top = await pool.fetch("SELECT skill,SUM(n)::int AS n FROM skill_usage WHERE user_id=$1 GROUP BY skill ORDER BY n DESC LIMIT 3", user_id)
        if top:
            bits.append("en çok kullandığın: " + ", ".join(r["skill"] for r in top))
        if not bits:
            return "Seni daha yeni tanıyorum: henüz kayıtlı bir şeyim yok. Bana kendinden bahset ya da “hatırla: …” de, hemen başlayalım. 🤖"
        return "Seni şöyle tanıyorum: " + "; ".join(bits) + ". (Hepsi senin kayıtlarından; hiçbirini uydurmadım.)"
    if _RESUME.match(f):
        rows = [r for r in await _past_messages(pool, user_id, limit=40) if not _is_recall_query(r["content"])][:3]
        if not rows:
            return "Daha önce bir konuşma kaydı bulamadım; yeni bir sohbete başlayabiliriz."
        rows = list(reversed(rows))
        return "En son şunları konuşmuştuk:\n" + "\n".join(f"• {_day(r['created_at'])} — {_clip(r['content'])}" for r in rows) + "\nKaldığımız yerden devam edelim mi?"
    m = _RECENT.match(f)
    if m:
        if m.group(2):
            start, end, label = _window(m.group(2), now)
            rows = await pool.fetch("SELECT category,key,value,updated_at FROM memories WHERE user_id=$1 AND updated_at>=$2 AND updated_at<$3 ORDER BY updated_at DESC LIMIT 8", user_id, start, end)
            empty = f"{label} hafızaya yeni bir şey kaydetmemişsin."
        else:
            rows = await pool.fetch("SELECT category,key,value,updated_at FROM memories WHERE user_id=$1 ORDER BY updated_at DESC LIMIT $2", user_id, min(int(m.group(1) or 5), 10))
            empty = "Hafızamda henüz kayıtlı bir şey yok."
        if not rows:
            return empty
        return "Hafızadaki kayıtlar:\n" + "\n".join(f"• {_day(r['updated_at'])} — {_clip(r['value'], 100)}" for r in rows)
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
