"""Owner-only, bounded Qwen listening analysis over the existing desktop queue.

Transport requires DB rows, but no conversation history, owner learning or
persistent memory writes. A stage's transcription sits briefly in the queue,
and is scrubbed once the result is retrieved or expires.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from aiohttp import web

from listening_analysis import ANALYST_SYSTEM, ListeningPayloadError, build_request
from model_identity import is_qwen_model
from response_quality import strip_qwen_thinking


def _identity(body: dict) -> tuple[uuid.UUID, str]:
    raw = body.get("request_id")
    if not isinstance(raw, str):
        raise ValueError("request_id_required")
    request_id = uuid.UUID(raw)
    normalized = json.dumps({
        "stage": body.get("stage"), "text": body.get("text"),
        "part": body.get("part"), "total": body.get("total"),
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return request_id, hashlib.sha256(normalized.encode("utf8")).hexdigest()


def _validated_analysis(result, stage: str) -> tuple[str, str] | None:
    if not isinstance(result, dict):
        return None
    if result.get("provider") != "local-ollama" or result.get("stage") != stage:
        return None
    model = result.get("model")
    if not isinstance(model, str) or not is_qwen_model(model):
        return None
    content = result.get("analysis")
    if not isinstance(content, str) or len(content) > 9500:
        return None
    answer = strip_qwen_thinking(content).strip()
    if not answer or answer.lower().startswith("<think>"):
        # Malformed escape-encoded thinking tags must never be shown as a
        # finished Qwen answer (the sanitizer handles real newlines).
        return None
    return answer, model


async def _scrub_expired(pool, user_id: str):
    # Scrub old microphone text *before* normal queue claim can dispatch it.
    await pool.execute(
        """
        UPDATE device_commands SET status='expired',
          result='{"message":"Yerel dinleme analizi zaman aşımına uğradı."}'::jsonb,
          payload=payload - 'text' - 'system', completed_at=NOW()
        WHERE user_id=$1 AND target='desktop'
          AND command='agent_task'
          AND payload->>'mode'='local_listening_analysis'
          AND status IN ('queued','delivered')
          AND created_at < NOW() - INTERVAL '30 minutes'
        """, user_id,
    )


async def post_local_listening_analysis(request: web.Request) -> web.Response:
    if request.get("auth_kind") != "web":
        raise web.HTTPForbidden(text='{"error":"web_session_required"}',
                                content_type="application/json")
    try:
        body = await request.json()
        stage, prompt, _ = build_request(body)
        request_id, digest = _identity(body)
    except (ValueError, TypeError, ListeningPayloadError):
        return web.json_response({"error":"invalid_analysis_request"},status=400)
    pool = request.app["db"]
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1::text,0))",
                "ultron-listening-analysis:" + request["user_id"],
            )
            await _scrub_expired(conn, request["user_id"])
            previous = await conn.fetchrow(
                "SELECT id,payload FROM device_commands "
                "WHERE user_id=$1 AND target='desktop' AND command='agent_task' "
                "AND payload->>'mode'='local_listening_analysis' "
                "AND payload->>'request_id'=$2 "
                "ORDER BY id DESC LIMIT 1",
                request["user_id"], str(request_id),
            )
            if previous:
                saved = previous["payload"]
                if isinstance(saved, str):
                    saved = json.loads(saved)
                if saved.get("digest") != digest:
                    return web.json_response({"error":"request_id_conflict"},status=409)
                return web.json_response({
                    "id": previous["id"], "status":"queued", "provider":"local-ollama",
                    "replayed":True,
                },status=202)
            ready = await conn.fetchval(
                "SELECT COALESCE(last_seen > NOW()-INTERVAL '15 seconds' "
                "AND state->'local_listening_analysis_ready'='true'::jsonb,FALSE) "
                "FROM device_presence WHERE user_id=$1 AND device='desktop'",
                request["user_id"],
            )
            if not ready:
                return web.json_response({
                    "error":"local_analysis_offline",
                    "detail":"Yerel Qwen analiz işçisi güncel veya hazır değil.",
                },status=409)
            running = await conn.fetchval(
                "SELECT COUNT(*) FROM device_commands "
                "WHERE user_id=$1 AND target='desktop' AND command='agent_task' "
                "AND payload->>'mode'='local_listening_analysis' "
                "AND status IN ('queued','delivered')",
                request["user_id"],
            )
            if int(running or 0)>=1:
                return web.json_response({
                    "error":"local_analysis_busy", "detail":"Önceki analiz bölümü bekleniyor.",
                },status=429)
            row = await conn.fetchrow(
                "INSERT INTO device_commands(user_id,target,command,payload,source_device,max_retries) "
                "VALUES($1,'desktop','agent_task',$2::jsonb,$3,0) RETURNING id",
                request["user_id"],json.dumps({
                    "mode":"local_listening_analysis",
                    "stage":stage,
                    "text":prompt,
                    "system":ANALYST_SYSTEM,
                    "digest":digest,
                    "request_id":str(request_id),
                },ensure_ascii=False),request["device_id"],
            )
    return web.json_response({
        "id":row["id"],"status":"queued","provider":"local-ollama",
    },status=202)


async def get_local_listening_analysis(request: web.Request) -> web.Response:
    if request.get("auth_kind") != "web":
        raise web.HTTPForbidden(text='{"error":"web_session_required"}',
                                content_type="application/json")
    try:
        ident = int(request.match_info["id"])
        if ident < 1:
            raise ValueError()
    except (ValueError,TypeError):
        return web.json_response({"error":"invalid_id"},status=400)
    pool=request.app["db"]
    await _scrub_expired(pool,request["user_id"])
    row=await pool.fetchrow(
        "SELECT id,status,result,payload FROM device_commands "
        "WHERE id=$1 AND user_id=$2 AND target='desktop' AND command='agent_task' "
        "AND payload->>'mode'='local_listening_analysis'",
        ident,request["user_id"],
    )
    if not row:
        return web.json_response({"error":"not_found"},status=404)
    status=row["status"]
    if status not in ("completed","failed","expired","cancelled"):
        return web.json_response({"status":status,"id":ident})
    # Text scrub is idempotent. Results remain read-only for lost-response polls.
    await pool.execute(
        "UPDATE device_commands SET payload=payload - 'text' - 'system' "
        "WHERE id=$1 AND user_id=$2 AND payload->>'mode'='local_listening_analysis'",
        ident,request["user_id"],
    )
    if status!="completed":
        return web.json_response({"status":status,"error":"local_analysis_unavailable"})
    result=row["result"]
    if isinstance(result,str):
        try:result=json.loads(result)
        except ValueError:result={}
    saved=row["payload"]
    if isinstance(saved,str):
        saved=json.loads(saved)
    stage=saved.get("stage")
    checked=_validated_analysis(result,stage)
    if checked is None:
        return web.json_response({"status":"failed","error":"invalid_local_analysis"},status=502)
    answer,model=checked
    return web.json_response({
        "status":"completed","stage":stage,"analysis":answer,
        "model":model,"provider":"local-ollama","saved":False,
    })


def register_local_listening_analysis_routes(app:web.Application)->None:
    app.router.add_post("/api/local-listening-analysis",post_local_listening_analysis)
    app.router.add_get("/api/local-listening-analysis/{id}",get_local_listening_analysis)
