"""Pomodoro / focus sessions built on reminders: "pomodoro başlat", "50 dakika odaklan", "pomodoro 25 5", "odak modunu kapat"."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

if __package__:
    from .text_normalization import fold_turkish
    from .reminders import HOME_TZ
else:
    from text_normalization import fold_turkish
    from reminders import HOME_TZ

MARK = "🍅"
_START = re.compile(r"^\s*(?:lutfen\s+)?(?:pomodoro(?:\s+(?:baslat|kur|modu))?(?:\s+(\d{1,3})\s+(\d{1,2}))?|(?:(\d{1,3})\s*(?:dakika|dk)\s+)?(?:odaklan(?:ma modu|mamı baslat|mayi baslat)?|odak modu(?:nu)? (?:baslat|ac)|calisma modu(?:nu)? (?:baslat|ac))(?:\s+(\d{1,3})\s*(?:dakika|dk))?)\s*$")
_STOP = re.compile(r"^\s*(?:pomodoro\w*|odak modu\w*|odaklanma modu\w*|calisma modu\w*)\s+(?:durdur|iptal|kapat|bitir)\w*\s*$|^\s*(?:durdur|iptal et|kapat)\s+pomodoro\w*\s*$")


def wants_focus(text: str) -> bool:
    f = fold_turkish(text)
    return len(f) <= 60 and bool(_START.match(f) or _STOP.match(f))


async def handle(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    if pool is None or not wants_focus(text):
        return None
    f = fold_turkish(text)
    if _STOP.match(f):
        n = await pool.fetchval("WITH c AS (UPDATE owner_reminders SET status='cancelled' WHERE user_id=$1 AND status='pending' AND text LIKE $2 RETURNING 1) SELECT COUNT(*) FROM c",
                                user_id, MARK + "%")
        return "Odak oturumunu iptal ettim." if n else "Çalışan bir odak oturumu yok."
    m = _START.match(f)
    work = next((int(g) for g in (m.group(3), m.group(4), m.group(1)) if g), 25)
    rest = int(m.group(2)) if m.group(2) else (5 if work <= 30 else 10)
    if not 5 <= work <= 180 or not 1 <= rest <= 60:
        return "Odak süresi 5–180 dakika, mola 1–60 dakika olabilir. Örn. “pomodoro 25 5” ya da “50 dakika odaklan”."
    running = await pool.fetchval("SELECT COUNT(*) FROM owner_reminders WHERE user_id=$1 AND status='pending' AND text LIKE $2", user_id, MARK + "%")
    if int(running or 0):
        return "Zaten çalışan bir odak oturumun var. Önce “pomodoro durdur” de."
    start = (now or datetime.now(timezone.utc)).astimezone(HOME_TZ)
    t_break, t_back = start + timedelta(minutes=work), start + timedelta(minutes=work + rest)
    for when, label in ((t_break, f"{MARK} Mola zamanı ☕ ({rest} dk dinlen)"), (t_back, f"{MARK} Mola bitti, odaklanma zamanı!")):
        await pool.execute("INSERT INTO owner_reminders(user_id,text,due_at) VALUES($1,$2,$3)", user_id, label, when)
    return (f"{MARK} Odak başladı: {work} dk çalış, sonra {rest} dk mola. Mola bildirimi {t_break:%H:%M}, dönüş bildirimi {t_back:%H:%M}. "
            "Bildirimler GÖLGE açıkken ya da bildirimleri açtıysan kilitliyken gelir. İptal için “pomodoro durdur”.")
