"""Proactive GÖLGE: speaks up before being asked.

Rules (all owner-scoped, de-duplicated, respect quiet hours):
  • an event/plan starts in ~10 minutes
  • rain is likely in the next 3 hours (once a day)
  • optional morning briefing
Results are stored as owner notifications. An open page shows them within seconds;
if nobody picked one up after a short grace, a Web Push goes to the phone. Explicit
reminders you set yourself are pushed even in quiet hours.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from aiohttp import web

if __package__:
    from .text_normalization import fold_turkish
    from . import calendar_feed, instant_skills, web_push, alert_skills
else:
    from text_normalization import fold_turkish
    import calendar_feed
    import instant_skills
    import web_push
    import alert_skills

HOME_TZ = ZoneInfo("Europe/Istanbul")
GRACE_SECONDS = 25
TICK_SECONDS = 30
DEFAULT_PREFS = {"proactive": True, "morning_brief": False, "morning_time": "08:00", "evening_preview": False, "weekly_review": False,
                 "quiet_start": "23:00", "quiet_end": "07:00"}
_HHMM = re.compile(r"(?:[01]?\d|2[0-3])[:.]?[0-5]?\d?\Z")


def reminders_mod():
    if __package__:
        from . import reminders
    else:
        import reminders
    return reminders


def _minutes(value: str) -> int:
    value = str(value).replace(".", ":")
    h, _, m = value.partition(":")
    return int(h) * 60 + int(m or 0)


def in_quiet_hours(prefs: dict, local_now: datetime) -> bool:
    start, end = _minutes(prefs["quiet_start"]), _minutes(prefs["quiet_end"])
    if start == end:
        return False
    now = local_now.hour * 60 + local_now.minute
    return (start <= now < end) if start < end else (now >= start or now < end)


async def get_prefs(pool: Any, user_id: str) -> dict:
    raw = await pool.fetchval("SELECT prefs FROM owner_prefs WHERE user_id=$1", user_id)
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = {}
    prefs = dict(DEFAULT_PREFS)
    prefs.update({k: v for k, v in (raw or {}).items() if k in DEFAULT_PREFS})
    return prefs


async def set_pref(pool: Any, user_id: str, **changes) -> dict:
    # jsonb merge of only the changed keys: concurrent updates to other keys (style, budget, …) are never overwritten.
    await pool.execute(
        "INSERT INTO owner_prefs(user_id,prefs) VALUES($1,$2::jsonb) "
        "ON CONFLICT(user_id) DO UPDATE SET prefs=COALESCE(owner_prefs.prefs,'{}'::jsonb)||EXCLUDED.prefs,updated_at=NOW()",
        user_id, json.dumps(changes))
    return await get_prefs(pool, user_id)


async def get_extra(pool: Any, user_id: str, key: str, default: Any = None) -> Any:
    raw = await pool.fetchval("SELECT prefs FROM owner_prefs WHERE user_id=$1", user_id)
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = {}
    return (raw or {}).get(key, default)


async def set_extra(pool: Any, user_id: str, key: str, value: Any) -> None:
    """Store one module-owned key in owner_prefs without touching the others."""
    await pool.execute(
        "INSERT INTO owner_prefs(user_id,prefs) VALUES($1,jsonb_build_object($2::text,$3::jsonb)) "
        "ON CONFLICT(user_id) DO UPDATE SET prefs=COALESCE(owner_prefs.prefs,'{}'::jsonb)||jsonb_build_object($2::text,$3::jsonb),updated_at=NOW()",
        user_id, key, json.dumps(value))


# ── rules ───────────────────────────────────────────────────────────────────

async def upcoming_events(pool: Any, user_id: str, local_now: datetime) -> list[dict]:
    lo, hi = local_now + timedelta(minutes=8), local_now + timedelta(minutes=16)
    out = []
    rows = await pool.fetch(
        "SELECT id,title,scheduled_date,scheduled_time FROM owner_plans WHERE user_id=$1 AND is_done=FALSE "
        "AND scheduled_date=$2 AND scheduled_time IS NOT NULL", user_id, local_now.date())
    for r in rows:
        start = datetime.combine(r["scheduled_date"], r["scheduled_time"], tzinfo=HOME_TZ)
        if lo <= start <= hi:
            out.append({"key": f"plan:{r['id']}:{r['scheduled_date']}", "title": "Yaklaşan plan",
                        "body": f"{start:%H:%M} — {str(r['title'])[:100]} (yaklaşık 10 dk sonra)"})
    try:
        events = await calendar_feed.events_between(pool, user_id, local_now.date(), local_now.date())
    except Exception:
        events = None
    for e in events or []:
        if e["all_day"]:
            continue
        start = datetime.fromisoformat(e["start"])
        if lo <= start <= hi:
            digest = hashlib.sha1((e["start"] + e["title"]).encode()).hexdigest()[:10]
            place = f" • {e['location']}" if e.get("location") else ""
            out.append({"key": f"cal:{digest}", "title": "Yaklaşan etkinlik",
                        "body": f"{start:%H:%M} — {e['title'][:100]}{place} (yaklaşık 10 dk sonra)"})
    return out


async def weather_alerts(fetch_json, local_now: datetime) -> list[dict]:
    """Rain (≥60 %), thunderstorm, strong gusts, extreme heat/cold within the next 3 hours; once per day per kind."""
    if not (7 <= local_now.hour < 21):
        return []
    name, lat, lon = instant_skills.home_location()
    try:
        data = await fetch_json(
            f"https://api.open-meteo.com/v1/forecast?latitude={round(lat, 2)}&longitude={round(lon, 2)}"
            "&hourly=precipitation_probability,temperature_2m,weather_code,wind_gusts_10m&timezone=Europe%2FIstanbul&forecast_days=2",
            f"proactive-weather:{round(lat, 2)}:{round(lon, 2)}", 900)
        hourly = data["hourly"]
        times = hourly["time"]
    except Exception:
        return []

    def series(key: str) -> list:
        values = hourly.get(key)
        return values if isinstance(values, list) else [None] * len(times)

    probs, temps, codes, gusts = (series("precipitation_probability"), series("temperature_2m"), series("weather_code"), series("wind_gusts_10m"))
    horizon = local_now + timedelta(hours=3)
    rain = temp_hi = 0
    temp_lo = 99
    storm = False
    gust = 0.0
    for i, t in enumerate(times):
        try:
            at = datetime.fromisoformat(t).replace(tzinfo=HOME_TZ)
        except ValueError:
            continue
        if not (local_now - timedelta(minutes=30) <= at <= horizon):
            continue
        num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
        rain = max(rain, int(probs[i])) if num(probs[i]) else rain
        if num(temps[i]):
            temp_hi, temp_lo = max(temp_hi, temps[i]), min(temp_lo, temps[i])
        storm = storm or (num(codes[i]) and codes[i] >= 95)
        gust = max(gust, float(gusts[i])) if num(gusts[i]) else gust
    day = local_now.date()
    out = []
    if rain >= 60:
        out.append({"key": f"rain:{day}", "title": "Yağmur bekleniyor",
                    "body": f"{name} için önümüzdeki 3 saatte yağış olasılığı %{rain}. Şemsiyeni unutma."})
    if storm:
        out.append({"key": f"storm:{day}", "title": "Gök gürültülü fırtına", "body": f"{name} için önümüzdeki 3 saatte gök gürültülü fırtına bekleniyor. Açık havadan ve ağaç altından uzak dur."})
    if gust >= 60:
        out.append({"key": f"wind:{day}", "title": "Kuvvetli rüzgâr", "body": f"{name} için önümüzdeki 3 saatte rüzgâr hamleleri {round(gust)} km/sa'ya çıkabilir. Dışarıdaki eşyaları sabitle."})
    if temp_hi >= 37:
        out.append({"key": f"heat:{day}", "title": "Aşırı sıcak", "body": f"{name} için sıcaklık {round(temp_hi)}°C'ye çıkacak. Bol su iç, öğle güneşinden kaçın."})
    if temp_lo <= -3:
        out.append({"key": f"cold:{day}", "title": "Dondurucu soğuk", "body": f"{name} için sıcaklık {round(temp_lo)}°C'ye düşecek. Sıkı giyin, buzlanmaya dikkat et."})
    return out


rain_alert = weather_alerts   # name used by earlier tests and callers


async def morning_brief(pool, user_id, prefs, fetch_json, fetch_text, local_now: datetime) -> list[dict]:
    if not prefs.get("morning_brief"):
        return []
    start = _minutes(prefs["morning_time"])
    now = local_now.hour * 60 + local_now.minute
    if not (start <= now < start + 120):
        return []
    text = await instant_skills.answer_briefing("günlük brifing", pool, user_id, fetch_json, local_now, fetch_text)
    if not text:
        return []
    body = ""
    for line in text.splitlines():
        if len(body) + len(line) + 1 > 380:
            break
        body += line + "\n"
    return [{"key": f"brief:{local_now.date()}", "title": "Günaydın — günün özeti", "body": body.strip()[:400]}]


async def quake_alert(fetch_json, now: datetime) -> list[dict]:
    """M5.0+ in/near Türkiye within the last hour. Urgent: ignores quiet hours."""
    try:
        data = await fetch_json(
            "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minmagnitude=5&orderby=time&limit=3"
            "&minlatitude=34&maxlatitude=43&minlongitude=25&maxlongitude=46", "proactive-quake", 120)
        feats = data["features"]
    except Exception:
        return []
    out = []
    for ft in feats:
        p = ft["properties"]
        at = datetime.fromtimestamp(p["time"] / 1000, timezone.utc)
        if now - at <= timedelta(hours=1):
            out.append({"key": f"quake:{ft.get('id') or p['time']}", "urgent": True, "title": f"Deprem: M{p['mag']:.1f}",
                        "body": f"{str(p.get('place') or '?')[:80]} — {at.astimezone(HOME_TZ):%H:%M}. Resmî bilgi için AFAD/Kandilli'yi kontrol et. (USGS)"})
    return out


async def evening_preview(pool, user_id, prefs, local_now: datetime) -> list[dict]:
    if not prefs.get("evening_preview") or not (21 * 60 <= local_now.hour * 60 + local_now.minute < 23 * 60):
        return []
    tomorrow = local_now.date() + timedelta(days=1)
    lines, _ = await instant_skills.agenda_lines(pool, user_id, tomorrow, tomorrow)
    if not lines:
        return [{"key": f"evening:{tomorrow}", "title": "Yarın için", "body": "Yarın için kayıtlı etkinlik ya da plan görünmüyor. İyi geceler!"}]
    body = f"Yarın {len(lines)} kayıt var. İlk: {lines[0]}"
    return [{"key": f"evening:{tomorrow}", "title": "Yarına hazırlık", "body": body[:400]}]


async def weekly_review(pool, user_id, prefs, local_now: datetime) -> list[dict]:
    if not prefs.get("weekly_review") or local_now.weekday() != 6 or not (19 * 60 <= local_now.hour * 60 + local_now.minute < 22 * 60):
        return []
    if __package__:
        from . import weekly_skills
    else:
        import weekly_skills
    body = await weekly_skills.handle("bu haftanin ozeti", pool, user_id, local_now)
    if not body or "kayıtlı bir veri yok" in body:
        return []
    # The notification can show on a lock screen: no amounts or entries, only a pointer to the in-app review.
    return [{"key": f"weekly:{local_now.date()}", "title": "Haftalık özet hazır",
             "body": "Haftanın planları, alışkanlıkları ve harcamaların hazır. Görmek için GÖLGE’de “haftalık özet” yaz."}]


async def evaluate(pool: Any, user_id: str, now: datetime, fetch_json, fetch_text=None) -> list[dict]:
    local_now = now.astimezone(HOME_TZ)
    prefs = await get_prefs(pool, user_id)
    if not prefs["proactive"]:
        return []
    quiet = in_quiet_hours(prefs, local_now)
    items: list[dict] = []
    for rule in (upcoming_events(pool, user_id, local_now), weather_alerts(fetch_json, local_now),
                 morning_brief(pool, user_id, prefs, fetch_json, fetch_text, local_now),
                 evening_preview(pool, user_id, prefs, local_now), weekly_review(pool, user_id, prefs, local_now),
                 quake_alert(fetch_json, now)):
        try:
            items += await rule
        except Exception:
            continue  # one broken rule must not silence the others
    return [i for i in items if i.get("urgent") or not quiet]


async def store(pool: Any, user_id: str, items: list[dict]) -> int:
    n = 0
    for item in items:
        got = await pool.fetchval(
            "INSERT INTO owner_notifications(user_id,dedupe_key,title,body) VALUES($1,$2,$3,$4) "
            "ON CONFLICT(user_id,dedupe_key) DO NOTHING RETURNING id",
            user_id, item["key"], item["title"][:120], item["body"][:400])
        n += 1 if got else 0
    return n


# ── dispatcher ──────────────────────────────────────────────────────────────

async def tick(pool: Any, fetch_json, fetch_text=None, now: datetime | None = None, sender=None) -> dict:
    """One dispatcher pass. `sender(pool, user_id, message, **kw)` defaults to Web Push."""
    now = now or datetime.now(timezone.utc)
    sender = sender or web_push.push_to_user
    stats = {"stored": 0, "pushed": 0}
    users = [r["user_id"] for r in await pool.fetch(
        "SELECT user_id FROM push_subscriptions UNION SELECT user_id FROM device_presence "
        "WHERE last_seen > NOW() - INTERVAL '7 days' UNION SELECT user_id FROM owner_prefs")]
    for user_id in users:
        stats["stored"] += await store(pool, user_id, await evaluate(pool, user_id, now, fetch_json, fetch_text))
    try:
        for user_id, note in await alert_skills.check_all(pool, fetch_json):
            stats["stored"] += await store(pool, user_id, [note])
    except Exception:
        pass
    # explicit reminders nobody picked up in-app → push (not blocked by quiet hours)
    rows = await pool.fetch(
        "UPDATE owner_reminders SET status='delivered',delivered_at=NOW() WHERE id IN ("
        " SELECT r.id FROM owner_reminders r WHERE r.status='pending' AND r.due_at <= NOW() - make_interval(secs=>$1)"
        " AND EXISTS (SELECT 1 FROM push_subscriptions s WHERE s.user_id=r.user_id)"
        " ORDER BY r.due_at LIMIT 20 FOR UPDATE SKIP LOCKED) RETURNING user_id,text,due_at,repeat_rule", float(GRACE_SECONDS))
    await (reminders_mod().reschedule_repeats(pool, rows, now))
    for r in rows:
        stats["pushed"] += await sender(pool, r["user_id"], {"title": "⏰ Hatırlatıcı", "body": r["text"], "tag": "golge-reminder"},
                                        urgency="high", ttl=3600)
    notes = await pool.fetch(
        "UPDATE owner_notifications SET pushed_at=NOW() WHERE id IN ("
        " SELECT n.id FROM owner_notifications n WHERE n.pushed_at IS NULL AND n.inapp_at IS NULL"
        " AND n.created_at <= NOW() - make_interval(secs=>$1) ORDER BY n.id LIMIT 20 FOR UPDATE SKIP LOCKED)"
        " RETURNING user_id,title,body", float(GRACE_SECONDS))
    for n in notes:
        stats["pushed"] += await sender(pool, n["user_id"], {"title": n["title"], "body": n["body"], "tag": "golge-proactive"}, ttl=1800)
    await pool.execute("DELETE FROM owner_notifications WHERE created_at < NOW() - INTERVAL '3 days'")
    return stats


async def dispatcher_loop(app: web.Application, fetch_json, fetch_text=None) -> None:
    import time as _time
    if __package__:
        from . import ops
    else:
        import ops
    pool = app["db"]
    status = app.setdefault("dispatcher_status", {"ticks": 0, "errors": 0, "last_tick_at": None, "last_stats": {}, "last_maintenance": {}})
    last_maintenance = 0.0
    while True:
        try:
            async with pool.acquire() as conn:
                if await conn.fetchval("SELECT pg_try_advisory_lock(7243001)"):
                    try:
                        status["last_stats"] = await tick(pool, fetch_json, fetch_text)
                        status["ticks"] += 1
                        status["last_tick_at"] = _time.time()
                        if _time.time() - last_maintenance > 3600:
                            status["last_maintenance"] = await ops.maintenance(pool)
                            last_maintenance = _time.time()
                    finally:
                        await conn.execute("SELECT pg_advisory_unlock(7243001)")
                else:
                    status["last_tick_at"] = _time.time()   # another instance owns the lock; we are healthy
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            status["errors"] += 1
            print(f"[proactive] tick failed: {type(exc).__name__}", flush=True)
        await asyncio.sleep(TICK_SECONDS)


async def due_notifications(pool: Any, user_id: str) -> list[dict]:
    rows = await pool.fetch(
        "UPDATE owner_notifications SET inapp_at=NOW() WHERE id IN ("
        " SELECT id FROM owner_notifications WHERE user_id=$1 AND inapp_at IS NULL ORDER BY id LIMIT 5 FOR UPDATE SKIP LOCKED)"
        " RETURNING id,title,body", user_id)
    return [dict(r) for r in rows]


# ── chat: preferences ───────────────────────────────────────────────────────

_ON = r"(?:ac|acik|ac\w*|ekle|baslat)"
_OFF = r"(?:kapat|kapa\w*|iptal|durdur|devre disi)"


async def handle_prefs(text: str, pool: Any, user_id: str) -> str | None:
    f = fold_turkish(text)
    if len(f) > 120:
        return None
    if re.search(r"\bbildirim ayarlarim\b|\bproaktif ayarlar\w*\b|\bsessiz saatlerim\b", f):
        p = await get_prefs(pool, user_id)
        n = await pool.fetchval("SELECT COUNT(*) FROM push_subscriptions WHERE user_id=$1", user_id)
        return ("Bildirim ayarların:\n"
                f"• Proaktif uyarılar: {'açık' if p['proactive'] else 'kapalı'}\n"
                f"• Sabah brifingi bildirimi: {'açık, ' + p['morning_time'] if p['morning_brief'] else 'kapalı'}\n"
                f"• Akşam özeti bildirimi: {'açık' if p['evening_preview'] else 'kapalı'}\n"
                f"• Haftalık özet bildirimi: {'açık (pazar akşamı)' if p['weekly_review'] else 'kapalı'}\n"
                f"• Sessiz saatler: {p['quiet_start']} – {p['quiet_end']}\n"
                f"• Bildirim alan cihaz: {int(n or 0)}" + ("" if n else " (Hafıza → Bildirimleri aç düğmesi)"))
    m = re.search(r"\bsessiz saat\w*\b.*?\b([01]?\d|2[0-3])(?:[:.]([0-5]\d))?\s*(?:ile|-|–|den|'?dan|ve)\s*([01]?\d|2[0-3])(?:[:.]([0-5]\d))?\b", f)
    if m:
        s, e = f"{int(m.group(1)):02d}:{m.group(2) or '00'}", f"{int(m.group(3)):02d}:{m.group(4) or '00'}"
        await set_pref(pool, user_id, quiet_start=s, quiet_end=e)
        return f"Tamam, sessiz saatler {s} – {e}. Bu aralıkta yalnızca senin kurduğun hatırlatıcılar gelir."
    if re.search(r"\bsessiz saat\w*\b", f) and re.search(_OFF, f):
        await set_pref(pool, user_id, quiet_start="00:00", quiet_end="00:00")
        return "Sessiz saatleri kapattım; proaktif uyarılar gece de gelebilir."
    if re.search(r"\bsabah (?:brifing\w*|ozet\w*)\b.*\bbildirim\w*\b|\bbildirim\w*\b.*\bsabah (?:brifing\w*|ozet\w*)\b", f):
        if re.search(_OFF, f):
            await set_pref(pool, user_id, morning_brief=False)
            return "Sabah brifingi bildirimini kapattım."
        t = re.search(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", f)
        when = f"{int(t.group(1)):02d}:{t.group(2)}" if t else "08:00"
        await set_pref(pool, user_id, morning_brief=True, morning_time=when)
        return f"Tamam, her sabah {when} civarında günün özetini bildirim olarak göndereceğim."
    if re.search(r"\bak[sş]am (?:ozet\w*|hazirlik\w*)\b.*\bbildirim\w*\b|\bbildirim\w*\b.*\bak[sş]am (?:ozet\w*|hazirlik\w*)\b", f) or \
            re.search(r"\baksam (?:ozet\w*|hazirlik\w*)\b.*\bbildirim", f):
        off = bool(re.search(_OFF, f))
        await set_pref(pool, user_id, evening_preview=not off)
        return "Akşam özeti bildirimini kapattım." if off else "Tamam, her akşam 21:00 sonrası yarının planlarını bildirim olarak göndereceğim."
    if re.search(r"\bhaftalik (?:ozet\w*|rapor\w*)\b.*\bbildirim\w*\b|\bbildirim\w*\b.*\bhaftalik (?:ozet\w*|rapor\w*)\b", f):
        if re.search(r"\?|\bm[iuü]\b|\bnasil\b|\bnedir\b", f):          # a question reports the setting, it never changes it
            p = await get_prefs(pool, user_id)
            return "Haftalık özet bildirimi şu an " + ("açık (pazar akşamı)." if p["weekly_review"] else "kapalı. Açmak için “haftalık özet bildirimi aç” de.")
        off = bool(re.search(_OFF, f))
        await set_pref(pool, user_id, weekly_review=not off)
        return "Haftalık özet bildirimini kapattım." if off else "Tamam, her pazar akşamı (19:00 sonrası) haftanın özetini bildirim olarak göndereceğim; o hafta kayıt yoksa göndermem."
    if re.search(r"\bproaktif\b|\bkendiliginden uyar\w*\b|\buyari\w* (?:ac|kapat)", f) and (re.search(_OFF, f) or re.search(_ON, f)):
        off = bool(re.search(_OFF, f))
        await set_pref(pool, user_id, proactive=not off)
        return ("Proaktif uyarıları kapattım; yalnızca kurduğun hatırlatıcılar gelecek." if off else
                "Proaktif uyarılar açık: yaklaşan etkinlikleri ve yağmuru önceden haber vereceğim.")
    return None
