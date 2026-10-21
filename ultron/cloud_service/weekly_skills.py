"""Weekly review from the owner's own data: "haftalık özet", "geçen hafta nasıldı", "haftalık rapor".

Read-only; every line comes from stored rows (plans, habits, expenses, journal, reminders, usage) and a
section is omitted when there is nothing recorded, so the review never invents activity."""
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

_ASK = re.compile(r"^(?:(bu|gecen)\s+hafta(?:nin)?\s+(?:ozeti|raporu|ozet|rapor)|haftalik\s+(?:ozet|rapor|degerlendirme)|(bu|gecen)\s+hafta\s+nasil(?:di|\s+gecti)|haftami\s+(?:ozetle|degerlendir))\s*\??$")
_HABIT_TR = {"water": ("su", "bardak"), "sleep": ("uyku", "saat"), "exercise": ("spor", "dk"), "steps": ("adım", ""), "mood": ("mod", "/5")}


def wants_weekly(text: str) -> bool:
    f = fold_turkish(text)
    return len(f) <= 50 and bool(_ASK.match(f))


def _n(v: float) -> str:
    return f"{v:,.1f}".rstrip("0").rstrip(".").replace(",", ".") if v % 1 else f"{int(v):,}".replace(",", ".")


async def handle(text: str, pool: Any, user_id: str, now: datetime | None = None) -> str | None:
    if pool is None or not wants_weekly(text):
        return None
    f = fold_turkish(text)
    today = (now or datetime.now(timezone.utc)).astimezone(HOME_TZ).date()
    monday = today - timedelta(days=today.weekday())
    if "gecen" in f:
        start, end, label = monday - timedelta(days=7), monday - timedelta(days=1), "Geçen hafta"
    else:
        start, end, label = monday, today, "Bu hafta"
    lines = []
    done = await pool.fetchrow("SELECT COUNT(*) FILTER (WHERE is_done) AS done, COUNT(*) AS total FROM owner_plans WHERE user_id=$1 AND scheduled_date BETWEEN $2 AND $3", user_id, start, end)
    if done and int(done["total"]):
        lines.append(f"📅 Planlar: {int(done['done'])}/{int(done['total'])} tamamlandı")
    habits = await pool.fetch("SELECT habit, SUM(amount) AS total, COUNT(DISTINCT day) AS days FROM owner_habits WHERE user_id=$1 AND day BETWEEN $2 AND $3 GROUP BY habit ORDER BY habit", user_id, start, end)
    parts = []
    for r in habits:
        name, unit = _HABIT_TR.get(r["habit"], (r["habit"], ""))
        if r["habit"] in ("sleep", "mood"):
            parts.append(f"{name} ort. {_n(float(r['total']) / max(1, int(r['days'])))}{(' ' + unit) if unit else ''}")
        elif r["habit"] != "weight":
            parts.append(f"{name} {_n(float(r['total']))}{(' ' + unit) if unit else ''} ({int(r['days'])} gün)")
    if parts:
        lines.append("💧 Alışkanlık: " + " · ".join(parts))
    spent = await pool.fetch("SELECT category, SUM(amount) AS total FROM owner_expenses WHERE user_id=$1 AND spent_on BETWEEN $2 AND $3 GROUP BY category ORDER BY total DESC", user_id, start, end)
    if spent:
        total = sum(float(r["total"]) for r in spent)
        lines.append(f"💸 Harcama: {_n(total)} ₺, en çok {spent[0]['category']} ({_n(float(spent[0]['total']))} ₺)")
    j = await pool.fetchval("SELECT COUNT(*) FROM owner_journal WHERE user_id=$1 AND day BETWEEN $2 AND $3", user_id, start, end)
    if int(j or 0):
        lines.append(f"📓 Günlük: {int(j)} girdi")
    rem = await pool.fetchval("SELECT COUNT(*) FROM owner_reminders WHERE user_id=$1 AND status='delivered' AND delivered_at::date BETWEEN $2 AND $3", user_id, start, end)
    if int(rem or 0):
        lines.append(f"⏰ Tetiklenen hatırlatıcı: {int(rem)}")
    top = await pool.fetch("SELECT skill, SUM(n)::int AS n FROM skill_usage WHERE user_id=$1 AND day BETWEEN $2 AND $3 GROUP BY skill ORDER BY n DESC, skill LIMIT 3", user_id, start, end)
    if top:
        lines.append("🧭 En çok kullandığın: " + ", ".join(f"{r['skill']} ({r['n']})" for r in top))
    if not lines:
        return f"{label} için kayıtlı bir veri yok. Plan, alışkanlık, harcama ya da günlük kaydettikçe burada özetlerim."
    return f"📊 {label} ({start:%d.%m}–{end:%d.%m}):\n" + "\n".join(lines)
