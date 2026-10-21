"""Operations: deep health, owner diagnostics, retention maintenance and data export."""
from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Any

from aiohttp import web

STARTED = time.time()


def _iso(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


async def deep_health(app: web.Application) -> dict:
    pool = app["db"]
    checks: dict[str, Any] = {}
    try:
        checks["database"] = bool(await asyncio.wait_for(pool.fetchval("SELECT 1"), 3))
    except Exception:
        checks["database"] = False
    task = app.get("proactive_task")
    checks["dispatcher_running"] = bool(task is not None and not task.done())
    status = app.get("dispatcher_status") or {}
    last = status.get("last_tick_at")
    checks["dispatcher_recent"] = bool(last and time.time() - last < 180)
    return {"ok": all(checks.values()), "checks": checks, "uptime_seconds": int(time.time() - STARTED)}


async def diagnostics(app: web.Application, user_id: str) -> dict:
    pool = app["db"]

    async def count(sql: str, *args) -> int:
        try:
            return int(await pool.fetchval(sql, *args) or 0)
        except Exception:
            return -1

    status = dict(app.get("dispatcher_status") or {})
    if status.get("last_tick_at"):
        status["last_tick_age_seconds"] = int(time.time() - status["last_tick_at"])
    presence = await pool.fetchrow("SELECT last_seen FROM device_presence WHERE user_id=$1 AND device='desktop'", user_id)
    return {
        "version": {"commit": os.getenv("RENDER_GIT_COMMIT", "")[:12], "branch": os.getenv("RENDER_GIT_BRANCH", "")},
        "uptime_seconds": int(time.time() - STARTED),
        "dispatcher": status,
        "counts": {
            "push_devices": await count("SELECT COUNT(*) FROM push_subscriptions WHERE user_id=$1", user_id),
            "pending_reminders": await count("SELECT COUNT(*) FROM owner_reminders WHERE user_id=$1 AND status='pending'", user_id),
            "active_price_alerts": await count("SELECT COUNT(*) FROM owner_alerts WHERE user_id=$1 AND active", user_id),
            "unread_notifications": await count("SELECT COUNT(*) FROM owner_notifications WHERE user_id=$1 AND inapp_at IS NULL", user_id),
            "running_missions": await count("SELECT COUNT(*) FROM missions WHERE user_id=$1 AND status IN ('planning','running')", user_id),
            "open_plans": await count("SELECT COUNT(*) FROM owner_plans WHERE user_id=$1 AND is_done=FALSE", user_id),
            "memories": await count("SELECT COUNT(*) FROM memories WHERE user_id=$1", user_id),
        },
        "desktop_last_seen": _iso(presence["last_seen"]) if presence else None,
        "integrations": {
            "gemini": bool(os.getenv("GEMINI_API_KEY")),
            "home_assistant": bool(os.getenv("HOME_ASSISTANT_URL") and os.getenv("HOME_ASSISTANT_TOKEN")),
        },
    }


RETENTION = (
    ("owner_reminders", "DELETE FROM owner_reminders WHERE status IN ('delivered','cancelled') AND COALESCE(delivered_at, created_at) < NOW() - INTERVAL '30 days'"),
    ("missions", "DELETE FROM missions WHERE status IN ('done','failed','cancelled') AND updated_at < NOW() - INTERVAL '30 days'"),
    ("owner_notifications", "DELETE FROM owner_notifications WHERE created_at < NOW() - INTERVAL '3 days'"),
    ("owner_alerts", "DELETE FROM owner_alerts WHERE NOT active AND COALESCE(fired_at, created_at) < NOW() - INTERVAL '90 days'"),
    ("push_subscriptions", "DELETE FROM push_subscriptions WHERE last_ok IS NULL AND created_at < NOW() - INTERVAL '60 days'"),
    ("skill_usage", "DELETE FROM skill_usage WHERE day < CURRENT_DATE - 120"),
    ("skill_feedback", "DELETE FROM skill_feedback WHERE created_at < NOW() - INTERVAL '365 days'"),
    ("owner_plans", "DELETE FROM owner_plans WHERE is_done AND updated_at < NOW() - INTERVAL '365 days'"),
)


async def maintenance(pool: Any) -> dict[str, int]:
    """Retention sweep; each table is independent so one failure does not stop the rest."""
    removed: dict[str, int] = {}
    for name, sql in RETENTION:
        try:
            tag = await pool.execute(sql)
            removed[name] = int(str(tag).rsplit(" ", 1)[-1]) if tag else 0
        except Exception:
            removed[name] = -1
    return removed


async def export_owner_data(pool: Any, user_id: str) -> dict:
    async def rows(sql: str) -> list[dict]:
        return [{k: _iso(v) for k, v in dict(r).items()} for r in await pool.fetch(sql, user_id)]

    prefs = await pool.fetchval("SELECT prefs FROM owner_prefs WHERE user_id=$1", user_id)
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "memories": await rows("SELECT category,key,value,version,created_at,updated_at FROM memories WHERE user_id=$1 ORDER BY updated_at DESC"),
        "plans": await rows("SELECT title,scheduled_date,scheduled_time,note,is_done FROM owner_plans WHERE user_id=$1 ORDER BY scheduled_date"),
        "reminders": await rows("SELECT text,due_at,status,repeat_rule FROM owner_reminders WHERE user_id=$1 AND status='pending' ORDER BY due_at"),
        "lists": await rows("SELECT list_label AS list, item, created_at FROM owner_list_items WHERE user_id=$1 ORDER BY list_name, id"),
        "expenses": await rows("SELECT amount, category, note, spent_on FROM owner_expenses WHERE user_id=$1 ORDER BY spent_on DESC, id DESC LIMIT 1000"),
        "habits": await rows("SELECT habit, amount, note, day FROM owner_habits WHERE user_id=$1 ORDER BY day DESC, id DESC LIMIT 2000"),
        "skill_usage": await rows("SELECT day, skill, n FROM skill_usage WHERE user_id=$1 ORDER BY day DESC, skill LIMIT 2000"),
        "feedback": await rows("SELECT rating, skill, user_text, reply, created_at FROM skill_feedback WHERE user_id=$1 ORDER BY id DESC LIMIT 500"),
        "journal": await rows("SELECT day, entry FROM owner_journal WHERE user_id=$1 ORDER BY day DESC, id DESC LIMIT 2000"),
        "routines": await rows("SELECT name, steps FROM owner_routines WHERE user_id=$1 ORDER BY name"),
        "price_alerts": await rows("SELECT asset,vs,direction,threshold,active FROM owner_alerts WHERE user_id=$1 ORDER BY id"),
        "preferences": json.loads(prefs) if isinstance(prefs, str) else (prefs or {}),
        "missions": await rows("SELECT goal,status,report,created_at FROM missions WHERE user_id=$1 ORDER BY created_at DESC LIMIT 20"),
        "calendar_feed_connected": bool(await pool.fetchval("SELECT 1 FROM owner_calendar_feeds WHERE user_id=$1", user_id)),
        "push_devices": int(await pool.fetchval("SELECT COUNT(*) FROM push_subscriptions WHERE user_id=$1", user_id) or 0),
        "note": "Sohbet geçmişi, görseller ve gizli bağlantılar (iCal adresi, push anahtarları) bilerek dışarıda bırakıldı.",
    }


async def deep_health_route(request: web.Request) -> web.Response:
    result = await deep_health(request.app)
    return web.json_response(result, status=200 if result["ok"] else 503)


async def diagnostics_route(request: web.Request) -> web.Response:
    if request.get("auth_kind") not in ("web", "device"):
        raise web.HTTPForbidden()
    return web.json_response(await diagnostics(request.app, request["user_id"]), dumps=lambda v: json.dumps(v, default=str, ensure_ascii=False))


async def export_route(request: web.Request) -> web.Response:
    if request.get("auth_kind") != "web":
        raise web.HTTPForbidden(text='{"error":"browser_session_required"}', content_type="application/json")
    data = await export_owner_data(request.app["db"], request["user_id"])
    return web.Response(text=json.dumps(data, ensure_ascii=False, indent=2, default=str), content_type="application/json",
                        headers={"Content-Disposition": 'attachment; filename="golge-verilerim.json"'})


def register_routes(app: web.Application) -> None:
    app.router.add_get("/api/health/deep", deep_health_route)
    app.router.add_get("/api/diagnostics", diagnostics_route)
    app.router.add_get("/api/export", export_route)
