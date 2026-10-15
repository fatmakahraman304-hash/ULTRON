"""Owner-authenticated iPhone -> paired Windows Ollama chat bridge.

No Ollama on Render, no public Ollama proxy, no implicit Gemini fallback, and
no use of the desktop agent's dangerous tools. Laptop must be online and run
the current ULTRON queue worker. A single-use local chat command is attributed
to the user and checked for ownership on every poll. Cloud memory is shared.
"""
from __future__ import annotations

import json
import os
import time
import uuid

from aiohttp import web
from conversation_persona import build_system_instruction
from conversation_turns import load_contextual_thread_turns
from personal_context_focus import memory_focus_question
from auto_learning import learn_from_owner_message
from local_reply_validation import _validated_local_reply


async def post_local_chat(request: web.Request) -> web.Response:
    if request.get("auth_kind") != "web":
        raise web.HTTPForbidden(text='{"error":"web_session_required"}',
                                content_type="application/json")
    try:
        body = await request.json()
    except (TypeError, ValueError):
        return web.json_response({"error": "invalid_json"}, status=400)
    if not isinstance(body, dict):
        return web.json_response({"error": "invalid_payload"}, status=400)
    text = str(body.get("message") or "").strip()
    if not 1 <= len(text) <= 3000:
        return web.json_response({"error": "message_length_1_to_3000"}, status=400)
    raw_conv = str(body.get("conversation_id") or "").strip()
    try:
        conversation = uuid.UUID(raw_conv) if raw_conv else uuid.uuid4()
    except (TypeError, ValueError):
        return web.json_response({"error": "invalid_conversation_id"}, status=400)
    raw_request_id = body.get("request_id")
    try:
        request_id = uuid.UUID(raw_request_id) if isinstance(raw_request_id, str) else None
        if raw_request_id is not None and request_id is None:
            raise ValueError()
    except (ValueError, TypeError):
        return web.json_response({"error":"invalid_request_id"}, status=400)
    pool = request.app["db"]
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Serialize local-chat submissions from this owner. This lock is
            # transaction-scoped, not a held connection or GPU lock. Avoid
            # racing two queued requests against the same conversation, and
            # enforce the existing three-job owner cap atomically.
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
                "ultron-local-chat:" + request["user_id"],
            )
            # A lost POST response must return the existing task, even if the
            # desktop went offline since acceptance. Never fall back and duplicate it.
            if request_id is not None:
                previous = await conn.fetchrow(
                    "SELECT l.command_id,l.conversation_id,l.user_message_id,c.payload "
                    "FROM local_chat_requests l JOIN device_commands c ON c.id=l.command_id "
                    "WHERE l.user_id=$1 AND c.user_id=$1 AND l.request_id=$2",
                    request["user_id"], request_id,
                )
                if previous:
                    payload = previous["payload"]
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    if payload.get("text") != text or (raw_conv and previous["conversation_id"] != conversation):
                        return web.json_response({"error":"request_id_conflict"}, status=409)
                    return web.json_response({"status":"queued", "command_id":previous["command_id"],
                        "conversation_id":str(previous["conversation_id"]), "provider":"local",
                        "user_message_id":previous["user_message_id"], "replayed":True}, status=202)
            online = await conn.fetchval(
                "SELECT COALESCE(last_seen > NOW() - INTERVAL '15 seconds' "
                "AND state->'local_chat_ready' = 'true'::jsonb, FALSE) "
                "FROM device_presence WHERE user_id=$1 AND device='desktop'",
                request["user_id"]
            )
            if not online:
                return web.json_response({
                    "error": "desktop_offline",
                    "detail": "Yerel sohbet şu anda hazır değil."
                }, status=409)
            outstanding = await conn.fetchval(
                "SELECT COUNT(*) FROM device_commands "
                "WHERE user_id=$1 AND target='desktop' "
                "AND command='agent_task' AND payload->>'mode'='local_brain' "
                "AND status IN ('queued','delivered')",
                request["user_id"],
            )
            if int(outstanding or 0) >= 3:
                return web.json_response(
                    {"error":"local_brain_busy",
                     "detail":"Yerel beyin meşgul; önceki yanıtı bekle."},
                    status=429,
                )
            pending_thread = await conn.fetchval(
                "SELECT COUNT(*) FROM local_chat_requests l "
                "JOIN device_commands c ON c.id=l.command_id "
                "WHERE l.user_id=$1 AND l.conversation_id=$2 "
                "AND c.user_id=$1 AND c.target='desktop' "
                "AND c.command='agent_task' "
                "AND c.payload->>'mode'='local_brain' "
                "AND c.status IN ('queued','delivered')",
                request["user_id"], conversation,
            )
            if pending_thread:
                return web.json_response(
                    {"error":"local_chat_thread_busy",
                     "detail":"Bu sohbetin önceki yanıtını bekle."},
                    status=429,
                )
            completed = await conn.fetch(
                "SELECT l.command_id,c.result FROM local_chat_requests l "
                "JOIN device_commands c ON c.id=l.command_id "
                "WHERE l.user_id=$1 AND c.user_id=$1 AND l.conversation_id=$2 "
                "AND c.status='completed' AND l.reply_saved=FALSE ORDER BY l.command_id",
                request["user_id"], conversation,
            )
            for old in completed:
                result = old["result"]
                if isinstance(result, str):
                    result = json.loads(result)
                details = _validated_local_reply(result)
                if details is None:
                    return web.json_response({"error":"previous_local_reply_invalid"}, status=409)
                await _save_reply(conn, request["user_id"], old["command_id"], details)
            # Retrieve only the authenticated owner's current-thread turns
            # before querying saved facts. Follow-up focus must agree between
            # local Qwen and cloud Gemini; never use assistant text as intent.
            turns = await load_contextual_thread_turns(
                conn, request["user_id"], conversation,
                question=text, max_chars=2600, limit=12,
            )
            focus_query = memory_focus_question(text, turns)
            memory = (await request.app["local_memory_context"](
                conn, request["user_id"], focus_query
            ))[:2400]
            system = build_system_instruction(
                base_prompt=os.getenv("ULTRON_SYSTEM_PROMPT"),
                memory=memory, recent="Conversation turns provided separately with roles.",
                user_message=text, read_only=True, max_chars=4500,
                has_prior_turns=bool(turns),
            )

            claimed = await conn.fetchval(
                "INSERT INTO conversations(id,user_id,title) VALUES($1,$2,$3) "
                "ON CONFLICT(id) DO UPDATE SET updated_at=NOW() "
                "WHERE conversations.user_id=EXCLUDED.user_id RETURNING id",
                conversation, request["user_id"], text[:80],
            )
            if claimed is None:
                raise web.HTTPNotFound(text='{"error":"conversation_not_found"}',
                                       content_type="application/json")
            row = await conn.fetchrow(
                "INSERT INTO device_commands(user_id,target,command,payload,source_device) "
                "VALUES($1,'desktop','agent_task',$2::jsonb,$3) RETURNING id",
                request["user_id"],
                json.dumps({"mode":"local_brain","text":text,"system":system,
                            "turns":turns}, ensure_ascii=False),
                request["device_id"],
            )
            user_message_id = await conn.fetchval(
                "INSERT INTO messages(conversation_id,user_id,role,content,device_id) "
                "VALUES($1,$2,'user',$3,$4) RETURNING id",
                conversation, request["user_id"], text, request["device_id"],
            )
            await conn.execute(
                "INSERT INTO local_chat_requests(command_id,user_id,conversation_id,request_id,user_message_id) "
                "VALUES($1,$2,$3,$4,$5)",row["id"],request["user_id"],conversation,request_id,user_message_id,
            )
    # User text accepted into the real local queue; no assistant/tool text is learned.
    try:
        await learn_from_owner_message(pool, request["user_id"], text)
    except Exception:
        pass  # Learning is ancillary and cannot fail the chat request.
    return web.json_response({
        "status": "queued", "command_id": row["id"],
        "conversation_id": str(conversation), "provider": "local", "user_message_id": user_message_id,
    }, status=202)


async def _save_reply(conn, user_id, ident, details):
    """Persist validated local output once, including before the next turn loads history."""
    pending = await conn.fetchrow(
        "SELECT reply_saved,conversation_id,assistant_message_id FROM local_chat_requests "
        "WHERE command_id=$1 AND user_id=$2 FOR UPDATE", ident, user_id,
    )
    if not pending:
        return None
    if pending["reply_saved"]:
        return pending["assistant_message_id"]
    reply, model, source = details
    message_id = await conn.fetchval(
        "INSERT INTO messages(conversation_id,user_id,role,content,device_id) "
        "VALUES($1,$2,'assistant',$3,$4) RETURNING id",
        pending["conversation_id"], user_id, reply, source,
    )
    await conn.execute(
        "UPDATE local_chat_requests SET reply_saved=TRUE,assistant_message_id=$2 WHERE command_id=$1",
        ident, message_id,
    )
    return message_id


async def save_pending_local_replies(pool, user_id):
    """Recover finished replies after a phone closes or its polling deadline ends."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            rows = await conn.fetch(
                "SELECT l.command_id,c.result FROM local_chat_requests l "
                "JOIN device_commands c ON c.id=l.command_id "
                "WHERE l.user_id=$1 AND c.user_id=$1 AND l.reply_saved=FALSE "
                "AND c.status='completed' AND c.command='agent_task' "
                "AND c.payload->>'mode'='local_brain' ORDER BY l.command_id LIMIT 100",
                user_id,
            )
            for row in rows:
                result = row["result"]
                if isinstance(result, str):
                    result = json.loads(result)
                details = _validated_local_reply(result)
                if details is not None:
                    await _save_reply(conn, user_id, row["command_id"], details)


async def get_local_chat(request: web.Request) -> web.Response:
    if request.get("auth_kind") != "web":
        raise web.HTTPForbidden(text='{"error":"web_session_required"}',
                                content_type="application/json")
    try:
        ident = int(request.match_info["id"])
        if ident < 1:
            raise ValueError()
    except (TypeError, ValueError):
        return web.json_response({"error":"invalid_id"},status=400)
    pool=request.app["db"]
    # Ownership + local-only mode checked in SQL. No access to other tasks.
    row=await pool.fetchrow(
        "SELECT c.status,c.result,c.payload,l.conversation_id,l.reply_saved "
        "FROM local_chat_requests l JOIN device_commands c ON c.id=l.command_id "
        "WHERE l.command_id=$1 AND l.user_id=$2 AND c.user_id=$2 "
        "AND c.payload->>'mode'='local_brain'",
        ident, request["user_id"],
    )
    if not row:
        return web.json_response({"error":"not_found"},status=404)
    status=str(row["status"])
    result=row["result"]
    if isinstance(result,str):
        try: result=json.loads(result)
        except ValueError: result={}
    if not isinstance(result,dict):
        result={}
    if status != "completed":
        return web.json_response({
            "status":status,
            "detail": str(result.get("message") or "")[:180] if status in ("failed","expired","cancelled") else "",
            "provider":"local",
        }, status=200)

    details = _validated_local_reply(result)
    if details is None:
        return web.json_response(
            {"status":"failed","error":"invalid_local_reply"}, status=502,
        )
    reply, model, source = details
    # Save reply exactly once, protected by Postgres row lock.
    async with pool.acquire() as conn:
        async with conn.transaction():
            assistant_message_id = await _save_reply(conn, request["user_id"], ident, details)
    return web.json_response({
        "status":"completed","provider":"local", "result_provider":result.get("provider", "local-ollama"),
        "assistant_message_id":assistant_message_id, "command_id":ident,
        "reply":reply,"model":model,
        "conversation_id":str(row["conversation_id"]),
    })


def register_local_brain_routes(app:web.Application,memory_context,recent_context)->None:
    app["local_memory_context"]=memory_context
    app["local_recent_context"]=recent_context
    app.router.add_post("/api/local-chat",post_local_chat)
    app.router.add_get("/api/local-chat/{id}",get_local_chat)
