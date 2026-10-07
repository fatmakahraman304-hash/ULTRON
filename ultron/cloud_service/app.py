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
    "phone": {"ping", "refresh", "open_memory", "focus_chat", "open_remote", "vibrate", "scroll_top"},
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
    return web.json_response({
        "ok": all(config.values()),
        "service": "ultron-cloud",
        "config": config,
        "deploy": {
            "commit": os.getenv("RENDER_GIT_COMMIT", ""),
            "branch": os.getenv("RENDER_GIT_BRANCH", ""),
        },
    })


async def index(request: web.Request) -> web.FileResponse:
    response = web.FileResponse(STATIC_DIR / "index.html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


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

    # One-shot controls (mute, wake, interrupt, memory sync) should never sit in
    # a queue and surprise the user later. Only free-form agent tasks are allowed
    # to wait for an offline laptop to reconnect.
    if auth_kind == "web" and target == "desktop" and command != "agent_task":
        online = await request.app["db"].fetchval(
            """
            SELECT COALESCE(last_seen > NOW() - INTERVAL '15 seconds', FALSE)
            FROM device_presence
            WHERE user_id=$1 AND device='desktop'
            """,
            request["user_id"],
        )
        if not online:
            raise web.HTTPConflict(
                text=json.dumps({"error": "desktop_offline"}),
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
            # Never execute a forgotten remote command days later. Old queued
            # work is made visible as expired instead of silently lingering.
            await conn.execute(
                """
                UPDATE device_commands
                SET status='expired',
                    result='{"message":"Görev 24 saat içinde teslim alınmadığı için süresi doldu."}'::jsonb,
                    completed_at=NOW()
                WHERE user_id=$1 AND target=$2 AND status='queued'
                  AND created_at <= NOW() - INTERVAL '24 hours'
                """,
                request["user_id"], target,
            )
            # A delivered agent task owns the single-task lane only while its
            # desktop lease is alive. The desktop renews delivered_at every few
            # seconds; if that heartbeat disappears for 20 seconds the worker is
            # gone/stuck and the lane must be released automatically.
            await conn.execute(
                """
                UPDATE device_commands
                SET status='failed',
                    result='{"message":"Laptop görev lease''i 20 saniye boyunca yenilenmedi; kuyruk otomatik serbest bırakıldı."}'::jsonb,
                    completed_at=NOW(),
                    progress = COALESCE(progress, '[]'::jsonb) ||
                      jsonb_build_array(jsonb_build_object(
                        'stage','failed',
                        'message','Laptop görev worker bağlantısı kesildi; sonraki görevler serbest bırakıldı.',
                        'percent',NULL,
                        'at',EXTRACT(EPOCH FROM NOW())
                      ))
                WHERE user_id=$1 AND target=$2 AND command='agent_task'
                  AND status='delivered'
                  AND delivered_at <= NOW() - INTERVAL '20 seconds'
                """,
                request["user_id"], target,
            )
            rows = await conn.fetch(
                """
                WITH picked_controls AS (
                  SELECT id FROM device_commands d
                  WHERE d.user_id=$1 AND d.target=$2 AND d.status='queued'
                    AND d.command <> 'agent_task'
                    AND d.created_at > NOW() - INTERVAL '24 hours'
                    AND COALESCE(d.run_after, d.created_at) <= NOW()
                  ORDER BY d.id ASC
                  LIMIT 19
                  FOR UPDATE SKIP LOCKED
                ),
                picked_agent AS (
                  SELECT id FROM device_commands d
                  WHERE d.user_id=$1 AND d.target=$2 AND d.status='queued'
                    AND d.command='agent_task'
                    AND d.created_at > NOW() - INTERVAL '24 hours'
                    AND COALESCE(d.run_after, d.created_at) <= NOW()
                    AND NOT EXISTS (
                      SELECT 1 FROM device_commands active
                      WHERE active.user_id=d.user_id
                        AND active.target=d.target
                        AND active.command='agent_task'
                        AND active.status='delivered'
                        AND active.delivered_at > NOW() - INTERVAL '20 seconds'
                    )
                  ORDER BY d.id ASC
                  LIMIT 1
                  FOR UPDATE SKIP LOCKED
                ),
                picked AS (
                  SELECT id FROM picked_controls
                  UNION ALL
                  SELECT id FROM picked_agent
                )
                UPDATE device_commands d
                SET status='delivered',
                    delivered_at=NOW(),
                    progress = CASE
                      WHEN d.command='agent_task' THEN COALESCE(d.progress, '[]'::jsonb) ||
                        jsonb_build_array(jsonb_build_object(
                          'stage','claimed',
                          'message','Laptop ULTRON görevi aldı.',
                          'percent',5,
                          'at',EXTRACT(EPOCH FROM NOW())
                        ))
                      ELSE COALESCE(d.progress, '[]'::jsonb)
                    END
                FROM picked
                WHERE d.id=picked.id
                RETURNING d.id,d.target,d.command,d.payload,d.source_device,d.progress,d.checkpoint,d.retry_count,d.max_retries,d.created_at
                """,
                request["user_id"], target,
            )
    commands = []
    for row in rows:
        item = dict(row)
        payload = item.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        item["payload"] = payload if isinstance(payload, dict) else {}
        commands.append(item)
    return web.json_response({"commands": commands}, dumps=_json_dumps)


async def complete_device_command(request: web.Request) -> web.Response:
    try:
        command_id = int(request.match_info["id"])
    except Exception:
        raise web.HTTPBadRequest(text=json.dumps({"error": "invalid_command_id"}), content_type="application/json")

    body = await request.json()
    status = str(body.get("status", "completed")).strip().lower()
    if status not in {"completed", "failed"}:
        raise web.HTTPBadRequest(text=json.dumps({"error": "invalid_status"}), content_type="application/json")
    result = body.get("result", {})
    if isinstance(result, str):
        result = {"message": result}
    if not isinstance(result, dict):
        result = {}
    retryable = bool(result.get("retryable", False))
    try:
        retry_after_seconds = max(10, min(900, int(result.get("retry_after_seconds", 30) or 30)))
    except Exception:
        retry_after_seconds = 30

    auth_kind = request.get("auth_kind", "")
    expected_target = "desktop" if auth_kind == "device" else "phone"

    current = await request.app["db"].fetchrow(
        "SELECT retry_count,max_retries FROM device_commands WHERE id=$1 AND user_id=$2 AND target=$3",
        command_id, request["user_id"], expected_target,
    )
    if not current:
        raise web.HTTPNotFound(text=json.dumps({"error": "command_not_found"}), content_type="application/json")

    should_retry = (
        expected_target == "desktop"
        and status == "failed"
        and retryable
        and int(current["retry_count"] or 0) < int(current["max_retries"] or 0)
    )

    if should_retry:
        row = await request.app["db"].fetchrow(
            """
            UPDATE device_commands
            SET status='queued',
                result=$1::jsonb,
                retry_count=retry_count+1,
                delivered_at=NULL,
                completed_at=NULL,
                run_after=NOW()+($2::int * INTERVAL '1 second'),
                progress = COALESCE(progress, '[]'::jsonb) ||
                  jsonb_build_array(jsonb_build_object(
                    'stage','retry',
                    'message',COALESCE(NULLIF(($1::jsonb->>'message'),''),'Geçici hata sonrası yeniden denenecek.'),
                    'percent',NULL,
                    'at',EXTRACT(EPOCH FROM NOW())
                  ))
            WHERE id=$3 AND user_id=$4 AND target=$5
            RETURNING id,target,command,status,result,progress,retry_count,max_retries,run_after,created_at,delivered_at,completed_at
            """,
            json.dumps(result), retry_after_seconds, command_id, request["user_id"], expected_target,
        )
    else:
        row = await request.app["db"].fetchrow(
            """
            UPDATE device_commands
            SET status=$1,
                result=$2::jsonb,
                completed_at=NOW(),
                progress = COALESCE(progress, '[]'::jsonb) ||
                  jsonb_build_array(jsonb_build_object(
                    'stage', CASE WHEN $1='completed' THEN 'completed' ELSE 'failed' END,
                    'message', COALESCE(NULLIF(($2::jsonb->>'message'),''), CASE WHEN $1='completed' THEN 'Görev tamamlandı.' ELSE 'Görev başarısız oldu.' END),
                    'percent', CASE WHEN $1='completed' THEN 100 ELSE NULL END,
                    'at', EXTRACT(EPOCH FROM NOW())
                  ))
            WHERE id=$3 AND user_id=$4 AND target=$5
            RETURNING id,target,command,status,result,progress,retry_count,max_retries,run_after,created_at,delivered_at,completed_at
            """,
            status, json.dumps(result), command_id, request["user_id"], expected_target,
        )
    if not row:
        raise web.HTTPNotFound(text=json.dumps({"error": "command_not_found"}), content_type="application/json")
    return web.json_response({"ok": True, "command": dict(row)}, dumps=_json_dumps)


async def cancel_device_command(request: web.Request) -> web.Response:
    try:
        command_id = int(request.match_info["id"])
    except Exception:
        raise web.HTTPBadRequest(
            text=json.dumps({"error": "invalid_command_id"}),
            content_type="application/json",
        )

    auth_kind = request.get("auth_kind", "")
    expected_target = "desktop" if auth_kind == "web" else "phone"
    row = await request.app["db"].fetchrow(
        """
        UPDATE device_commands
        SET status='cancelled',
            result='{"message":"Görev kullanıcı tarafından iptal edildi."}'::jsonb,
            completed_at=NOW()
        WHERE id=$1 AND user_id=$2 AND target=$3 AND status='queued'
        RETURNING id,target,command,status,result,created_at,completed_at
        """,
        command_id, request["user_id"], expected_target,
    )
    if not row:
        raise web.HTTPConflict(
            text=json.dumps({"error": "command_not_cancellable"}),
            content_type="application/json",
        )
    return web.json_response({"ok": True, "command": dict(row)}, dumps=_json_dumps)


async def append_device_command_progress(request: web.Request) -> web.Response:
    try:
        command_id = int(request.match_info["id"])
    except Exception:
        raise web.HTTPBadRequest(
            text=json.dumps({"error": "invalid_command_id"}),
            content_type="application/json",
        )

    if request.get("auth_kind", "") != "device":
        raise web.HTTPForbidden(
            text=json.dumps({"error": "device_auth_required"}),
            content_type="application/json",
        )

    body = await request.json()
    stage = str(body.get("stage", "")).strip()[:80]
    message = str(body.get("message", "")).strip()[:2000]
    percent = body.get("percent")
    try:
        percent = None if percent is None else max(0, min(100, int(percent)))
    except Exception:
        percent = None
    if not stage and not message:
        raise web.HTTPBadRequest(
            text=json.dumps({"error": "stage_or_message_required"}),
            content_type="application/json",
        )

    if stage == "lease":
        row = await request.app["db"].fetchrow(
            """
            UPDATE device_commands
            SET delivered_at=NOW()
            WHERE id=$1 AND user_id=$2 AND target='desktop'
              AND status='delivered'
            RETURNING id,status,delivered_at
            """,
            command_id,
            request["user_id"],
        )
        if not row:
            raise web.HTTPNotFound(
                text=json.dumps({"error": "command_not_active"}),
                content_type="application/json",
            )
        return web.json_response({"ok": True, "command": dict(row)}, dumps=_json_dumps)

    entry = {
        "stage": stage or "progress",
        "message": message,
        "percent": percent,
        "at": time.time(),
    }
    row = await request.app["db"].fetchrow(
        """
        UPDATE device_commands
        SET progress = COALESCE(progress, '[]'::jsonb) || $1::jsonb,
            delivered_at = CASE WHEN status='delivered' THEN NOW() ELSE delivered_at END
        WHERE id=$2 AND user_id=$3 AND target='desktop'
          AND status IN ('delivered','completed','failed')
        RETURNING id,status,progress
        """,
        json.dumps([entry], ensure_ascii=False),
        command_id,
        request["user_id"],
    )
    if not row:
        raise web.HTTPNotFound(
            text=json.dumps({"error": "command_not_found"}),
            content_type="application/json",
        )
    return web.json_response({"ok": True, "command": dict(row)}, dumps=_json_dumps)


async def save_device_command_checkpoint(request: web.Request) -> web.Response:
    try:
        command_id = int(request.match_info["id"])
    except Exception:
        raise web.HTTPBadRequest(
            text=json.dumps({"error": "invalid_command_id"}),
            content_type="application/json",
        )

    if request.get("auth_kind", "") != "device":
        raise web.HTTPForbidden(
            text=json.dumps({"error": "device_auth_required"}),
            content_type="application/json",
        )

    body = await request.json()
    try:
        step_index = max(0, min(99, int(body.get("step_index", 0) or 0)))
    except Exception:
        step_index = 0
    state = body.get("state", {})
    if not isinstance(state, dict):
        state = {}
    note = str(body.get("note", "")).strip()[:2000]
    checkpoint = {
        "step_index": step_index,
        "state": state,
        "note": note,
        "updated_at": time.time(),
    }
    row = await request.app["db"].fetchrow(
        """
        UPDATE device_commands
        SET checkpoint=$1::jsonb,
            progress=COALESCE(progress,'[]'::jsonb) ||
              jsonb_build_array(jsonb_build_object(
                'stage','checkpoint',
                'message',COALESCE(NULLIF($2,''),'Görev kontrol noktası kaydedildi.'),
                'percent',NULL,
                'step_index',$3,
                'at',EXTRACT(EPOCH FROM NOW())
              ))
        WHERE id=$4 AND user_id=$5 AND target='desktop'
          AND status IN ('delivered','queued')
        RETURNING id,status,checkpoint,progress
        """,
        json.dumps(checkpoint, ensure_ascii=False),
        note,
        step_index,
        command_id,
        request["user_id"],
    )
    if not row:
        raise web.HTTPNotFound(
            text=json.dumps({"error": "command_not_found"}),
            content_type="application/json",
        )
    return web.json_response({"ok": True, "command": dict(row)}, dumps=_json_dumps)


async def recent_device_commands(request: web.Request) -> web.Response:
    auth_kind = request.get("auth_kind", "")
    target = "desktop" if auth_kind == "web" else "phone"
    limit = min(max(int(request.query.get("limit", "30")), 1), 100)
    await request.app["db"].execute(
        """
        UPDATE device_commands
        SET status='expired',
            result='{"message":"Görev 24 saat içinde teslim alınmadığı için süresi doldu."}'::jsonb,
            completed_at=NOW()
        WHERE user_id=$1 AND target=$2 AND status='queued'
          AND created_at <= NOW() - INTERVAL '24 hours'
        """,
        request["user_id"], target,
    )
    rows = await request.app["db"].fetch(
        """
        SELECT id,target,command,payload,source_device,status,result,progress,checkpoint,retry_count,max_retries,run_after,created_at,delivered_at,completed_at
        FROM device_commands
        WHERE user_id=$1 AND target=$2
        ORDER BY id DESC LIMIT $3
        """,
        request["user_id"], target, limit,
    )
    items = []
    for row in rows:
        item = dict(row)
        for key in ("payload", "result", "progress", "checkpoint"):
            value = item.get(key, {})
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except Exception:
                    value = {}
            if key == "progress":
                item[key] = value if isinstance(value, list) else []
            else:
                item[key] = value if isinstance(value, dict) else {}
        items.append(item)
    return web.json_response({"commands": items}, dumps=_json_dumps)


async def device_presence_heartbeat(request: web.Request) -> web.Response:
    body = await request.json()
    state = body.get("state", {})
    if not isinstance(state, dict):
        state = {}
    auth_kind = request.get("auth_kind", "")
    device = "desktop" if auth_kind == "device" else "phone"
    row = await request.app["db"].fetchrow(
        """
        INSERT INTO device_presence(user_id,device,state,last_seen)
        VALUES($1,$2,$3::jsonb,NOW())
        ON CONFLICT(user_id,device) DO UPDATE
        SET state=EXCLUDED.state,last_seen=NOW()
        RETURNING device,state,last_seen
        """,
        request["user_id"], device, json.dumps(state),
    )
    return web.json_response({"ok": True, "presence": dict(row)}, dumps=_json_dumps)


async def device_presence(request: web.Request) -> web.Response:
    rows = await request.app["db"].fetch(
        """
        SELECT device,state,last_seen,
               (last_seen > NOW() - INTERVAL '15 seconds') AS online
        FROM device_presence
        WHERE user_id=$1
        ORDER BY device
        """,
        request["user_id"],
    )
    items = []
    for row in rows:
        item = dict(row)
        state = item.get("state", {})
        if isinstance(state, str):
            try:
                state = json.loads(state)
            except Exception:
                state = {}
        item["state"] = state if isinstance(state, dict) else {}
        items.append(item)
    return web.json_response({"devices": items}, dumps=_json_dumps)


async def recent_live_errors(request: web.Request) -> web.Response:
    """Authenticated diagnostics for the phone Gemini Live bridge."""
    limit = min(max(int(request.query.get("limit", "8")), 1), 20)
    rows = await request.app["db"].fetch(
        """
        SELECT detail,device_id,created_at
        FROM events
        WHERE user_id=$1 AND event_type='gemini_live_error'
        ORDER BY id DESC
        LIMIT $2
        """,
        request["user_id"], limit,
    )
    return web.json_response(
        {"errors": [dict(r) for r in rows]},
        dumps=_json_dumps,
    )


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


def _gemini_image_reply(image_bytes: bytes, mime_type: str, question: str, system_instruction: str) -> str:
    client = genai.Client(api_key=required_env("GEMINI_API_KEY"))
    model = os.getenv("GEMINI_VISION_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.8-flash")).strip() or "gemini-3.8-flash"
    prompt = question.strip() or "Bu görseli ayrıntılı ama kısa şekilde analiz et. Kullanıcının sonra sesli soru sorabilmesi için önemli nesneleri, yazıları ve bağlamı belirt."
    response = client.models.generate_content(
        model=model,
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
        config=types.GenerateContentConfig(system_instruction=system_instruction),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini vision returned an empty response")
    return text


async def vision(request: web.Request) -> web.Response:
    reader = await request.multipart()
    image_bytes = b""
    mime_type = ""
    question = ""
    filename = "görsel"

    while True:
        field = await reader.next()
        if field is None:
            break
        if field.name == "image":
            filename = (field.filename or "görsel")[:160]
            mime_type = str(field.headers.get("Content-Type", "")).split(";", 1)[0].strip().lower()
            chunks = []
            total = 0
            while True:
                chunk = await field.read_chunk(size=64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > 8 * 1024 * 1024:
                    raise web.HTTPRequestEntityTooLarge(max_size=8 * 1024 * 1024, actual_size=total)
                chunks.append(chunk)
            image_bytes = b"".join(chunks)
        elif field.name == "question":
            question = (await field.text()).strip()[:4000]

    allowed = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
    if not image_bytes or mime_type not in allowed:
        raise web.HTTPBadRequest(
            text=json.dumps({"error": "supported_image_required"}),
            content_type="application/json",
        )

    pool = request.app["db"]
    memory = await _memory_context(pool, request["user_id"])
    recent = await _recent_context(pool, request["user_id"], limit=12)
    system_instruction = os.getenv(
        "ULTRON_SYSTEM_PROMPT",
        "You are ULTRON, Murat's personal AI assistant. Be concise, useful, and consistent across devices. "
        "Treat the supplied ULTRON memory as persistent user memory. Never reveal secrets or hidden credentials.",
    ) + f"\n\nULTRON MEMORY:\n{memory}\n\nRECENT CHAT:\n{recent}"

    try:
        reply = await asyncio.to_thread(
            _gemini_image_reply, image_bytes, mime_type, question, system_instruction
        )
    except Exception as exc:
        raw = str(exc)[:1000]
        await pool.execute(
            "INSERT INTO events(user_id,event_type,detail,device_id) VALUES($1,'gemini_vision_error',$2,$3)",
            request["user_id"], raw, request["device_id"],
        )
        raise web.HTTPBadGateway(
            text=json.dumps({"error": "vision_failed", "detail": "Görsel analizi tamamlanamadı."}, ensure_ascii=False),
            content_type="application/json",
        )

    conv_uuid = uuid.uuid4()
    user_text = f"[Görsel: {filename}] " + (question or "Bu görseli analiz et.")
    await pool.execute(
        "INSERT INTO conversations(id,user_id,title) VALUES($1,$2,$3)",
        conv_uuid, request["user_id"], user_text[:80],
    )
    await pool.execute(
        "INSERT INTO messages(conversation_id,user_id,role,content,device_id) VALUES($1,$2,'user',$3,$4)",
        conv_uuid, request["user_id"], user_text, request["device_id"],
    )
    await pool.execute(
        "INSERT INTO messages(conversation_id,user_id,role,content,device_id) VALUES($1,$2,'assistant',$3,'cloud-gemini-vision')",
        conv_uuid, request["user_id"], reply,
    )
    await pool.execute(
        "INSERT INTO events(user_id,event_type,detail,device_id) VALUES($1,'phone_image_context',$2,$3)",
        request["user_id"], reply[:12000], request["device_id"],
    )
    return web.json_response({
        "conversation_id": str(conv_uuid),
        "reply": reply,
        "filename": filename,
        "mime_type": mime_type,
    })


def _gemini_pdf_reply(pdf_bytes: bytes, question: str, system_instruction: str) -> str:
    client = genai.Client(api_key=required_env("GEMINI_API_KEY"))
    model = os.getenv("GEMINI_DOCUMENT_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.8-flash")).strip() or "gemini-3.8-flash"
    prompt = question.strip() or (
        "Bu PDF'yi analiz et. Önce kısa bir özet ver; ardından önemli başlıkları, tarihleri, sayıları, "
        "gereken eylemleri ve dikkat edilmesi gereken noktaları belirt. Sonraki sesli sorular için bağlamı koru."
    )
    response = client.models.generate_content(
        model=model,
        contents=[
            prompt,
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        ],
        config=types.GenerateContentConfig(system_instruction=system_instruction),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini document returned an empty response")
    return text


async def document(request: web.Request) -> web.Response:
    reader = await request.multipart()
    pdf_bytes = b""
    question = ""
    filename = "belge.pdf"

    while True:
        field = await reader.next()
        if field is None:
            break
        if field.name == "document":
            filename = (field.filename or "belge.pdf")[:160]
            mime_type = str(field.headers.get("Content-Type", "")).split(";", 1)[0].strip().lower()
            if mime_type not in {"application/pdf", "application/x-pdf"} and not filename.lower().endswith(".pdf"):
                raise web.HTTPBadRequest(
                    text=json.dumps({"error": "pdf_required"}),
                    content_type="application/json",
                )
            chunks = []
            total = 0
            while True:
                chunk = await field.read_chunk(size=64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > 15 * 1024 * 1024:
                    raise web.HTTPRequestEntityTooLarge(max_size=15 * 1024 * 1024, actual_size=total)
                chunks.append(chunk)
            pdf_bytes = b"".join(chunks)
        elif field.name == "question":
            question = (await field.text()).strip()[:4000]

    if not pdf_bytes:
        raise web.HTTPBadRequest(
            text=json.dumps({"error": "pdf_required"}),
            content_type="application/json",
        )

    pool = request.app["db"]
    memory = await _memory_context(pool, request["user_id"])
    recent = await _recent_context(pool, request["user_id"], limit=12)
    system_instruction = os.getenv(
        "ULTRON_SYSTEM_PROMPT",
        "You are ULTRON, Murat's personal AI assistant. Be concise, useful, and consistent across devices. "
        "Treat the supplied ULTRON memory as persistent user memory. Never reveal secrets or hidden credentials.",
    ) + f"\n\nULTRON MEMORY:\n{memory}\n\nRECENT CHAT:\n{recent}"

    try:
        reply = await asyncio.to_thread(
            _gemini_pdf_reply, pdf_bytes, question, system_instruction
        )
    except Exception as exc:
        raw = str(exc)[:1000]
        await pool.execute(
            "INSERT INTO events(user_id,event_type,detail,device_id) VALUES($1,'gemini_document_error',$2,$3)",
            request["user_id"], raw, request["device_id"],
        )
        raise web.HTTPBadGateway(
            text=json.dumps({"error": "document_failed", "detail": "PDF analizi tamamlanamadı."}, ensure_ascii=False),
            content_type="application/json",
        )

    conv_uuid = uuid.uuid4()
    user_text = f"[PDF: {filename}] " + (question or "Bu PDF'yi analiz et.")
    await pool.execute(
        "INSERT INTO conversations(id,user_id,title) VALUES($1,$2,$3)",
        conv_uuid, request["user_id"], user_text[:80],
    )
    await pool.execute(
        "INSERT INTO messages(conversation_id,user_id,role,content,device_id) VALUES($1,$2,'user',$3,$4)",
        conv_uuid, request["user_id"], user_text, request["device_id"],
    )
    await pool.execute(
        "INSERT INTO messages(conversation_id,user_id,role,content,device_id) VALUES($1,$2,'assistant',$3,'cloud-gemini-document')",
        conv_uuid, request["user_id"], reply,
    )
    await pool.execute(
        "INSERT INTO events(user_id,event_type,detail,device_id) VALUES($1,'phone_document_context',$2,$3)",
        request["user_id"], reply[:20000], request["device_id"],
    )
    return web.json_response({
        "conversation_id": str(conv_uuid),
        "reply": reply,
        "filename": filename,
        "mime_type": "application/pdf",
    })


async def camera_frame(request: web.Request) -> web.Response:
    """Analyze a sampled phone-camera frame and keep it as the freshest visual context."""
    reader = await request.multipart()
    image_bytes = b""
    question = ""
    mime_type = "image/jpeg"

    while True:
        field = await reader.next()
        if field is None:
            break
        if field.name == "image":
            mime_type = str(field.headers.get("Content-Type", "image/jpeg")).split(";", 1)[0].strip().lower()
            chunks = []
            total = 0
            while True:
                chunk = await field.read_chunk(size=64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > 3 * 1024 * 1024:
                    raise web.HTTPRequestEntityTooLarge(max_size=3 * 1024 * 1024, actual_size=total)
                chunks.append(chunk)
            image_bytes = b"".join(chunks)
        elif field.name == "question":
            question = (await field.text()).strip()[:2000]

    if not image_bytes or mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise web.HTTPBadRequest(
            text=json.dumps({"error": "camera_frame_required"}),
            content_type="application/json",
        )

    pool = request.app["db"]
    memory = await _memory_context(pool, request["user_id"])
    system_instruction = os.getenv(
        "ULTRON_SYSTEM_PROMPT",
        "You are ULTRON, Murat's personal AI assistant. Be concise, useful, and consistent across devices. "
        "Treat the supplied ULTRON memory as persistent user memory. Never reveal secrets or hidden credentials.",
    ) + f"\n\nULTRON MEMORY:\n{memory}"

    camera_prompt = question or (
        "Bu telefon kamerasından alınmış canlı bir kare. Kullanıcı birazdan 'şuna bak', 'ne görüyorsun' "
        "veya benzeri bir soru sorabilir. Görseldeki önemli nesneleri, kişisel veri içermeyen görünür yazıları, "
        "mekânı ve dikkat çekici değişiklikleri kısa ve somut şekilde açıkla."
    )
    try:
        reply = await asyncio.to_thread(
            _gemini_image_reply, image_bytes, mime_type, camera_prompt, system_instruction
        )
    except Exception as exc:
        await pool.execute(
            "INSERT INTO events(user_id,event_type,detail,device_id) VALUES($1,'gemini_camera_error',$2,$3)",
            request["user_id"], str(exc)[:1000], request["device_id"],
        )
        raise web.HTTPBadGateway(
            text=json.dumps({"error": "camera_failed", "detail": "Canlı kamera analizi tamamlanamadı."}, ensure_ascii=False),
            content_type="application/json",
        )

    await pool.execute(
        "INSERT INTO events(user_id,event_type,detail,device_id) VALUES($1,'phone_camera_context',$2,$3)",
        request["user_id"], reply[:12000], request["device_id"],
    )
    return web.json_response({"ok": True, "reply": reply})


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



async def live_voice(request: web.Request) -> web.WebSocketResponse:
    """Authenticated phone <-> Gemini Live audio bridge.

    The Gemini API key never reaches the browser. The phone sends 16 kHz PCM16
    frames over this same-origin WebSocket; Cloud forwards them to Gemini Live
    and returns Gemini's native 24 kHz PCM plus transcript events.
    """
    ws = web.WebSocketResponse(heartbeat=25, receive_timeout=180)
    await ws.prepare(request)

    pool = request.app["db"]
    user_id = request["user_id"]
    device_id = request["device_id"]
    raw_voice_session = str(request.query.get("session_id", "")).strip()
    try:
        conv_uuid = uuid.UUID(raw_voice_session) if raw_voice_session else uuid.uuid4()
    except (ValueError, AttributeError):
        conv_uuid = uuid.uuid4()
    memory = await _memory_context(pool, user_id)
    recent = await _recent_context(pool, user_id, limit=18)
    base_prompt = os.getenv(
        "ULTRON_SYSTEM_PROMPT",
        "You are ULTRON, Murat's personal AI assistant. Be concise, useful, and consistent across devices. "
        "Treat the supplied ULTRON memory as persistent user memory. Never reveal secrets or hidden credentials.",
    )
    system_instruction = (
        base_prompt
        + "\n\nYou are speaking through the user's phone using Gemini Live native audio. "
          "Speak naturally in the same language as the user. Keep replies conversational and usually brief. "
          "Use save_memory whenever the user explicitly asks you to remember something or reveals a stable personal fact worth remembering. "
          "Use recall_memory when current persistent memory is needed instead of guessing from stale session context. "
          "Use get_latest_image_context whenever the user refers to the photo/image they just sent. "
          "Use get_latest_document_context whenever the user refers to the PDF/document they just sent. "
          "Use control_phone_ui when the user asks to control the current phone surface. Supported actions include ULTRON views plus safe app intents such as browser/search/maps/call composer. "
          "For iPhone system/app control, never claim unrestricted device access: iOS only allows actions exposed by browser URL/deep-link intents or explicit Shortcuts. "
          "Use run_ios_shortcut when the user asks for an iPhone action that should be delegated to Apple Shortcuts. Prefer the shortcut name ULTRON Bridge unless the user explicitly names another shortcut. "
          "For opening apps such as YouTube, Spotify, WhatsApp, Instagram, Chrome, Maps, Messages, Mail, or FaceTime, ALWAYS use control_phone_ui and NEVER use Apple Shortcuts. "
          "If the user names content to find inside YouTube or Spotify, use youtube_search or spotify_search instead of merely opening the app. "
          "If the user asks to prepare a WhatsApp message, use whatsapp_message. "
          "For direct phone/app actions, perform the tool call immediately and do not add a conversational confirmation afterward unless the action fails. "
          "Use run_ios_action only for iPhone system settings that truly require Apple Shortcuts: set_focus, set_volume, set_brightness, bluetooth, wifi, and compose_message. "
          "You are ONE ULTRON across the phone and paired Windows laptop, not two separate assistants. "
          "The paired laptop's local agent is an extension of your own capability set. Whenever the user asks for something the desktop ULTRON can do, use send_laptop_task automatically even if the user does not explicitly say 'on the laptop'. "
          "Desktop capabilities include file/folder operations, Windows and desktop control, system status/settings, opening and controlling desktop apps, browser automation, coding/development-agent work, screen inspection, local file processing, web/news/weather/flight lookups, reminders, messaging, media/video/YouTube actions, monitoring, dynamic Center Stage control, interactive hologram creation/editing, multi-object 3D Scene Lab composition, natural object-name selection/movement/rotation/scaling, multi-select and named-group batch editing, align/distribute tools, line/grid/radial arrays, parent-child Scene Graph hierarchy, reusable camera bookmarks and timeline-authored cinematic camera keyframes, live drop/launch/zero-G/float physics simulation, holographic distance measurements, scene diagnostics and live collision-risk visualization, duplicate/undo/redo, animated object motion, multi-object eased timeline/keyframe animation, persistent manual and cinematic camera paths, object-attached HUD/data cards, holographic object links, Scene Director modes, named in-app scene projects, persistent imported GLB Asset Library with reuse/delete and embedded animation control, audio-reactive particles, themes/HUD labels, exploded views, camera/layout control, scene save/reopen, screenshot capture, real live Three.js scene video recording and short local animation-video rendering/preview, converting the current hologram or 3D scene into a video, whole-system/world awareness, self-diagnostics, adaptive screen awareness, smart-home/IoT scenes, presence, backups, long-running supervisor tasks, research/knowledge retrieval, persistent goals, prediction, decision support, dry-run simulation, and any other action/plugin available to the desktop ULTRON. "
          "Never answer 'I cannot do that from the phone' merely because the capability lives on the laptop; delegate it through send_laptop_task. "
          "If the user explicitly says iPhone/phone, use phone tools. If the user explicitly says laptop/computer/Windows, use send_laptop_task. If no device is named, use phone tools for clearly iPhone-local intents and use the desktop agent for desktop/tool/file/system/automation tasks. "
          "Use get_laptop_status when the user asks whether the laptop is online, busy, muted, or what it is doing. "
          "Use get_latest_laptop_task when the user asks what happened to the last laptop task, whether it finished, or for its result. "
          "Use cancel_laptop_task when the user explicitly asks to cancel the latest queued laptop task. "
          "send_laptop_task may schedule a task for later by setting delay_minutes. "
          "For complex laptop tasks, include a short ordered plan of 2-7 concrete steps so the desktop agent can report progress and resume from checkpoints. "
          "For an online immediate desktop task, send_laptop_task returns quickly so the phone's Gemini Live audio session never blocks. The browser receives the eventual desktop result independently and announces it; you must not wait for or inject another result turn. "
          "After send_laptop_task returns accepted/running, only acknowledge briefly that the task was sent or is being processed; NEVER claim completion yet. "
          "Do not pretend a laptop action is completed until the desktop agent reports completion; accurately say whether it completed, failed, was scheduled, or remains queued. "
          "The phone is in always-listening mode while the microphone session is active; no wake word is required. "
          "When the user gives a direct phone/app command, execute the appropriate tool immediately before speaking. "
          "Do not ask follow-up closing questions such as 'Başka bir emriniz var mı?' after completing a command. "
          "For successful direct actions, keep any spoken confirmation extremely short, for example 'Açıyorum.' or say nothing beyond the result."
        + f"\n\nULTRON MEMORY:\n{memory}\n\nRECENT SHARED CHAT:\n{recent}"
    )
    model = os.getenv("GEMINI_LIVE_MODEL", "models/gemini-3.1-flash-live-preview").strip()
    voice = os.getenv("ULTRON_LIVE_VOICE", "Charon").strip() or "Charon"
    try:
        desktop_state = await pool.fetchval(
            "SELECT state FROM device_presence WHERE user_id=$1 AND device='desktop'",
            user_id,
        )
        if isinstance(desktop_state, str):
            desktop_state = json.loads(desktop_state)
        if isinstance(desktop_state, dict):
            saved_voice = str(desktop_state.get("voice", "")).strip()
            if saved_voice:
                voice = saved_voice
    except Exception:
        pass

    existing_owner = await pool.fetchval(
        "SELECT user_id FROM conversations WHERE id=$1",
        conv_uuid,
    )
    if existing_owner is not None and existing_owner != user_id:
        conv_uuid = uuid.uuid4()

    await pool.execute(
        """
        INSERT INTO conversations(id,user_id,title)
        VALUES($1,$2,'Telefon sesli ULTRON')
        ON CONFLICT(id) DO UPDATE SET updated_at=NOW()
        """,
        conv_uuid, user_id,
    )

    client = genai.Client(
        api_key=required_env("GEMINI_API_KEY"),
        http_options={"api_version": "v1beta"},
    )
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        input_audio_transcription={},
        output_audio_transcription={},
        system_instruction=system_instruction,
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                silence_duration_ms=720,
                prefix_padding_ms=180,
                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
            )
        ),
        context_window_compression=types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow(),
        ),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            )
        ),
        tools=[{"function_declarations": [
            {
                "name": "save_memory",
                "description": "Save or update a stable user fact in the shared ULTRON Cloud memory. Use when the user asks to remember something or shares an important persistent fact.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "key": {"type": "STRING", "description": "Short stable key, for example favorite_color or school."},
                        "value": {"type": "STRING", "description": "The exact fact to remember, preserving the user's wording when practical."},
                        "category": {"type": "STRING", "description": "PROFILE, PREFERENCE, PROJECT, RELATIONSHIP, WISH, NOTE, FACT, IMPORTANT, DEVICE, or TASK."}
                    },
                    "required": ["key", "value"]
                }
            },
            {
                "name": "recall_memory",
                "description": "Search the latest shared ULTRON Cloud memory for facts relevant to the user's question.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "Words or topic to search for in persistent memory."}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_latest_image_context",
                "description": "Get the analysis of the most recent photo or image uploaded from the phone. Use when the user says this photo, this image, what do you see, or asks a follow-up about the uploaded image.",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "get_latest_document_context",
                "description": "Get the analysis of the most recent PDF uploaded from the phone. Use when the user says this PDF, this document, this file, or asks a follow-up about the uploaded PDF.",
                "parameters": {"type": "OBJECT", "properties": {}}
            }
,
            {
                "name": "control_phone_ui",
                "description": "Control the current ULTRON phone interface or launch a safe iPhone intent without Apple Shortcuts. Actions: chat, memory, remote, camera, vibrate, scroll_top, browser, search_web, maps, call, sms, email, facetime, open_app, youtube_search, spotify_search, whatsapp_message.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {"type": "STRING", "description": "One of chat, memory, remote, camera, vibrate, scroll_top, browser, search_web, maps, call, sms, email, facetime, open_app, youtube_search, spotify_search, whatsapp_message."},
                        "query": {"type": "STRING", "description": "App name, search text, destination, phone number, email address, or message text depending on action."}
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "send_laptop_task",
                "description": "Delegate any task that the paired Windows desktop ULTRON can perform. This is the phone voice assistant's gateway to the full desktop action/plugin/tool set; use it automatically for desktop-capable tasks, not only when the user literally says laptop.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "task": {"type": "STRING", "description": "The exact desktop task requested by the user, concise but complete."},
                        "delay_minutes": {"type": "INTEGER", "description": "Optional delay before the laptop may claim this task. Use 0 for immediately."},
                        "plan": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Optional ordered 2-7 step plan for complex tasks."}
                    },
                    "required": ["task"]
                }
            },
            {
                "name": "get_laptop_status",
                "description": "Read the paired laptop's current ULTRON presence/status.",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "get_latest_laptop_task",
                "description": "Get the latest desktop ULTRON agent task status, progress, and result.",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "cancel_laptop_task",
                "description": "Cancel the latest queued desktop ULTRON agent task. Only queued tasks can be cancelled.",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "run_ios_shortcut",
                "description": "Run an Apple Shortcut on the current iPhone. Use ULTRON Bridge by default and pass the requested phone action as text input.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "shortcut_name": {"type": "STRING", "description": "Shortcut name. Default ULTRON Bridge."},
                        "input": {"type": "STRING", "description": "Text command or payload to pass into the shortcut."}
                    },
                    "required": ["input"]
                }
            },
            {
                "name": "run_ios_action",
                "description": "Send an iPhone system-setting automation command to ULTRON Bridge. Do NOT use for opening apps; use control_phone_ui for apps.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {"type": "STRING", "description": "One of set_focus, set_volume, set_brightness, bluetooth, wifi, compose_message."},
                        "target": {"type": "STRING", "description": "App name, focus name, contact, or on/off depending on action."},
                        "value": {"type": "STRING", "description": "Optional value such as 0-100 volume/brightness, message body, or on/off."}
                    },
                    "required": ["action"]
                }
            }
        ]}],
    )

    in_parts: list[str] = []
    out_parts: list[str] = []
    send_lock = asyncio.Lock()
    async def send_json(payload: dict[str, Any]) -> None:
        if not ws.closed:
            async with send_lock:
                await ws.send_str(json.dumps(payload, ensure_ascii=False, default=str))

    try:
        async with client.aio.live.connect(model=model, config=config) as session:
            desktop_task_watchers: set[asyncio.Task] = set()

            def _decode_json_value(value: Any, fallback: Any) -> Any:
                if isinstance(value, str):
                    try:
                        return json.loads(value)
                    except Exception:
                        return fallback
                return value if value is not None else fallback

            async def watch_desktop_task_result(command_id: int, task_text: str) -> None:
                """Watch a desktop task without blocking Gemini Live tool handling.

                The phone gets a quick outcome within five seconds. If the
                desktop is still working, the watcher keeps running and later
                sends the real final result as a second update.
                """
                deadline = time.monotonic() + 180.0
                quick_deadline = time.monotonic() + 5.0
                quick_sent = False
                last_status = ""
                last_progress_len = -1
                try:
                    while time.monotonic() < deadline and not ws.closed:
                        row = await pool.fetchrow(
                            """
                            SELECT status,result,progress,delivered_at,completed_at
                            FROM device_commands
                            WHERE id=$1 AND user_id=$2 AND target='desktop'
                            """,
                            command_id, user_id,
                        )
                        if not row:
                            return

                        status = str(row["status"] or "")
                        result = _decode_json_value(row["result"], {})
                        progress = _decode_json_value(row["progress"], [])
                        if not isinstance(result, dict):
                            result = {}
                        if not isinstance(progress, list):
                            progress = []

                        if status != last_status or len(progress) != last_progress_len:
                            last_status = status
                            last_progress_len = len(progress)
                            await send_json({
                                "type": "laptop_task_update",
                                "id": command_id,
                                "status": status,
                                "progress": progress[-4:],
                            })

                        if status in {"completed", "failed", "cancelled", "expired"}:
                            assistant_reply = str(
                                result.get("assistant_reply")
                                or result.get("message")
                                or ""
                            ).strip()
                            await send_json({
                                "type": "laptop_task_result",
                                "id": command_id,
                                "status": status,
                                "task": task_text,
                                "result": result,
                                "assistant_reply": assistant_reply,
                                "quick": not quick_sent,
                            })
                            return

                        if not quick_sent and time.monotonic() >= quick_deadline:
                            quick_sent = True
                            await send_json({
                                "type": "laptop_task_quick_status",
                                "id": command_id,
                                "status": status or "running",
                                "task": task_text,
                                "message": "Görev 5 saniye içinde tamamlanmadı; laptop ULTRON çalışmaya devam ediyor.",
                            })

                        await asyncio.sleep(0.20)

                    if not ws.closed:
                        await send_json({
                            "type": "laptop_task_update",
                            "id": command_id,
                            "status": "running",
                            "message": "Laptop görevi arka planda çalışmaya devam ediyor.",
                        })
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    if not ws.closed:
                        await send_json({
                            "type": "laptop_task_update",
                            "id": command_id,
                            "status": "watch_error",
                            "message": str(exc)[:180],
                        })

            await send_json({
                "type": "ready",
                "model": model.split("/")[-1],
                "voice": voice,
                "session_id": str(conv_uuid),
                "resumed": existing_owner == user_id,
            })

            async def browser_to_gemini() -> None:
                async for msg in ws:
                    if msg.type == web.WSMsgType.BINARY:
                        if msg.data:
                            await session.send_realtime_input(
                                audio=types.Blob(
                                    data=bytes(msg.data),
                                    mime_type="audio/pcm;rate=16000",
                                )
                            )
                    elif msg.type == web.WSMsgType.TEXT:
                        try:
                            payload = json.loads(msg.data)
                        except Exception:
                            payload = {}
                        kind = str(payload.get("type", ""))
                        if kind == "text":
                            text = str(payload.get("text", "")).strip()
                            if text:
                                await session.send_client_content(
                                    turns={"role": "user", "parts": [{"text": text}]},
                                    turn_complete=True,
                                )
                        elif kind == "close":
                            await ws.close()
                            return
                    elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.CLOSED, web.WSMsgType.ERROR):
                        return

            async def execute_live_tool(fc):
                name = str(getattr(fc, "name", "") or "")
                args = dict(getattr(fc, "args", {}) or {})
                if name == "save_memory":
                    key = str(args.get("key", "")).strip()[:120]
                    value = str(args.get("value", "")).strip()[:8000]
                    category = str(args.get("category", "FACT")).strip().upper()[:40] or "FACT"
                    if not key or not value:
                        return types.FunctionResponse(
                            id=fc.id, name=name,
                            response={"ok": False, "error": "key_and_value_required"},
                        )
                    row = await pool.fetchrow(
                        """
                        INSERT INTO memories(user_id, category, key, value, version, updated_by_device)
                        VALUES($1,$2,$3,$4,1,$5)
                        ON CONFLICT(user_id,key) DO UPDATE SET
                          category=EXCLUDED.category,
                          value=EXCLUDED.value,
                          version=memories.version+1,
                          updated_by_device=EXCLUDED.updated_by_device,
                          updated_at=NOW()
                        RETURNING category,key,value,version,updated_at
                        """,
                        user_id, category, key, value, device_id,
                    )
                    await send_json({
                        "type": "memory_saved",
                        "key": key,
                        "value": value,
                        "category": category,
                        "version": int(row["version"]),
                    })
                    return types.FunctionResponse(
                        id=fc.id, name=name,
                        response={"ok": True, "saved": {"key": key, "value": value, "category": category, "version": int(row["version"])}},
                    )

                if name == "recall_memory":
                    query = str(args.get("query", "")).strip().lower()
                    rows = await pool.fetch(
                        """
                        SELECT category,key,value,version,updated_at
                        FROM memories
                        WHERE user_id=$1
                          AND ($2='' OR LOWER(key) LIKE '%' || $2 || '%' OR LOWER(value) LIKE '%' || $2 || '%' OR LOWER(category) LIKE '%' || $2 || '%')
                        ORDER BY updated_at DESC
                        LIMIT 12
                        """,
                        user_id, query,
                    )
                    items = [
                        {"category": r["category"], "key": r["key"], "value": r["value"], "version": r["version"]}
                        for r in rows
                    ]
                    return types.FunctionResponse(
                        id=fc.id, name=name,
                        response={"ok": True, "memories": items},
                    )

                if name == "get_latest_image_context":
                    row = await pool.fetchrow(
                        """
                        SELECT detail,created_at
                        FROM events
                        WHERE user_id=$1 AND event_type IN ('phone_image_context','phone_camera_context')
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        user_id,
                    )
                    if not row:
                        return types.FunctionResponse(
                            id=fc.id, name=name,
                            response={"ok": False, "error": "no_recent_image"},
                        )
                    return types.FunctionResponse(
                        id=fc.id, name=name,
                        response={"ok": True, "analysis": row["detail"], "created_at": str(row["created_at"])},
                    )

                if name == "get_latest_document_context":
                    row = await pool.fetchrow(
                        """
                        SELECT detail,created_at
                        FROM events
                        WHERE user_id=$1 AND event_type='phone_document_context'
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        user_id,
                    )
                    if not row:
                        return types.FunctionResponse(
                            id=fc.id, name=name,
                            response={"ok": False, "error": "no_recent_document"},
                        )
                    return types.FunctionResponse(
                        id=fc.id, name=name,
                        response={"ok": True, "analysis": row["detail"], "created_at": str(row["created_at"])},
                    )

                if name == "control_phone_ui":
                    action = str(args.get("action", "")).strip().lower()
                    query = str(args.get("query", "")).strip()[:500]
                    allowed = {"chat", "memory", "remote", "camera", "vibrate", "scroll_top", "browser", "search_web", "maps", "call", "sms", "email", "facetime", "open_app", "youtube_search", "spotify_search", "whatsapp_message"}
                    if action not in allowed:
                        return types.FunctionResponse(
                            id=fc.id, name=name,
                            response={"ok": False, "error": "unsupported_action"},
                        )
                    await send_json({"type": "phone_action", "action": action, "query": query})
                    return types.FunctionResponse(
                        id=fc.id, name=name,
                        response={"ok": True, "action": action, "query": query},
                    )

                if name == "send_laptop_task":
                    task_text = str(args.get("task", "")).strip()[:4000]
                    if not task_text:
                        return types.FunctionResponse(
                            id=fc.id, name=name,
                            response={"ok": False, "error": "task_required"},
                        )
                    try:
                        delay_minutes = max(0, min(1440, int(args.get("delay_minutes", 0) or 0)))
                    except Exception:
                        delay_minutes = 0
                    raw_plan = args.get("plan", [])
                    plan = []
                    if isinstance(raw_plan, list):
                        for step in raw_plan[:7]:
                            value = str(step or "").strip()[:240]
                            if value:
                                plan.append(value)

                    online = bool(await pool.fetchval(
                        """
                        SELECT COALESCE(last_seen > NOW() - INTERVAL '15 seconds', FALSE)
                        FROM device_presence
                        WHERE user_id=$1 AND device='desktop'
                        """,
                        user_id,
                    ))
                    row = await pool.fetchrow(
                        """
                        INSERT INTO device_commands(user_id,target,command,payload,source_device,run_after)
                        VALUES($1,'desktop','agent_task',$2::jsonb,$3,NOW()+($4::int * INTERVAL '1 minute'))
                        RETURNING id,created_at,run_after
                        """,
                        user_id,
                        json.dumps({"text": task_text, "origin": "voice", "plan": plan}, ensure_ascii=False),
                        device_id,
                        delay_minutes,
                    )
                    scheduled = delay_minutes > 0
                    command_id = int(row["id"])
                    await send_json({
                        "type": "laptop_task",
                        "id": command_id,
                        "task": task_text,
                        "online": online,
                        "queued": (not online) or scheduled,
                        "scheduled": scheduled,
                        "run_after": str(row["run_after"]),
                    })

                    # Scheduled/offline work cannot finish inside this Live tool
                    # call. Return its durable queue state immediately.
                    if scheduled or not online:
                        return types.FunctionResponse(
                            id=fc.id, name=name,
                            response={
                                "ok": True,
                                "command_id": command_id,
                                "desktop_online": online,
                                "queued": True,
                                "scheduled": scheduled,
                                "run_after": str(row["run_after"]),
                                "task": task_text,
                                "origin": "voice",
                                "result_will_arrive_async": not scheduled,
                            },
                        )

                    # CRITICAL: never block the Gemini Live function call while
                    # the laptop works. Long-running function calls were causing
                    # the phone Live websocket to be torn down and reconnect.
                    # Watch completion in a background task and inject the real
                    # desktop result back into the same Live session later.
                    watcher = asyncio.create_task(
                        watch_desktop_task_result(command_id, task_text)
                    )
                    desktop_task_watchers.add(watcher)
                    watcher.add_done_callback(desktop_task_watchers.discard)

                    return types.FunctionResponse(
                        id=fc.id, name=name,
                        response={
                            "ok": True,
                            "command_id": command_id,
                            "status": "accepted",
                            "desktop_online": True,
                            "queued": False,
                            "scheduled": False,
                            "task": task_text,
                            "origin": "voice",
                            "result_will_arrive_async": True,
                            "message": "Laptop ULTRON görevi aldı. Sonuç tamamlanınca bu sesli oturuma otomatik gelecek.",
                        },
                    )

                if name == "get_laptop_status":
                    row = await pool.fetchrow(
                        """
                        SELECT state,last_seen,(last_seen > NOW() - INTERVAL '15 seconds') AS online
                        FROM device_presence
                        WHERE user_id=$1 AND device='desktop'
                        """,
                        user_id,
                    )
                    if not row:
                        return types.FunctionResponse(
                            id=fc.id, name=name,
                            response={"ok": True, "online": False, "seen": False},
                        )
                    state = row["state"]
                    if isinstance(state, str):
                        try:
                            state = json.loads(state)
                        except Exception:
                            state = {}
                    return types.FunctionResponse(
                        id=fc.id, name=name,
                        response={
                            "ok": True,
                            "online": bool(row["online"]),
                            "last_seen": str(row["last_seen"]),
                            "state": state if isinstance(state, dict) else {},
                        },
                    )

                if name == "get_latest_laptop_task":
                    row = await pool.fetchrow(
                        """
                        SELECT id,status,payload,result,progress,retry_count,max_retries,run_after,created_at,delivered_at,completed_at
                        FROM device_commands
                        WHERE user_id=$1 AND target='desktop' AND command='agent_task'
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        user_id,
                    )
                    if not row:
                        return types.FunctionResponse(
                            id=fc.id, name=name,
                            response={"ok": True, "found": False},
                        )
                    item = dict(row)
                    for key in ("payload", "result", "progress"):
                        value = item.get(key)
                        if isinstance(value, str):
                            try:
                                value = json.loads(value)
                            except Exception:
                                value = [] if key == "progress" else {}
                        item[key] = value
                    item["found"] = True
                    item["ok"] = True
                    return types.FunctionResponse(id=fc.id, name=name, response=item)

                if name == "cancel_laptop_task":
                    row = await pool.fetchrow(
                        """
                        WITH latest AS (
                          SELECT id FROM device_commands
                          WHERE user_id=$1 AND target='desktop' AND command='agent_task'
                            AND status='queued'
                          ORDER BY id DESC
                          LIMIT 1
                        )
                        UPDATE device_commands d
                        SET status='cancelled',
                            result='{"message":"Görev sesli komutla iptal edildi."}'::jsonb,
                            completed_at=NOW(),
                            progress=COALESCE(progress,'[]'::jsonb) ||
                              jsonb_build_array(jsonb_build_object(
                                'stage','cancelled',
                                'message','Görev sesli komutla iptal edildi.',
                                'percent',NULL,
                                'at',EXTRACT(EPOCH FROM NOW())
                              ))
                        FROM latest
                        WHERE d.id=latest.id
                        RETURNING d.id,d.status,d.result
                        """,
                        user_id,
                    )
                    if not row:
                        return types.FunctionResponse(
                            id=fc.id, name=name,
                            response={"ok": False, "error": "no_queued_task"},
                        )
                    await send_json({"type": "laptop_task_cancelled", "id": int(row["id"])})
                    return types.FunctionResponse(
                        id=fc.id, name=name,
                        response={"ok": True, "command_id": int(row["id"]), "status": "cancelled"},
                    )

                if name == "run_ios_shortcut":
                    shortcut_name = str(args.get("shortcut_name", "ULTRON Bridge")).strip()[:120] or "ULTRON Bridge"
                    shortcut_input = str(args.get("input", "")).strip()[:1000]
                    if not shortcut_input:
                        return types.FunctionResponse(
                            id=fc.id, name=name,
                            response={"ok": False, "error": "shortcut_input_required"},
                        )
                    await send_json({
                        "type": "ios_shortcut",
                        "shortcut_name": shortcut_name,
                        "input": shortcut_input,
                    })
                    return types.FunctionResponse(
                        id=fc.id, name=name,
                        response={
                            "ok": True,
                            "shortcut_name": shortcut_name,
                            "input": shortcut_input,
                            "note": "iOS may require Shortcuts permissions or confirmation depending on the actions inside the shortcut.",
                        },
                    )

                if name == "run_ios_action":
                    action = str(args.get("action", "")).strip().lower()
                    allowed = {"set_focus", "set_volume", "set_brightness", "bluetooth", "wifi", "compose_message"}
                    if action not in allowed:
                        return types.FunctionResponse(
                            id=fc.id, name=name,
                            response={"ok": False, "error": "unsupported_ios_action"},
                        )
                    command = {
                        "version": 1,
                        "source": "ultron",
                        "action": action,
                        "target": str(args.get("target", "")).strip()[:300],
                        "value": str(args.get("value", "")).strip()[:1200],
                    }
                    await send_json({
                        "type": "ios_action",
                        "command": command,
                    })
                    return types.FunctionResponse(
                        id=fc.id, name=name,
                        response={
                            "ok": True,
                            "shortcut_name": "ULTRON Bridge",
                            "command": command,
                            "note": "Execution depends on actions and permissions configured inside the Apple Shortcut.",
                        },
                    )

                return types.FunctionResponse(
                    id=fc.id, name=name or "unknown",
                    response={"ok": False, "error": "unknown_tool"},
                )

            async def gemini_to_browser() -> None:
                while not ws.closed:
                    got_any = False
                    async for response in session.receive():
                        got_any = True
                        if response.data and not ws.closed:
                            async with send_lock:
                                await ws.send_bytes(response.data)

                        if getattr(response, "tool_call", None):
                            fn_responses = []
                            for fc in response.tool_call.function_calls:
                                fn_responses.append(await execute_live_tool(fc))
                            if fn_responses:
                                await session.send_tool_response(function_responses=fn_responses)

                        sc = getattr(response, "server_content", None)
                        if sc is None:
                            continue
                        if getattr(sc, "interrupted", False):
                            # Gemini detected the user speaking over the answer.
                            # Drop the unfinished assistant transcript and tell
                            # the phone to stop any audio already queued locally.
                            out_parts.clear()
                            await send_json({"type": "interrupted"})
                        if sc.input_transcription and sc.input_transcription.text:
                            text = str(sc.input_transcription.text).strip()
                            if text:
                                in_parts.append(text)
                                await send_json({"type": "input_transcript", "text": text})
                        if sc.output_transcription and sc.output_transcription.text:
                            text = str(sc.output_transcription.text).strip()
                            if text:
                                out_parts.append(text)
                                await send_json({"type": "output_transcript", "text": text})
                        if sc.turn_complete:
                            full_in = " ".join(in_parts).strip()
                            full_out = " ".join(out_parts).strip()
                            in_parts.clear()
                            out_parts.clear()
                            if full_in:
                                await pool.execute(
                                    "INSERT INTO messages(conversation_id,user_id,role,content,device_id) "
                                    "VALUES($1,$2,'user',$3,$4)",
                                    conv_uuid, user_id, full_in, device_id,
                                )
                            if full_out:
                                await pool.execute(
                                    "INSERT INTO messages(conversation_id,user_id,role,content,device_id) "
                                    "VALUES($1,$2,'assistant',$3,'cloud-gemini-live')",
                                    conv_uuid, user_id, full_out,
                                )
                            if full_in or full_out:
                                await pool.execute(
                                    "UPDATE conversations SET updated_at=NOW() WHERE id=$1",
                                    conv_uuid,
                                )
                                await send_json({
                                    "type": "turn_complete",
                                    "input": full_in,
                                    "output": full_out,
                                    "conversation_id": str(conv_uuid),
                                })
                    if not got_any:
                        await asyncio.sleep(0.02)

            inbound = asyncio.create_task(browser_to_gemini())
            outbound = asyncio.create_task(gemini_to_browser())
            done, pending = await asyncio.wait(
                {inbound, outbound}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                exc = task.exception()
                if exc:
                    raise exc
            for task in list(desktop_task_watchers):
                task.cancel()
            if desktop_task_watchers:
                await asyncio.gather(*desktop_task_watchers, return_exceptions=True)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        try:
            await pool.execute(
                "INSERT INTO events(user_id,event_type,detail,device_id) "
                "VALUES($1,'gemini_live_error',$2,$3)",
                user_id, str(exc)[:1000], device_id,
            )
        except Exception:
            pass
        if not ws.closed:
            await send_json({
                "type": "error",
                "message": "Sesli ULTRON bağlantısı geçici olarak kullanılamıyor.",
                "detail": str(exc)[:160],
            })
    finally:
        if not ws.closed:
            await ws.close()
    return ws


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def build_app() -> web.Application:
    app = web.Application(middlewares=[auth_middleware], client_max_size=18 * 1024 * 1024)
    app.router.add_get("/", index)
    app.router.add_static("/static/", STATIC_DIR, show_index=False)
    app.router.add_get("/health", health)
    app.router.add_post("/api/login", login)
    app.router.add_post("/api/logout", logout)
    app.router.add_get("/api/session", session)
    app.router.add_get("/api/messages", list_messages)
    app.router.add_get("/api/debug/live-errors", recent_live_errors)
    app.router.add_post("/api/chat", chat)
    app.router.add_post("/api/vision", vision)
    app.router.add_post("/api/document", document)
    app.router.add_post("/api/camera-frame", camera_frame)
    app.router.add_get("/api/live", live_voice)
    app.router.add_post("/api/device-commands", send_device_command)
    app.router.add_post("/api/device-commands/claim", claim_device_commands)
    app.router.add_post("/api/device-commands/{id}/complete", complete_device_command)
    app.router.add_post("/api/device-commands/{id}/progress", append_device_command_progress)
    app.router.add_post("/api/device-commands/{id}/checkpoint", save_device_command_checkpoint)
    app.router.add_post("/api/device-commands/{id}/cancel", cancel_device_command)
    app.router.add_get("/api/device-commands/recent", recent_device_commands)
    app.router.add_post("/api/device-presence/heartbeat", device_presence_heartbeat)
    app.router.add_get("/api/device-presence", device_presence)
    app.router.add_get("/api/memories", list_memories)
    app.router.add_put("/api/memories", upsert_memory)
    app.router.add_delete("/api/memories/{key}", delete_memory)
    app.on_startup.append(init_db)
    app.on_cleanup.append(close_db)
    return app


if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    web.run_app(build_app(), host="0.0.0.0", port=port)