"""Situational awareness: proactive suggestions computed from the owner's own calendar, plans, habits and budget.

Opt-in ("akıllı öneriler aç"). Each rule is real arithmetic over recorded data and fires at most once per key
(per day/week); quiet hours are applied by the caller. A rule may attach a PROPOSED action to the approval queue
("onayla N") — it never changes anything by itself.

  bedtime   an early start tomorrow → when to be asleep (7.5 h + 14 min) and an offer to set a wind-down reminder
  busy day  four or more timed items tomorrow → how full the day is and the free windows
  water     habit logged recently but little water today by the evening
  budget    spending pace projects the month over the budget
  streak    a habit streak of 5+ days that is about to break tonight
"""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from typing import Any

if __package__:
    from . import approval_skills, plan_skills
else:
    import approval_skills
    import plan_skills

EARLY = 9 * 60
SLEEP_MINUTES = 450 + 14
PREP_MINUTES = 60


def _hm(m: int) -> str:
    m %= 24 * 60
    return f"{m // 60:02d}:{m % 60:02d}"


async def _seen(pool: Any, user_id: str, key: str) -> bool:
    return bool(await pool.fetchval("SELECT 1 FROM owner_notifications WHERE user_id=$1 AND dedupe_key=$2 LIMIT 1", user_id, key))


async def bedtime(pool, user_id, prefs, now: datetime) -> list[dict]:
    if not prefs.get("smart_nudges") or not 20 <= now.hour < 23:
        return []
    tomorrow = now.date() + timedelta(days=1)
    key = f"nudge:bed:{tomorrow}"
    if await _seen(pool, user_id, key):
        return []
    busy, _ = await plan_skills.busy_intervals(pool, user_id, tomorrow)
    if not busy:
        return []
    first = min(s for s, _ in busy)
    if first >= EARLY:
        return []
    wake = first - PREP_MINUTES
    bed = wake - SLEEP_MINUTES + 24 * 60               # minutes since TODAY's midnight (tomorrow's times are offset by a day)
    now_min = now.hour * 60 + now.minute
    body = f"Yarın ilk etkinliğin {_hm(first)}. Hazırlanmak için {_hm(wake)}'da kalkarsan, yaklaşık {_hm(bed)}'da uyumuş olman iyi olur (7,5 saat uyku)."
    wind_down = bed - 30
    if wind_down > now_min:
        pid, _ = await approval_skills.propose(pool, user_id, f"bugün {_hm(wind_down)} yatmaya hazırlanmayı hatırlat", "agent")
        if pid is not None:
            body += f" {_hm(wind_down)} için hatırlatıcı kurmamı istersen “onayla {pid}” de."
    else:
        body += " Vakit az; şimdiden hazırlanmaya başlamak iyi olabilir."
    return [{"key": key, "title": "Yarın erken başlıyorsun", "body": body[:400]}]


async def busy_day(pool, user_id, prefs, now: datetime) -> list[dict]:
    if not prefs.get("smart_nudges") or not 18 <= now.hour < 22:
        return []
    tomorrow = now.date() + timedelta(days=1)
    key = f"nudge:busy:{tomorrow}"
    if await _seen(pool, user_id, key):
        return []
    busy, _ = await plan_skills.busy_intervals(pool, user_id, tomorrow)
    if len(busy) < 4:
        return []
    minutes = sum(e - s for s, e in busy)
    slots = plan_skills.free_slots(busy, 9 * 60, 20 * 60, 45)[:3]
    free = ", ".join(f"{_hm(a)}–{_hm(b)}" for a, b in slots) or "yok"
    return [{"key": key, "title": "Yarın yoğun bir gün", "body": f"Yarın {len(busy)} zamanlı kaydın var (yaklaşık {minutes // 60} sa {minutes % 60} dk dolu). Boş pencereler: {free}."}]


async def water(pool, user_id, prefs, now: datetime) -> list[dict]:
    if not prefs.get("smart_nudges") or not 17 <= now.hour < 21:
        return []
    key = f"nudge:water:{now.date()}"
    if await _seen(pool, user_id, key):
        return []
    recent = await pool.fetchval("SELECT COUNT(DISTINCT day) FROM owner_habits WHERE user_id=$1 AND habit='water' AND day>=$2 AND day<$3", user_id, now.date() - timedelta(days=7), now.date())
    if int(recent or 0) < 2:
        return []                                                     # only for people who actually track water
    today = float(await pool.fetchval("SELECT COALESCE(SUM(amount),0) FROM owner_habits WHERE user_id=$1 AND habit='water' AND day=$2", user_id, now.date()))
    if today >= 4:
        return []
    return [{"key": key, "title": "Su içmeyi unutma", "body": f"Bugün şu ana kadar {int(today)} bardak su kaydettin; hedef 8. Bir bardakla başlayabilirsin."}]


async def budget_pace(pool, user_id, prefs, now: datetime) -> list[dict]:
    if not prefs.get("smart_nudges") or not 9 <= now.hour < 22 or now.day < 7:
        return []
    iso = now.isocalendar()
    key = f"nudge:budget:{iso[0]}-W{iso[1]}"
    if await _seen(pool, user_id, key):
        return []
    raw = await pool.fetchval("SELECT prefs->'budget'->>'monthly' FROM owner_prefs WHERE user_id=$1", user_id)
    if not raw:
        return []
    budget = float(raw)
    spent = float(await pool.fetchval("SELECT COALESCE(SUM(amount),0) FROM owner_expenses WHERE user_id=$1 AND spent_on BETWEEN $2 AND $3", user_id, now.date().replace(day=1), now.date()))
    days = calendar.monthrange(now.year, now.month)[1]
    projected = spent / now.day * days
    if projected <= budget * 1.1 or spent >= budget:                 # already-over is reported by the expense replies themselves
        return []
    return [{"key": key, "title": "Bütçe temposu", "body": f"Bu hızla ay sonunda yaklaşık {round(projected):,} ₺ harcayacaksın; bütçen {round(budget):,} ₺. Şimdiye kadar {round(spent):,} ₺ harcadın.".replace(",", ".")}]


async def streak_risk(pool, user_id, prefs, now: datetime) -> list[dict]:
    if not prefs.get("smart_nudges") or not 20 <= now.hour < 23:
        return []
    out = []
    names = {"water": "su", "sleep": "uyku", "exercise": "spor"}
    for habit, label in names.items():
        key = f"nudge:streak:{habit}:{now.date()}"
        if await _seen(pool, user_id, key):
            continue
        days = {r["day"] for r in await pool.fetch("SELECT DISTINCT day FROM owner_habits WHERE user_id=$1 AND habit=$2 AND day>=$3", user_id, habit, now.date() - timedelta(days=60))}
        if now.date() in days:
            continue
        run, cursor = 0, now.date() - timedelta(days=1)
        while cursor in days:
            run += 1
            cursor -= timedelta(days=1)
        if run >= 5:
            out.append({"key": key, "title": "Serin bozulmasın", "body": f"{label.capitalize()} serin {run} gün oldu; bugün henüz kayıt yok. Bir kayıtla serini sürdürebilirsin."})
    return out


async def evaluate(pool, user_id, prefs, local_now: datetime) -> list[dict]:
    items: list[dict] = []
    for rule in (bedtime, busy_day, water, budget_pace, streak_risk):
        try:
            items += await rule(pool, user_id, prefs, local_now)
        except Exception:
            continue                                                # a broken rule never blocks the others
    return items
