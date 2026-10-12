"""Explicit opt-in, owner-scoped local Qwen listening analysis bridge.

Local means inference on the paired Windows Ollama, NOT zero-cloud transit.
Each chunk temporarily resides in the Render device-command queue. No
conversation, auto-learning or long-term memory write is performed.
"""
from __future__ import annotations

import hashlib
import json
import uuid

from aiohttp import web
from listening_analysis import (
    ANALYST_SYSTEM, ListeningPayloadError,
    build_request, checked_analysis,
)
from local_reply_validation import _validated_local_reply


def _checksum(stage: str, prompt: str) -> str:
    return hashlib.sha256((stage + "\0" + prompt).encode("utf-8")).hexdigest()


def _parse_submission(body: dict) -> tuple[uuid.UUID, str, str, int, str]:
    if not isinstance(body, dict):
        raise ListeningPayloadError("Geçersiz gönderim.")
    key = body.get("request_id")
    if not isinstance(key, str):
        raise ListeningPayloadError("İstek kimliği eksik.")
    try:
        ident = uuid.UUID(key)
    except (ValueError, TypeError, AttributeError) as error:
        raise ListeningPayloadError("İstek kimliği geçersiz.") from error
    stage, prompt, limit = build_request(body)
    if len(prompt) > 14000:
        raise ListeningPayloadError("Yerel analiz bölüm sınırı aşıldı.")
    return ident, stage, prompt, limit, _checksum(stage, prompt)


async def post_local_listening(request: web.Request) -> web.Response:
    if request.get("auth_kind") != "web":
        raise web.HTTPForbidden()
    try:
        body = await request.json()
        ident, stage, prompt, cap, digest = _parse_submission(body)
    except (ValueError, TypeError, ListeningPayloadError):
        return web.json_response({"error": "invalid_analysis_request"}, status=400)
    pool = request.app["db"]
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1::text,0))",
                "ultron-listening:" + request["user_id"],
            )
            existing = await conn.fetchrow(
                "SELECT id,payload FROM device_commands "
                "WHERE user_id=$1 AND target='desktop' AND command='agent_task' "
                "AND payload->>'mode'='local_listening_analysis' "
                "AND payload->>'request_id'=$2 ORDER BY id DESC LIMIT 1",
                request["user_id"], str(ident),
            )
            if existing:
                raw = existing["payload"]
                payload = json.loads(raw) if isinstance(raw, str) else raw
                if payload.get("checksum") != digest:
                    return web.json_response({"error": "request_id_conflict"}, status=409)
                return web.json_response(
                    {"status": "queued", "command_id": existing["id"], "replayed": True},
                    status=202,
                )
            ready = await conn.fetchval(
                "SELECT COALESCE(last_seen > NOW() - INTERVAL '15 seconds' "
                "AND state->>'local_chat_ready'='true' "
                "AND state->>'listening_analysis_ready'='true', FALSE) "
                "FROM device_presence WHERE user_id=$1 AND device='desktop'",
                request["user_id"],
            )
            if not ready:
                return web.json_response(
                    {"error": "local_analyst_unavailable",
                     "detail": "Güncel Windows Qwen analiz işçisi hazır değil."},
                    status=409,
                )
            outstanding = await conn.fetchval(
                "SELECT COUNT(*) FROM device_commands "
                "WHERE user_id=$1 AND target='desktop' "
                "AND command='agent_task' "
                "AND payload->>'mode'='local_listening_analysis' "
                "AND status IN ('queued','delivered')",
                request["user_id"],
            )
            if int(outstanding or 0) >= 2:
                return web.json_response({"error": "local_analyst_busy"}, status=429)
            row = await conn.fetchrow(
                "INSERT INTO device_commands(user_id,target,command,payload,source_device) "
                "VALUES($1,'desktop','agent_task',$2::jsonb,$3) RETURNING id",
                request["user_id"],
                json.dumps({
                    "mode": "local_listening_analysis",
                    "request_id": str(ident),
                    "stage": stage,
                    "checksum": digest,
                    "text": prompt,
                    "system": ANALYST_SYSTEM,
                }, ensure_ascii=False),
                request["device_id"],
            )
    return web.json_response(
        {"status": "queued", "command_id": row["id"], "provider": "local-ollama"},
        status=202,
    )


async def get_local_listening(request: web.Request) -> web.Response:
    if request.get("auth_kind") != "web":
        raise web.HTTPForbidden()
    try:
        ident = int(request.match_info["id"])
        if ident < 1:
            raise ValueError()
    except (ValueError, TypeError):
        raise web.HTTPBadRequest()
    pool = request.app["db"]
    row = await pool.fetchrow(
        "SELECT status,result,payload FROM device_commands "
        "WHERE id=$1 AND user_id=$2 AND target='desktop' "
        "AND command='agent_task' "
        "AND payload->>'mode'='local_listening_analysis'",
        ident, request["user_id"],
    )
    if not row:
        raise web.HTTPNotFound()
    status = str(row["status"])
    raw = row["payload"]
    payload = json.loads(raw) if isinstance(raw, str) else raw
    stage = str(payload.get("stage") or "")
    if status not in ("completed", "failed", "cancelled", "expired"):
        return web.json_response({"status": status})
    # Scrub the raw transcription from the temporary command payload once
    # terminal status is observed; never retain speech in conversation memory.
    await pool.execute(
        "UPDATE device_commands SET payload=payload-'text'-'system' "
        "WHERE id=$1 AND user_id=$2 AND payload->>'mode'='local_listening_analysis'",
        ident, request["user_id"],
    )
    if status != "completed":
        return web.json_response({"status": "failed", "error": "local_analyst_failed"})
    value = row["result"]
    result = json.loads(value) if isinstance(value, str) else value
    validated = _validated_local_reply(result)
    if validated is None or validated[2] != "desktop-local-ollama":
        return web.json_response(
            {"status": "failed", "error": "invalid_local_analysis"}, status=502,
        )
    answer = checked_analysis(validated[0], 9500 if stage == "final" else 2000)
    return web.json_response(
        {"status": "completed", "stage": stage, "analysis": answer,
         "provider": "local-ollama", "model": validated[1], "saved": False},
    )


def register_local_listening_routes(app: web.Application) -> None:
    app.router.add_post("/api/listening-analysis/local", post_local_listening)
    app.router.add_get("/api/listening-analysis/local/{id}", get_local_listening)
