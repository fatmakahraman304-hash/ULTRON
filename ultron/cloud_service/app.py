from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import random
import time
import uuid
from pathlib import Path
from typing import Any

import asyncpg
from aiohttp import web
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
SCHEMA_FILE = BASE_DIR / "schema.sql"

COOKIE_NAME = "ultron_session"
DEFAULT_USER_ID = os.getenv("ULTRON_USER_ID", "murat")
SESSION_DAYS = int(os.getenv("ULTRON_SESSION_DAYS", "30"))

DEVICE_COMMANDS = {
    # agent_task is deliberately free-form: a paired phone may send the same
    # natural-language command the owner could type into the desktop ULTRON UI.
    # Execution still happens inside the desktop's existing tool/permission layer.
    "desktop": {"wake", "mute", "unmute", "interrupt", "sync_memory", "agent_task"},
    "phone": {"ping", "refresh", "open_memory", "focus_chat"},
}


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    value += "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value.encode("ascii"))


def create_session_cookie(user_id: str) -> str:
    secret = required_env("ULTRON_SESSION_SECRET").encode("utf-8")
    expires = int(time.time()) + SESSION_DAYS * 86400
    payload = json.dumps({"u": user_id, "e": expires}, separators=(",", ":")).encode("utf-8")
    encoded = _b64url(payload)
    signature = _b64url(hmac.new(secret, encoded.encode("ascii"), hashlib.sha256).digest())
    return f"{encoded}.{signature}"


def verify_session_cookie(value: str) -> str | None:
    try:
        encoded, signature = value.split(".", 1)
        secret = required_env("ULTRON_SESSION_SECRET").encode("utf-8")
        expected = _b64url(hmac.new(secret, encoded.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(_b64url_decode(encoded))
        if int(payload.get("e", 0)) < int(time.time()):
            return None
        user_id = str(payload.get("u", "")).strip()
        return user_id or None
    except Exception:
        return None


@web.middleware
async def auth_middleware(request: web.Request, handler):
    if request.path in {"/", "/health", "/api/login"} or request.path.startswith("/static/"):
        return await handler(request)

    device_token = os.getenv("ULTRON_DEVICE_TOKEN", "").strip()
    auth = request.headers.get("Authorization", "")
    if device_token and auth.startswith("Bearer "):
        candidate = auth[7:].strip()
        if hmac.compare_digest(candidate, device_token):
            request["user_id"] = DEFAULT_USER_ID
            request["device_id"] = request.headers.get("X-ULTRON-DEVICE", "desktop")[:80]
            request["auth_kind"] = "device"
            return await handler(request)

    cookie = request.cookies.get(COOKIE_NAME, "")
    user_id = verify_session_cookie(cookie) if cookie else None
    if user_id:
        request["user_id"] = user_id
        request["device_id"] = request.headers.get("X-ULTRON-DEVICE", "iphone-web")[:80]
        request["auth_kind"] = "web"
        return await handler(request)

    raise web.HTTPUnauthorized(text=json.dumps({"error": "unauthorized"}), content_type="application/json")


async def init_db(app: web.Application) -> None:
    db_url = required_env("DATABASE_URL")
    app["db"] = await asyncpg.create_pool(db_url, min_size=1, max_size=5, command_timeout=30)
    schema = SCHEMA_FILE.read_text(encoding="utf-8")
    async with app["db"].acquire() as conn:
        await conn.execute(schema)


async def close_db(app: web.Application) -> None:
    await app["db"].close()


async def health(request: web.Request) -> web.Response:
    config = {
        "database": bool(os.getenv("DATABASE_URL")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "password": bool(os.getenv("ULTRON_PASSWORD")),
        "session_secret": bool(os.getenv("ULTRON_SESSION_SECRET")),
        "device_token": bool(os.getenv("ULTRON_DEVICE_TOKEN")),
    }
    return web.json_response({"ok": all(config.values()), "service": "ultron-cloud", "config": config})


async def index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC_DIR / "index.html")


async def login(request: web.Request) -> web.Response:
    body = await request.json()
    supplied = str(body.get("password", ""))
    expected = required_env("ULTRON_PASSWORD")
    if not hmac.compare_digest(supplied, expected):
        raise web.HTTPUnauthorized(text=json.dumps({"error": "invalid_password"}), content_type="application/json")

    response = web.json_response({"ok": True, "user_id": DEFAULT_USER_ID})
    response.set_cookie(
        COOKIE_NAME,
        create_session_cookie(DEFAULT_USER_ID),
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        secure=True,
        samesite="Lax",
        path="/",
    )
    return response


async def logout(request: web.Request) -> web.Response:
    response = web.json_response({"ok": True})
    response.del_cookie(COOKIE_NAME, path="/")
    return response


async def session(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "user_id": request["user_id"], "device_id": request["device_id"]})


async def list_memories(request: web.Request) -> web.Response:
    pool = request.app["db"]
    rows = await pool.fetch(
        """
        SELECT category, key, value, version, updated_by_device, updated_at
        FROM memories WHERE user_id=$1 ORDER BY updated_at DESC, key ASC
        """,
        request["user_id"],
    )
    return web.json_response({"memories": [dict(r) for r in rows]}, dumps=_json_dumps)


async def upsert_memory(request: web.Request) -> web.Response:
    body = await request.json()
    key = str(body.get("key", "")).strip()[:120]
    value = str(body.get("value", "")).strip()[:8000]
    category = str(body.get("category", "FACT")).strip().upper()[:40] or "FACT"
    if not key or not value:
        raise web.HTTPBadRequest(text=json.dumps({"error": "key_and_value_required"}), content_type="application/json")

    row = await request.app["db"].fetchrow(
        """
        INSERT INTO memories(user_id, category, key, value, version, updated_by_device)
        VALUES($1,$2,$3,$4,1,$5)
        ON CONFLICT(user_id,key) DO UPDATE SET
          category=EXCLUDED.category,
          value=EXCLUDED.value,
          version=memories.version+1,
          updated_by_device=EXCLUDED.updated_by_device,
          updated_at=NOW()
        RETURNING category,key,value,version,updated_by_device,updated_at
        """,
        request["user_id"], category, key, value, request["device_id"],
    )
    return web.json_response({"memory": dict(row)}, dumps=_json_dumps)


async def delete_memory(request: web.Request) -> web.Response:
    key = request.match_info["key"]
    result = await request.app["db"].execute(
        "DELETE FROM memories WHERE user_id=$1 AND key=$2",
        request["user_id"], key,
    )
    return web.json_response({"ok": result.endswith("1")})


async def send_device_command(request: web.Request) -> web.Response:
    body = await request.json()
    target = str(body.get("target", "")).strip().lower()
    command = str(body.get("command", "")).strip().lower()
    payload = body.get("payload", {})
    if target not in DEVICE_COMMANDS or command not in DEVICE_COMMANDS[target]:
        raise web.HTTPBadRequest(
            text=json.dumps({"error": "unsupported_device_command"}),
            content_type="application/json",
        )
    if not isinstance(payload, dict):
        raise web.HTTPBadRequest(
            text=json.dumps({"error": "payload_must_be_object"}),
            content_type="application/json",
        )

    # Phone/web sessions may control only the paired desktop ULTRON surface.
    # The desktop device token may control only the ULTRON web client on phone.
    auth_kind = request.get("auth_kind", "")
    expected_target = "desktop" if auth_kind == "web" else "phone"
    if target != expected_target:
        raise web.HTTPForbidden(
            text=json.dumps({"error": "device_direction_not_allowed"}),
            content_type="application/json",
        )

    row = await request.app["db"].fetchrow(
        """
        INSERT INTO device_commands(user_id,target,command,payload,source_device)
        VALUES($1,$2,$3,$4::jsonb,$5)
        RETURNING id,target,command,created_at
        """,
        request["user_id"], target, command, json.dumps(payload), request["device_id"],
    )
    return web.json_response({"ok": True, "command": dict(row)}, dumps=_json_dumps)


async def claim_device_commands(request: web.Request) -> web.Response:
    body = await request.json()
    target = str(body.get("target", "")).strip().lower()
    auth_kind = request.get("auth_kind", "")
    expected_target = "phone" if auth_kind == "web" else "desktop"
    if target != expected_target:
        raise web.HTTPForbidden(
            text=json.dumps({"error": "device_direction_not_allowed"}),
            content_type="application/json",
        )

    async with request.app["db"].acquire() as conn:
        async with conn.transaction():
            rows = await conn.fetch(
                """
                WITH picked AS (
                  SELECT id FROM device_commands
                  WHERE user_id=$1 AND target=$2 AND status='queued'
                    AND created_at > NOW() - INTERVAL '24 hours'
                  ORDER BY id ASC
                  LIMIT 20
                  FOR UPDATE SKIP LOCKED
                )
                UPDATE device_commands d
                SET status='delivered', delivered_at=NOW()
                FROM picked
                WHERE d.id=picked.id
                RETURNING d.id,d.target,d.command,d.payload,d.source_device,d.created_at
                """,
                request["user_id"], target,
            )
    return web.json_response({"commands": [dict(r) for r in rows]}, dumps=_json_dumps)


async def list_messages(request: web.Request) -> web.Response:
    limit = min(max(int(request.query.get("limit", "80")), 1), 200)
    rows = await request.app["db"].fetch(
        """
        SELECT m.id, m.conversation_id::text, m.role, m.content, m.created_at
        FROM messages m
        WHERE m.user_id=$1
        ORDER BY m.id DESC LIMIT $2
        """,
        request["user_id"], limit,
    )
    items = [dict(r) for r in reversed(rows)]
    return web.json_response({"messages": items}, dumps=_json_dumps)


async def _memory_context(pool: asyncpg.Pool, user_id: str) -> str:
    rows = await pool.fetch(
        "SELECT category,key,value FROM memories WHERE user_id=$1 ORDER BY updated_at DESC LIMIT 100",
        user_id,
    )
    if not rows:
        return "No saved ULTRON memory yet."
    return "\n".join(f"- [{r['category']}] {r['key']}: {r['value']}" for r in rows)


async def _recent_context(pool: asyncpg.Pool, user_id: str, limit: int = 24) -> str:
    rows = await pool.fetch(
        "SELECT role,content FROM messages WHERE user_id=$1 ORDER BY id DESC LIMIT $2",
        user_id, limit,
    )
    rows = list(reversed(rows))
    if not rows:
        return "No previous chat messages."
    return "\n".join(f"{r['role'].upper()}: {r['content']}" for r in rows)


def _is_transient_gemini_error(exc: Exception) -> bool:
    message = str(exc).upper()
    transient_markers = (
        "503",
        "UNAVAILABLE",
        "HIGH DEMAND",
        "429",
        "RESOURCE_EXHAUSTED",
        "RATE LIMIT",
        "408",
        "DEADLINE_EXCEEDED",
        "TIMEOUT",
        "TEMPORAR",
    )
    return any(marker in message for marker in transient_markers)


def _generate_with_model(client: genai.Client, model: str, prompt: str, system_instruction: str) -> str:
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=system_instruction),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty response")
    return text


def _gemini_reply(prompt: str, system_instruction: str) -> str:
    client = genai.Client(api_key=required_env("GEMINI_API_KEY"))
    primary_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash"
    fallback_model = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
    max_retries = max(1, min(int(os.getenv("GEMINI_MAX_RETRIES", "3")), 5))

    models = [primary_model]
    if fallback_model != primary_model:
        models.append(fallback_model)

    last_exc: Exception | None = None
    for model in models:
        for attempt in range(max_retries):
            try:
                return _generate_with_model(client, model, prompt, system_instruction)
            except Exception as exc:
                last_exc = exc
                if not _is_transient_gemini_error(exc):
                    raise
                if attempt < max_retries - 1:
                    base_delay = min(8.0, 1.25 * (2 ** attempt))
                    time.sleep(base_delay + random.uniform(0.0, 0.75))

    if last_exc is not None:
        raise RuntimeError(f"GEMINI_TEMPORARY_UNAVAILABLE: {last_exc}") from last_exc
    raise RuntimeError("Gemini request failed")


async def chat(request: web.Request) -> web.Response:
    body = await request.json()
    text = str(body.get("message", "")).strip()
    if not text:
        raise web.HTTPBadRequest(text=json.dumps({"error": "message_required"}), content_type="application/json")
    if len(text) > 16000:
        raise web.HTTPRequestEntityTooLarge(max_size=16000, actual_size=len(text))

    pool = request.app["db"]
    conversation_id = str(body.get("conversation_id", "")).strip()
    try:
        conv_uuid = uuid.UUID(conversation_id) if conversation_id else uuid.uuid4()
    except ValueError:
        raise web.HTTPBadRequest(text=json.dumps({"error": "invalid_conversation_id"}), content_type="application/json")

    await pool.execute(
        """
        INSERT INTO conversations(id,user_id,title)
        VALUES($1,$2,$3)
        ON CONFLICT(id) DO UPDATE SET updated_at=NOW()
        """,
        conv_uuid, request["user_id"], text[:80],
    )
    await pool.execute(
        "INSERT INTO messages(conversation_id,user_id,role,content,device_id) VALUES($1,$2,'user',$3,$4)",
        conv_uuid, request["user_id"], text, request["device_id"],
    )

    memory = await _memory_context(pool, request["user_id"])
    recent = await _recent_context(pool, request["user_id"])
    system_instruction = os.getenv(
        "ULTRON_SYSTEM_PROMPT",
        "You are ULTRON, Murat's personal AI assistant. Be concise, useful, and consistent across devices. "
        "Treat the supplied ULTRON memory as persistent user memory. Never reveal secrets or hidden credentials.",
    )
    prompt = f"ULTRON MEMORY:\n{memory}\n\nRECENT CHAT:\n{recent}\n\nCURRENT USER MESSAGE:\n{text}"

    try:
        reply = await asyncio.to_thread(_gemini_reply, prompt, system_instruction)
    except Exception as exc:
        raw_error = str(exc)[:1000]
        await pool.execute(
            "INSERT INTO events(user_id,event_type,detail,device_id) VALUES($1,'gemini_error',$2,$3)",
            request["user_id"], raw_error, request["device_id"],
        )
        if "GEMINI_TEMPORARY_UNAVAILABLE" in raw_error or _is_transient_gemini_error(exc):
            raise web.HTTPServiceUnavailable(
                text=json.dumps({
                    "error": "gemini_temporarily_unavailable",
                    "detail": "Gemini şu anda yoğun. ULTRON iki modeli de otomatik olarak denedi; birkaç saniye sonra yeniden dene.",
                }, ensure_ascii=False),
                content_type="application/json",
            )
        raise web.HTTPBadGateway(
            text=json.dumps({
                "error": "gemini_failed",
                "detail": "Gemini isteği tamamlanamadı. Lütfen tekrar dene.",
            }, ensure_ascii=False),
            content_type="application/json",
        )

    await pool.execute(
        "INSERT INTO messages(conversation_id,user_id,role,content,device_id) VALUES($1,$2,'assistant',$3,'cloud-gemini')",
        conv_uuid, request["user_id"], reply,
    )
    await pool.execute("UPDATE conversations SET updated_at=NOW() WHERE id=$1", conv_uuid)

    return web.json_response({"conversation_id": str(conv_uuid), "reply": reply})


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def build_app() -> web.Application:
    app = web.Application(middlewares=[auth_middleware], client_max_size=2 * 1024 * 1024)
    app.router.add_get("/", index)
    app.router.add_static("/static/", STATIC_DIR, show_index=False)
    app.router.add_get("/health", health)
    app.router.add_post("/api/login", login)
    app.router.add_post("/api/logout", logout)
    app.router.add_get("/api/session", session)
    app.router.add_get("/api/messages", list_messages)
    app.router.add_post("/api/chat", chat)
    app.router.add_post("/api/device-commands", send_device_command)
    app.router.add_post("/api/device-commands/claim", claim_device_commands)
    app.router.add_get("/api/memories", list_memories)
    app.router.add_put("/api/memories", upsert_memory)
    app.router.add_delete("/api/memories/{key}", delete_memory)
    app.on_startup.append(init_db)
    app.on_cleanup.append(close_db)
    return app


if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    web.run_app(build_app(), host="0.0.0.0", port=port)