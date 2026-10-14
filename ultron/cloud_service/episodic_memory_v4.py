"""GÖLGE Episodic Memory V4: owner-confirmed, versioned event timeline.

No automatic capture, background observation, provider-created memories or
model-context injection. API access is limited to authenticated web sessions.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from aiohttp import web
from live_voice_policy import safe_manual_memory_value


def validate_episode(title: object, summary: object, happened_at: object,
                     *, now: datetime | None = None) -> tuple[str, str, datetime]:
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 160:
        raise ValueError("invalid_episode_title")
    if not isinstance(summary, str) or not 1 <= len(summary.strip()) <= 2000:
        raise ValueError("invalid_episode_summary")
    title, summary = title.strip(), summary.strip()
    if not safe_manual_memory_value(title + " " + summary):
        raise ValueError("sensitive_episode_rejected")
    if not isinstance(happened_at, str) or len(happened_at) > 48:
        raise ValueError("invalid_episode_time")
    try:
        parsed = datetime.fromisoformat(happened_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_episode_time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone_required")
    parsed = parsed.astimezone(timezone.utc)
    clock = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if parsed.year < 1900 or parsed > clock + timedelta(minutes=5):
        raise ValueError("episode_time_out_of_range")
    return title, summary, parsed


def public_episode(row) -> dict:
    """Return only owner-visible fields, never database credentials."""
    item = dict(row)
    for field in ("series_id", "happened_at", "created_at", "superseded_at"):
        value = item.get(field)
        if value is not None and not isinstance(value, (int, float, str)):
            item[field] = str(value.isoformat() if hasattr(value, "isoformat") else value)
    return item


async def create_episode(pool, user_id: str, device_id: str,
                         title: str, summary: str, happened_at: str) -> dict:
    title, summary, happened = validate_episode(title, summary, happened_at)
    row = await pool.fetchrow(
        """INSERT INTO episodic_memories
           (user_id,series_id,version,title,summary,happened_at,provenance,device_id)
           VALUES($1,$2,1,$3,$4,$5,'owner_confirmed',$6)
           RETURNING id,series_id,version,title,summary,happened_at,provenance,created_at""",
        user_id, uuid4(), title, summary, happened, device_id,
    )
    return public_episode(row)


async def list_episodes(pool, user_id: str, limit: int = 20) -> list[dict]:
    try:
        count = max(1, min(int(limit), 50))
    except (TypeError, ValueError):
        count = 20
    rows = await pool.fetch(
        """SELECT id,series_id,version,title,summary,happened_at,provenance,created_at
           FROM episodic_memories WHERE user_id=$1 AND superseded_at IS NULL
           ORDER BY happened_at DESC,id DESC LIMIT $2""", user_id, count,
    )
    return [public_episode(row) for row in rows]


async def correct_episode(pool, user_id: str, device_id: str, episode_id: int,
                          title: str, summary: str, happened_at: str) -> dict | None:
    title, summary, happened = validate_episode(title, summary, happened_at)
    async with pool.acquire() as conn:
        async with conn.transaction():
            old = await conn.fetchrow(
                """SELECT series_id,version FROM episodic_memories
                   WHERE id=$1 AND user_id=$2 AND superseded_at IS NULL FOR UPDATE""",
                episode_id, user_id,
            )
            if old is None:
                return None
            await conn.execute(
                """UPDATE episodic_memories SET superseded_at=NOW()
                   WHERE id=$1 AND user_id=$2 AND superseded_at IS NULL""",
                episode_id, user_id,
            )
            row = await conn.fetchrow(
                """INSERT INTO episodic_memories
                   (user_id,series_id,version,title,summary,happened_at,provenance,device_id)
                   VALUES($1,$2,$3,$4,$5,$6,'owner_confirmed',$7)
                   RETURNING id,series_id,version,title,summary,happened_at,provenance,created_at""",
                user_id, old["series_id"], old["version"] + 1,
                title, summary, happened, device_id,
            )
    return public_episode(row)


async def episode_history(pool, user_id: str, episode_id: int) -> list[dict]:
    rows = await pool.fetch(
        """SELECT id,series_id,version,title,summary,happened_at,provenance,
                  created_at,superseded_at FROM episodic_memories
           WHERE user_id=$1 AND series_id=(
               SELECT series_id FROM episodic_memories WHERE id=$2 AND user_id=$1)
           ORDER BY version DESC LIMIT 50""", user_id, episode_id,
    )
    return [public_episode(row) for row in rows]


async def delete_episode(pool, user_id: str, episode_id: int) -> bool:
    """Forget the entire correction chain, not just its latest version."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """SELECT series_id FROM episodic_memories
                   WHERE id=$1 AND user_id=$2 FOR UPDATE""",
                episode_id, user_id,
            )
            if row is None:
                return False
            await conn.execute(
                "DELETE FROM episodic_memories WHERE user_id=$1 AND series_id=$2",
                user_id, row["series_id"],
            )
    return True


def _web_only(request):
    if request.get("auth_kind") != "web":
        raise web.HTTPForbidden(
            text='{"error":"web_session_required"}',
            content_type="application/json",
        )


def _episode_id(request):
    try:
        number = int(request.match_info["id"])
        if number < 1 or number > 2**63 - 1:
            raise ValueError()
        return number
    except (TypeError, ValueError, KeyError):
        raise web.HTTPBadRequest(
            text='{"error":"invalid_episode_id"}', content_type="application/json",
        )


async def _confirmed_payload(request):
    try:
        body = await request.json()
    except (ValueError, TypeError):
        body = None
    if not isinstance(body, dict) or body.get("owner_confirmed") is not True:
        raise web.HTTPBadRequest(
            text='{"error":"explicit_owner_confirmation_required"}',
            content_type="application/json",
        )
    return body


async def _post(request):
    _web_only(request)
    body = await _confirmed_payload(request)
    try:
        row = await create_episode(
            request.app["db"], request["user_id"], request["device_id"],
            body.get("title"), body.get("summary"), body.get("happened_at"),
        )
    except ValueError as exc:
        raise web.HTTPBadRequest(
            text='{"error":"' + str(exc) + '"}', content_type="application/json",
        )
    return web.json_response({"episode": row}, status=201)


async def _get(request):
    _web_only(request)
    rows = await list_episodes(
        request.app["db"], request["user_id"], request.query.get("limit", 20),
    )
    return web.json_response({"episodes": rows})


async def _put(request):
    _web_only(request)
    episode_id = _episode_id(request)
    body = await _confirmed_payload(request)
    try:
        row = await correct_episode(
            request.app["db"], request["user_id"], request["device_id"], episode_id,
            body.get("title"), body.get("summary"), body.get("happened_at"),
        )
    except ValueError as exc:
        raise web.HTTPBadRequest(
            text='{"error":"' + str(exc) + '"}', content_type="application/json",
        )
    if row is None:
        raise web.HTTPNotFound(
            text='{"error":"episode_not_found"}', content_type="application/json",
        )
    return web.json_response({"episode": row})


async def _history(request):
    _web_only(request)
    rows = await episode_history(
        request.app["db"], request["user_id"], _episode_id(request),
    )
    return web.json_response({"history": rows})


async def _delete(request):
    _web_only(request)
    if not await delete_episode(
        request.app["db"], request["user_id"], _episode_id(request),
    ):
        raise web.HTTPNotFound(
            text='{"error":"episode_not_found"}', content_type="application/json",
        )
    return web.json_response({"deleted": True})


def register_routes(app):
    app.router.add_get("/api/episodes", _get)
    app.router.add_post("/api/episodes", _post)
    app.router.add_get("/api/episodes/{id}/history", _history)
    app.router.add_put("/api/episodes/{id}", _put)
    app.router.add_delete("/api/episodes/{id}", _delete)
