"""Reviewable, browser-owner-approved personal memory learning.

Submitting a proposal never changes model-visible memory. Only an explicit
approval inserts a new memory entry. Existing memories never get overwritten,
and proposals from different owners are strictly separated.
"""
from __future__ import annotations

import re
from aiohttp import web

_ALLOWED = frozenset(("PREFERENCE", "PROJECT", "GOAL", "FACT", "DEVICE"))
_ID = re.compile(r"[1-9][0-9]{0,17}\Z")


def validate_suggestion(body: object) -> tuple[str, str, str]:
    if not isinstance(body, dict):
        raise ValueError("invalid_body")
    category, key, value = body.get("category"), body.get("key"), body.get("value")
    if not isinstance(category, str) or category not in _ALLOWED:
        raise ValueError("unsupported_category")
    if not isinstance(key, str) or not (1 <= len(key.strip()) <= 120) or "\x00" in key:
        raise ValueError("invalid_key")
    if not isinstance(value, str) or not (1 <= len(value.strip()) <= 1000) or "\x00" in value:
        raise ValueError("invalid_value")
    return category, key.strip(), value.strip()


def require_owner_browser(request):
    if request.get("auth_kind") != "web":
        raise web.HTTPForbidden(text='{"error":"owner_browser_session_required"}', content_type="application/json")
    if request.method in ("POST", "DELETE"):
        if request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            raise web.HTTPForbidden(text='{"error":"cross_site_denied"}', content_type="application/json")
        if request.method == "POST" and request.content_type != "application/json":
            raise web.HTTPUnsupportedMediaType(text='{"error":"json_required"}', content_type="application/json")


def _proposal_id(request):
    value = request.match_info.get("id", "")
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise web.HTTPBadRequest(text='{"error":"invalid_id"}', content_type="application/json")
    return int(value)


async def list_learning_proposals(request):
    require_owner_browser(request)
    rows = await request.app["db"].fetch(
        "SELECT id,category,key,value,status FROM learning_proposals "
        "WHERE user_id=$1 ORDER BY id DESC LIMIT 60",
        request["user_id"],
    )
    return web.json_response({
        "proposals": [dict(row) for row in rows],
        "auto_learning_enabled": False,
        "requires_explicit_approval": True,
    })


async def suggest_learning(request):
    require_owner_browser(request)
    try:
        category, key, value = validate_suggestion(await request.json())
    except (ValueError, TypeError):
        return web.json_response({"error": "invalid_learning_fields"}, status=400)
    pool = request.app["db"]
    count = await pool.fetchval(
        "SELECT COUNT(*) FROM learning_proposals WHERE user_id=$1 AND status='pending'",
        request["user_id"],
    )
    if count >= 30:
        return web.json_response({"error": "review_pending_proposals_first"}, status=429)
    row = await pool.fetchrow(
        "INSERT INTO learning_proposals(user_id,category,key,value) "
        "VALUES($1,$2,$3,$4) "
        "ON CONFLICT (user_id,key) WHERE status='pending' DO NOTHING "
        "RETURNING id,category,key,value,status",
        request["user_id"], category, key, value,
    )
    if row is None:
        return web.json_response({"error": "proposal_already_pending"}, status=409)
    return web.json_response({"proposal": dict(row), "memory_saved": False}, status=201)


async def decide_learning(request):
    require_owner_browser(request)
    proposal_id = _proposal_id(request)
    try:
        body = await request.json()
    except (ValueError, TypeError):
        return web.json_response({"error": "invalid_json"}, status=400)
    if not isinstance(body, dict) or type(body.get("approve")) is not bool:
        return web.json_response({"error": "approve_boolean_required"}, status=400)
    approve = body["approve"]
    pool = request.app["db"]
    async with pool.acquire() as db:
        async with db.transaction():
            proposal = await db.fetchrow(
                "SELECT id,category,key,value,status FROM learning_proposals "
                "WHERE id=$1 AND user_id=$2 FOR UPDATE",
                proposal_id, request["user_id"],
            )
            if proposal is None:
                raise web.HTTPNotFound(text='{"error":"not_found"}', content_type="application/json")
            if proposal["status"] != "pending":
                return web.json_response({"error": "already_decided"}, status=409)
            if approve:
                saved = await db.fetchval(
                    "INSERT INTO memories(user_id,category,key,value,updated_by_device) "
                    "VALUES($1,$2,$3,$4,'owner-approved-learning') "
                    "ON CONFLICT (user_id,key) DO NOTHING RETURNING key",
                    request["user_id"], proposal["category"], proposal["key"], proposal["value"],
                )
                if saved is None:
                    return web.json_response({"error": "memory_key_already_exists"}, status=409)
            row = await db.fetchrow(
                "UPDATE learning_proposals SET status=$3,reviewed_at=NOW() "
                "WHERE id=$1 AND user_id=$2 RETURNING id,category,key,value,status",
                proposal_id, request["user_id"], "approved" if approve else "rejected",
            )
    return web.json_response({"proposal": dict(row), "memory_saved": approve})


async def delete_learning_proposal(request):
    require_owner_browser(request)
    proposal_id = _proposal_id(request)
    row = await request.app["db"].fetchrow(
        "DELETE FROM learning_proposals WHERE id=$1 AND user_id=$2 RETURNING id",
        proposal_id, request["user_id"],
    )
    if row is None:
        raise web.HTTPNotFound(text='{"error":"not_found"}', content_type="application/json")
    return web.json_response({"deleted": True, "memory_unchanged": True})


def register_learning_routes(app):
    app.router.add_get("/api/learning-proposals", list_learning_proposals)
    app.router.add_post("/api/learning-proposals", suggest_learning)
    app.router.add_post("/api/learning-proposals/{id}/decision", decide_learning)
    app.router.add_delete("/api/learning-proposals/{id}", delete_learning_proposal)
