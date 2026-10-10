"""Owner-authenticated iPhone -> paired Windows Ollama chat bridge.

No Ollama on Render, no public Ollama proxy, no implicit Gemini fallback, and
no use of the desktop agent's dangerous tools. Laptop must be online and run
the current ULTRON queue worker. A single-use local chat command is attributed
to the user and checked for ownership on every poll. Cloud memory is shared.
"""
from __future__ import annotations

import json
import time
import uuid

from aiohttp import web
from conversation_persona import build_system_instruction
from conversation_turns import load_thread_turns
from auto_learning import learn_from_owner_message


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
    pool = request.app["db"]
    online = await pool.fetchval(
        "SELECT COALESCE(last_seen > NOW() - INTERVAL '15 seconds', FALSE) "
        "FROM device_presence WHERE user_id=$1 AND device='desktop'",
        request["user_id"]
    )
    if not online:
        return web.json_response({
            "error": "desktop_offline",
            "detail": "Ücretsiz yerel beyin için Windows ULTRON açık olmalı. Gemini'yi istersen seçebilirsin."
        }, status=409)
    # A short rate limit avoids uncontrolled GPU queue accumulation.
    outstanding = await pool.fetchval(
        "SELECT COUNT(*) FROM device_commands WHERE user_id=$1 AND target='desktop' "
        "AND command='agent_task' AND payload->>'mode'='local_brain' "
        "AND status IN ('queued','delivered')",
        request["user_id"],
    )
    if int(outstanding or 0) >= 3:
        return web.json_response({"error":"local_brain_busy",
            "detail":"Yerel beyin meşgul; önceki yanıtı bekle."},status=429)

    # Bound shared memory/history to protect 4GB consumer GPU.
    memory = (await request.app["local_memory_context"](pool, request["user_id"]))[:2400]
    turns = await load_thread_turns(pool, request["user_id"], conversation,
                                    max_chars=2600, limit=12)
    system = build_system_instruction(
        memory=memory, recent="Conversation turns provided separately with roles.",
        user_message=text, read_only=True, max_chars=4500,
        has_prior_turns=bool(turns),
    )

    async with pool.acquire() as conn:
        async with conn.transaction():
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
            await conn.execute(
                "INSERT INTO local_chat_requests(command_id,user_id,conversation_id) "
                "VALUES($1,$2,$3)",row["id"],request["user_id"],conversation,
            )
            await conn.execute(
                "INSERT INTO messages(conversation_id,user_id,role,content,device_id) "
                "VALUES($1,$2,'user',$3,$4)",
                conversation, request["user_id"], text, request["device_id"],
            )
    # User text accepted into the real local queue; no assistant/tool text is learned.
    try:
        await learn_from_owner_message(pool, request["user_id"], text)
    except Exception:
        pass  # Learning is ancillary and cannot fail the chat request.
    return web.json_response({
        "status": "queued", "command_id": row["id"],
        "conversation_id": str(conversation), "provider": "local",
    }, status=202)


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

    reply=str(result.get("assistant_reply") or "").strip()[:12000]
    if not reply:
        return web.json_response({"status":"failed","error":"empty_model_reply"},status=502)
    # Save reply exactly once, protected by Postgres row lock.
    async with pool.acquire() as conn:
        async with conn.transaction():
            pending=await conn.fetchrow(
                "SELECT reply_saved,conversation_id FROM local_chat_requests "
                "WHERE command_id=$1 AND user_id=$2 FOR UPDATE",ident,request["user_id"]
            )
            if pending and not pending["reply_saved"]:
                await conn.execute(
                    "INSERT INTO messages(conversation_id,user_id,role,content,device_id) "
                    "VALUES($1,$2,'assistant',$3,'desktop-local-ollama')",
                    pending["conversation_id"],request["user_id"],reply,
                )
                await conn.execute(
                    "UPDATE local_chat_requests SET reply_saved=TRUE WHERE command_id=$1",
                    ident,
                )
    return web.json_response({
        "status":"completed","provider":"local",
        "reply":reply,"model":str(result.get("model") or "")[:90],
        "conversation_id":str(row["conversation_id"]),
    })


def register_local_brain_routes(app:web.Application,memory_context,recent_context)->None:
    app["local_memory_context"]=memory_context
    app["local_recent_context"]=recent_context
    app.router.add_post("/api/local-chat",post_local_chat)
    app.router.add_get("/api/local-chat/{id}",get_local_chat)
