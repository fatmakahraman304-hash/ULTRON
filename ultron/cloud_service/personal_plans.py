"""Owner-created schedule entries, not a Google/Apple Calendar integration.

Only authenticated browser sessions may write. Every SQL operation is scoped
to the signed-in user, no calendar notifications are scheduled, and imported
or inferred entries are never inserted without the owner's explicit action.
"""
from __future__ import annotations

import re
from datetime import date, time
from aiohttp import web

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_TIME = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d\Z")


def validate_plan(body: object) -> tuple[str, date, time | None, str]:
    if not isinstance(body, dict):
        raise ValueError("invalid_payload")
    title = body.get("title")
    when = body.get("date")
    clock = body.get("time", "")
    note = body.get("note", "")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 140 or "\x00" in title:
        raise ValueError("title_length_1_to_140")
    if not isinstance(when, str) or not _DATE.fullmatch(when):
        raise ValueError("date_must_be_yyyy_mm_dd")
    try:
        scheduled_date = date.fromisoformat(when)
    except ValueError as exc:
        raise ValueError("invalid_calendar_date") from exc
    if clock is None:
        clock = ""
    if not isinstance(clock, str) or (clock and not _TIME.fullmatch(clock)):
        raise ValueError("time_must_be_hh_mm")
    if not isinstance(note, str) or len(note) > 500 or "\x00" in note:
        raise ValueError("note_too_long")
    return title.strip(), scheduled_date, time.fromisoformat(clock) if clock else None, note.strip()


def plan_dict(row) -> dict:
    d = dict(row)
    for key in ("scheduled_date", "scheduled_time"):
        value = d.get(key)
        d[key] = value.isoformat(timespec="minutes") if key == "scheduled_time" and value else (
            value.isoformat() if value else None
        )
    d["source"] = "owner_created_plan"
    return d


def _require_browser(request):
    if request.get("auth_kind") != "web":
        raise web.HTTPForbidden(text='{"error":"browser_session_required"}', content_type="application/json")
    if request.method in ("POST", "PATCH", "DELETE"):
        if request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            raise web.HTTPForbidden(text='{"error":"cross_origin_denied"}', content_type="application/json")
        if request.method in ("POST", "PATCH") and request.content_type != "application/json":
            raise web.HTTPUnsupportedMediaType(text='{"error":"json_required"}', content_type="application/json")


def _plan_id(request):
    try:
        raw = request.match_info["id"]
        if not re.fullmatch(r"[1-9]\d{0,17}", raw):
            raise ValueError()
        return int(raw)
    except (ValueError, KeyError, TypeError):
        raise web.HTTPBadRequest(text='{"error":"invalid_id"}', content_type="application/json")


async def list_plans(request):
    _require_browser(request)
    rows = await request.app["db"].fetch(
        "SELECT id,title,scheduled_date,scheduled_time,note,is_done "
        "FROM owner_plans WHERE user_id=$1 "
        "ORDER BY scheduled_date ASC, scheduled_time ASC NULLS LAST, id ASC LIMIT 100",
        request["user_id"],
    )
    return web.json_response({"plans": [plan_dict(row) for row in rows], "external_calendar_connected": False,
                              "notifications_enabled": False})


async def create_plan(request):
    _require_browser(request)
    try:
        body = await request.json()
        title, day, clock, note = validate_plan(body)
    except (ValueError, TypeError):
        return web.json_response({"error": "invalid_plan_fields"}, status=400)
    row = await request.app["db"].fetchrow(
        "INSERT INTO owner_plans(user_id,title,scheduled_date,scheduled_time,note) "
        "VALUES($1,$2,$3,$4,$5) "
        "RETURNING id,title,scheduled_date,scheduled_time,note,is_done",
        request["user_id"], title, day, clock, note,
    )
    return web.json_response({"plan": plan_dict(row), "notification_sent": False}, status=201)


async def update_plan(request):
    """Only the signed-in browser owner may edit an existing plan.

    The full validated replacement is atomic and retains its existing id
    and completion state. Provider calendar / notification writes never occur.
    """
    _require_browser(request)
    pid = _plan_id(request)
    try:
        title, day, clock, note = validate_plan(await request.json())
    except (ValueError, TypeError):
        return web.json_response({"error": "invalid_plan_fields"}, status=400)
    row = await request.app["db"].fetchrow(
        "UPDATE owner_plans SET title=$3,scheduled_date=$4,scheduled_time=$5,"
        "note=$6,updated_at=NOW() WHERE id=$1 AND user_id=$2 "
        "RETURNING id,title,scheduled_date,scheduled_time,note,is_done",
        pid, request["user_id"], title, day, clock, note,
    )
    if row is None:
        raise web.HTTPNotFound(text='{"error":"not_found"}', content_type="application/json")
    return web.json_response({"plan": plan_dict(row), "notification_sent": False})


async def set_plan_done(request):
    _require_browser(request)
    pid = _plan_id(request)
    try:
        body = await request.json()
    except (ValueError, TypeError):
        return web.json_response({"error": "invalid_json"}, status=400)
    if not isinstance(body, dict) or type(body.get("is_done")) is not bool:
        return web.json_response({"error": "is_done_boolean_required"}, status=400)
    row = await request.app["db"].fetchrow(
        "UPDATE owner_plans SET is_done=$3,updated_at=NOW() "
        "WHERE id=$1 AND user_id=$2 "
        "RETURNING id,title,scheduled_date,scheduled_time,note,is_done",
        pid, request["user_id"], body["is_done"],
    )
    if row is None:
        raise web.HTTPNotFound(text='{"error":"not_found"}', content_type="application/json")
    return web.json_response({"plan": plan_dict(row)})


async def delete_plan(request):
    _require_browser(request)
    pid = _plan_id(request)
    row = await request.app["db"].fetchrow(
        "DELETE FROM owner_plans WHERE id=$1 AND user_id=$2 RETURNING id",
        pid, request["user_id"],
    )
    if row is None:
        raise web.HTTPNotFound(text='{"error":"not_found"}', content_type="application/json")
    return web.json_response({"deleted": True, "id": pid})


def register_routes(app):
    app.router.add_get("/api/owner-plans", list_plans)
    app.router.add_post("/api/owner-plans", create_plan)
    app.router.add_put("/api/owner-plans/{id}", update_plan)
    app.router.add_patch("/api/owner-plans/{id}", set_plan_done)
    app.router.add_delete("/api/owner-plans/{id}", delete_plan)
