"""Free SD 1.5 via the existing paired-desktop queue; never dispatches Gemini."""

import hashlib
import json
import os
import uuid
from aiohttp import web
import image_studio as studio

SIZES = {"1:1": (512, 512), "9:16": (384, 640), "16:9": (640, 384)}


def enabled():
    return (
        studio.provider_mode() == "comfyui_local"
        and os.getenv("GOLGE_LOCAL_IMAGE_ENABLED") == "true"
    )


async def ready(conn, owner):
    return bool(
        await conn.fetchval(
            """SELECT COALESCE(last_seen>NOW()-INTERVAL '15 seconds'
        AND state->'local_image_ready'='true'::jsonb,FALSE) FROM device_presence
        WHERE user_id=$1 AND device='desktop'""",
            owner,
        )
    )


async def status(request):
    available = enabled() and await ready(request.app["db"], request["user_id"])
    return web.json_response(
        dict(
            available=available,
            provider="comfyui_local",
            requires_cost_approval=False,
            model="stable-diffusion-1.5",
            image_size="512",
            aspect_ratios=list(SIZES),
            sizes=SIZES,
            editing_available=False,
            detail=(
                "Ücretsiz yerel Stable Diffusion 1.5 hazır. Görsel laptopta üretilecek; API ücreti yok."
                if available
                else "Ücretsiz yerel üretim hazır değil: eşleşmiş laptop açık, ComfyUI ve SD 1.5 yapılandırılmış olmalı. Ücretli API kullanılmayacak."
            ),
        ),
        headers={"Cache-Control": "no-store"},
    )


async def generate(request):
    studio.require_origin(request)
    try:
        body = await request.json()
        rid = uuid.UUID(str(body["request_id"]))
        cid = uuid.UUID(str(body["conversation_id"]))
        prompt = body["prompt"]
        ratio = body.get("aspect_ratio", "1:1")
        style = body.get("style", "natural")
        if (
            not isinstance(prompt, str)
            or not 1 <= len(prompt.strip()) <= 4000
            or ratio not in SIZES
            or style not in studio.STYLES
            or body.get("image")
            or body.get("image_id")
            or body.get("image_size", "512") != "512"
        ):
            raise ValueError()
    except (ValueError, KeyError, TypeError, AttributeError):
        return studio.fail(
            "invalid_local_image_request",
            "SD 1.5: kare 512×512, dikey 384×640, yatay 640×384; metinden görsel desteklenir.",
        )
    owner = request["user_id"]
    pool = request.app["db"]
    digest = hashlib.sha256(
        json.dumps(
            [prompt, str(cid), ratio, style, "comfyui_local"], ensure_ascii=False
        ).encode()
    ).hexdigest()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(72649181)")
            previous = await conn.fetchrow(
                "SELECT * FROM image_requests WHERE user_id=$1 AND request_id=$2",
                owner,
                rid,
            )
            if previous:
                if (
                    previous["provider"] != "comfyui_local"
                    or previous["fingerprint"] != digest
                ):
                    return studio.fail(
                        "request_conflict", "İstek kimliği başka bir isteğe ait.", 409
                    )
                return await response(conn, owner, rid, previous)
            other = await conn.fetchval(
                "SELECT user_id FROM conversations WHERE id=$1", cid
            )
            if other is not None and other != owner:
                return studio.fail("conversation_not_found", "Sohbet bulunamadı.", 404)
            if not enabled() or not await ready(conn, owner):
                return studio.fail(
                    "local_image_unavailable",
                    "Laptop/ComfyUI hazır değil. Ücretli API kullanılmadı.",
                    503,
                )
            count = await conn.fetchval(
                """SELECT count(*) FROM device_commands WHERE user_id=$1
                AND target='desktop' AND payload->>'mode'='local_image' AND status IN ('queued','delivered')""",
                owner,
            )
            daily = await conn.fetchval(
                """SELECT count(*) FROM image_requests WHERE user_id=$1
                AND provider='comfyui_local' AND created_at>=date_trunc('day',NOW())""",
                owner,
            )
            if count >= 1 or daily >= 20:
                return studio.fail(
                    "local_image_busy",
                    "Bir yerel görsel görevi sürüyor veya günlük 20 istek sınırı doldu.",
                    429,
                )
            payload = dict(
                mode="local_image",
                text=prompt,
                request_id=str(rid),
                aspect_ratio=ratio,
                style=style,
            )
            command = await conn.fetchval(
                """INSERT INTO device_commands(user_id,target,command,payload,source_device,max_retries)
                VALUES($1,'desktop','agent_task',$2::jsonb,$3,0) RETURNING id""",
                owner,
                json.dumps(payload),
                request["device_id"],
            )
            await conn.execute(
                """INSERT INTO image_requests(user_id,request_id,conversation_id,fingerprint,status,command_id,provider)
                VALUES($1,$2,$3,$4,'queued',$5,'comfyui_local')""",
                owner,
                rid,
                cid,
                digest,
                command,
            )
    return web.json_response(
        dict(
            status="queued",
            request_id=str(rid),
            conversation_id=str(cid),
            provider="comfyui_local",
        ),
        status=202,
    )


async def response(conn, owner, rid, row):
    if row["status"] == "completed":
        saved = json.loads(row["result"])
        asset = await conn.fetchval(
            "SELECT 1 FROM generated_images WHERE message_id=$1 AND user_id=$2 AND created_at>=NOW()-INTERVAL '30 days'",
            saved["assistant_message_id"],
            owner,
        )
        if not asset:
            return studio.fail(
                "image_unavailable",
                "Görselin saklama süresi doldu; yeniden üretilmedi.",
                410,
            )
        return web.json_response(saved)
    command = (
        await conn.fetchrow(
            "SELECT status,created_at<NOW()-INTERVAL '10 minutes' AS expired FROM device_commands WHERE id=$1 AND user_id=$2",
            row["command_id"],
            owner,
        )
        if row["command_id"]
        else None
    )
    if (
        row["status"] in ("queued", "running")
        and command
        and (
            command["status"] in ("failed", "expired", "cancelled")
            or command["expired"]
        )
    ):
        await conn.execute(
            "UPDATE image_requests SET status='local_image_failed' WHERE user_id=$1 AND request_id=$2",
            owner,
            rid,
        )
        await conn.execute(
            """UPDATE device_commands SET status='expired',completed_at=NOW(),payload=payload-'text'
            WHERE id=$1 AND user_id=$2 AND status IN ('queued','delivered')""",
            row["command_id"],
            owner,
        )
        return studio.fail(
            "local_image_failed",
            "Laptop görevi kesildi veya süresi doldu. Otomatik tekrar/ücretli geçiş yapılmadı.",
            409,
        )
    if row["status"] not in ("queued", "running"):
        return studio.fail(
            row["status"],
            "Yerel görsel sonucu kullanılamıyor; otomatik tekrar yapılmadı.",
            409,
        )
    return web.json_response(
        dict(
            status=(
                "running" if command and command["status"] == "delivered" else "queued"
            ),
            request_id=str(rid),
            conversation_id=str(row["conversation_id"]),
            provider="comfyui_local",
        ),
        status=202,
    )


async def get_request(request):
    try:
        rid = uuid.UUID(request.match_info["request_id"])
    except ValueError:
        return studio.fail("invalid_request_id", "Geçerli istek kimliği gerekir.")
    async with request.app["db"].acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(72649181)")
            row = await conn.fetchrow(
                "SELECT * FROM image_requests WHERE user_id=$1 AND request_id=$2 AND provider='comfyui_local'",
                request["user_id"],
                rid,
            )
            if not row:
                return studio.fail("request_not_found", "İstek bulunamadı.", 404)
            return await response(conn, request["user_id"], rid, row)


async def complete(request, command_id, attempt, status, result):
    """Device-only fenced queue completion; bytes/history/ack commit atomically."""
    if request.get("auth_kind") != "device":
        raise web.HTTPForbidden()
    pool = request.app["db"]
    owner = request["user_id"]
    try:
        image = result.get("image", {})
        raw, mime, size = (
            studio.validate_image(image) if status == "completed" else (b"", None, None)
        )
    except Exception:
        return studio.fail(
            "invalid_local_image", "Geçersiz görsel; başarı kaydedilmedi.", 400
        )
    digest = hashlib.sha256(raw).hexdigest() if raw else ""
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(72649181)")
            cmd = await conn.fetchrow(
                "SELECT * FROM device_commands WHERE id=$1 AND user_id=$2 AND target='desktop' FOR UPDATE",
                command_id,
                owner,
            )
            if not cmd or attempt < 1 or cmd["delivery_attempt"] != attempt:
                raise web.HTTPConflict()
            payload = json.loads(cmd["payload"])
            saved = json.loads(cmd["result"])
            if payload.get("mode") != "local_image":
                raise web.HTTPConflict()
            if cmd["status"] == "completed" and saved.get("image_digest") == digest:
                return web.json_response(dict(ok=True, replayed=True))
            if cmd["status"] != "delivered":
                raise web.HTTPConflict()
            rid = uuid.UUID(payload["request_id"])
            row = await conn.fetchrow(
                "SELECT * FROM image_requests WHERE user_id=$1 AND request_id=$2 AND command_id=$3 AND provider='comfyui_local' FOR UPDATE",
                owner,
                rid,
                command_id,
            )
            if not row or row["status"] != "queued":
                raise web.HTTPConflict()
            if status == "completed":
                if size != SIZES[payload["aspect_ratio"]]:
                    return studio.fail(
                        "unexpected_image_size", "SD 1.5 profil boyutu uyuşmuyor.", 400
                    )
                output = await studio.persist(
                    conn,
                    owner,
                    row["conversation_id"],
                    rid,
                    payload["text"],
                    cmd["source_device"],
                    raw,
                    mime,
                    size,
                    "stable-diffusion-1.5",
                )
                saved = dict(
                    message="Ücretsiz yerel görsel kaydedildi.",
                    image_digest=digest,
                    assistant_message_id=output["assistant_message_id"],
                )
            else:
                await conn.execute(
                    "UPDATE image_requests SET status='local_image_failed' WHERE user_id=$1 AND request_id=$2",
                    owner,
                    rid,
                )
                saved = dict(
                    message="Yerel görsel üretimi başarısız. Ücretli API kullanılmadı."
                )
            await conn.execute(
                """UPDATE device_commands SET status=$1,result=$2::jsonb,completed_at=NOW(),payload=payload-'text'
                WHERE id=$3 AND user_id=$4""",
                status,
                json.dumps(saved),
                command_id,
                owner,
            )
    return web.json_response(dict(ok=True))
