"""Paid image generation: fail-closed policy, durable at-most-once dispatch.

The ledger deliberately has no retry transition. A worker lost after dispatch
leaves an uncertain request; reusing its UUID never charges again. Cancellation
suppresses output; it does NOT claim to cancel Google's server-side generation.
"""

from __future__ import annotations
import asyncio
import base64
import hashlib
import io
import json
import os
import uuid
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
from aiohttp import web
from PIL import Image

MODEL = "gemini-3.1-flash-image"
RATIOS = ("1:1", "9:16", "16:9")
STYLES = ("natural", "photo", "cinematic", "anime", "3d", "digital-art")


def policy():
    enabled = os.getenv("GOLGE_IMAGE_ENABLED") == "true"
    approved = os.getenv("GOLGE_IMAGE_BUDGET_APPROVED") == "true"
    key = bool(os.getenv("GEMINI_API_KEY", "").strip())
    model = os.getenv("GEMINI_IMAGE_MODEL", MODEL).strip()
    try:
        daily = min(20, max(0, int(os.getenv("GOLGE_IMAGE_DAILY_LIMIT", "0"))))
    except ValueError:
        daily = 0
    try:
        budget = Decimal(os.getenv("GOLGE_IMAGE_DAILY_BUDGET_USD", "0"))
        daily = (
            min(daily, int(budget / Decimal("0.50")))
            if budget.is_finite() and budget > 0
            else 0
        )
    except (InvalidOperation, ValueError, OverflowError):
        daily = 0
    ready = enabled and approved and key and model == MODEL and daily > 0
    return dict(
        available=ready,
        model=model,
        daily_limit=daily,
        reservation_usd="0.50",
        aspect_ratios=RATIOS,
        image_size="1K",
        styles=STYLES,
        detail=(
            "1K görsel çıktı bedeli yaklaşık 0,067 USD; giriş/düşünme bedeli eklenir. İstek başına bütçeden 0,50 USD ayrılır (fatura değil). Son 12 görsel 30 gün saklanır."
            if ready
            else "Görsel üretimi kapalı: sunucu etkinleştirmesi, API anahtarı, maliyet onayı ve günlük sınır gerekir."
        ),
        editing_available=False,
    )


def fail(code, detail, status=400):
    return web.json_response({"error": code, "detail": detail}, status=status)


def validate_image(result):
    encoded = result["image_b64"]
    if not isinstance(encoded, str) or len(encoded) > 12 * 1024 * 1024:
        raise ValueError("invalid encoded image")
    raw = base64.b64decode(encoded, validate=True)
    mime = result["mime_type"]
    if (
        mime not in {"image/png", "image/jpeg", "image/webp"}
        or not 0 < len(raw) <= 8 * 1024 * 1024
    ):
        raise ValueError("invalid image")
    with Image.open(io.BytesIO(raw)) as img:
        if (
            Image.MIME.get(img.format) != mime
            or img.width * img.height > 20_000_000
            or getattr(img, "n_frames", 1) != 1
        ):
            raise ValueError("invalid image dimensions/format")
        size = img.size
        img.verify()
    with Image.open(io.BytesIO(raw)) as img:
        img.load()
    return raw, mime, size


def require_origin(request):
    if request.get("auth_kind") == "web":
        origin = urlsplit(request.headers.get("Origin", ""))
        if (
            origin.scheme not in {"http", "https"}
            or origin.netloc != request.host
            or request.headers.get("Sec-Fetch-Site", "same-origin")
            not in {"same-origin", "none"}
        ):
            raise web.HTTPForbidden(
                text='{"error":"cross_site_denied"}', content_type="application/json"
            )


def provider_mode():
    # Free local is the default even if old Gemini enablement/keys are present.
    return os.getenv("GOLGE_IMAGE_PROVIDER", "comfyui_local")


async def status(request):
    if provider_mode() != "gemini":
        import local_image

        return await local_image.status(request)
    return web.json_response(
        policy() | {"provider": "gemini", "requires_cost_approval": True},
        headers={"Cache-Control": "no-store"},
    )


async def cancel(request):
    require_origin(request)
    try:
        body = await request.json()
        rid = uuid.UUID(str(body["request_id"]))
    except (ValueError, KeyError, TypeError):
        return fail("invalid_request_id", "Geçerli istek kimliği gerekir.")
    # Tombstone also covers cancellation arriving before the generation POST.
    async with request.app["db"].acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(72649181)")
            existing = await conn.fetchval(
                "SELECT status FROM image_requests WHERE user_id=$1 AND request_id=$2",
                request["user_id"],
                rid,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM image_requests WHERE user_id=$1 AND created_at >= date_trunc('day',NOW())",
                request["user_id"],
            )
            if existing is None and count >= 100:
                return fail(
                    "cancel_quota_exceeded",
                    "Günlük yeni istek kaydı sınırı doldu.",
                    429,
                )
            state = await conn.fetchval(
                """INSERT INTO image_requests(user_id,request_id,status)
                VALUES($1,$2,'output_suppressed') ON CONFLICT(user_id,request_id)
                DO UPDATE SET status=CASE WHEN image_requests.status='completed' THEN 'completed'
                ELSE 'output_suppressed' END RETURNING status""",
                request["user_id"],
                rid,
            )
            await conn.execute(
                """UPDATE device_commands SET status='cancelled',completed_at=NOW(),
                payload=payload - 'text', result='{"message":"Yerel görsel sonucu iptal edildi."}'::jsonb
                WHERE user_id=$1 AND id=(SELECT command_id FROM image_requests WHERE user_id=$1 AND request_id=$2)
                  AND payload->>'mode'='local_image' AND status IN ('queued','delivered')""",
                request["user_id"],
                rid,
            )
    return web.json_response(
        {
            "status": (
                "already_completed" if state == "completed" else "output_suppressed"
            ),
            "provider_stopped": False,
            "detail": "Geç yanıt gösterilmeyecek. Sağlayıcı işlemi ve ücreti iptal edilmiş sayılmaz.",
        }
    )


async def generate(request, provider):
    if provider_mode() != "gemini":
        import local_image

        return await local_image.generate(request)
    require_origin(request)
    if request.content_type != "application/json":
        return fail(
            "image_studio_upgrade_required",
            "Yeni görsel onay akışını kullanın; sayfayı yenileyin.",
        )
    try:
        body = await request.json()
        prompt = body.get("prompt", "")
        if not isinstance(prompt, str) or not 0 < len(prompt.strip()) <= 4000:
            return fail(
                "prompt_required", "1–4000 karakterlik bir görsel isteği yazın."
            )
        rid = uuid.UUID(str(body["request_id"]))
        cid = uuid.UUID(str(body["conversation_id"]))
        ratio, style = body.get("aspect_ratio", "1:1"), body.get("style", "natural")
        if (
            ratio not in RATIOS
            or style not in STYLES
            or body.get("image_size", "1K") != "1K"
        ):
            return fail(
                "unsupported_image_options",
                "Bu sürüm 1K kare, dikey veya yatay üretim destekler.",
            )
        if body.get("image") or body.get("image_id"):
            return fail(
                "editing_unavailable",
                "Görsel düzenleme henüz etkin değil; fotoğraf analizi kullanılabilir.",
            )
    except (ValueError, KeyError, TypeError, AttributeError):
        return fail("invalid_request", "Geçerli istek ve sohbet kimliği gerekir.")
    pool, owner = request.app["db"], request["user_id"]
    fingerprint = hashlib.sha256(
        json.dumps([prompt, str(cid), ratio, style], ensure_ascii=False).encode()
    ).hexdigest()
    config = policy()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Global spend reservation and per-owner idempotency are serialized
            # across workers, including concurrent requests with different UUIDs.
            await conn.execute("SELECT pg_advisory_xact_lock(72649181)")
            old = await conn.fetchrow(
                "SELECT * FROM image_requests WHERE user_id=$1 AND request_id=$2",
                owner,
                rid,
            )
            if old:
                if old["fingerprint"] and old["fingerprint"] != fingerprint:
                    return fail(
                        "request_conflict",
                        "Bu istek kimliği başka bir isteğe ait.",
                        409,
                    )
                if old["status"] == "completed":
                    saved = json.loads(old["result"])
                    asset = await conn.fetchrow(
                        "SELECT mime_type FROM generated_images WHERE message_id=$1 AND user_id=$2 AND created_at >= NOW()-INTERVAL '30 days'",
                        saved["assistant_message_id"],
                        owner,
                    )
                    if asset is None:
                        return fail(
                            "image_unavailable",
                            "Görsel silindi veya saklama süresi doldu. Yeni ücretli üretim yapılmadı.",
                            410,
                        )
                    return web.json_response(saved)
                return fail(
                    old["status"],
                    "İstek tekrar gönderilmedi. Geç yanıt/ücret durumu belirsizse yeni üretim başlatmayın.",
                    409,
                )
            other = await conn.fetchval(
                "SELECT user_id FROM conversations WHERE id=$1", cid
            )
            if other is not None and other != owner:
                return fail("conversation_not_found", "Sohbet bulunamadı.", 404)
            if not config["available"]:
                return fail("image_generation_disabled", config["detail"], 503)
            if body.get("cost_approved") is not True:
                return fail(
                    "image_cost_consent_required",
                    "Ücretli tek görsel üretimini açıkça onaylayın.",
                    403,
                )
            count = await conn.fetchval(
                "SELECT count(*) FROM image_requests WHERE reserved AND created_at >= date_trunc('day',NOW())"
            )
            if count >= config["daily_limit"]:
                return fail(
                    "image_quota_exceeded",
                    "Sunucunun günlük görsel üretim sınırı doldu.",
                    429,
                )
            await conn.execute(
                """INSERT INTO image_requests(user_id,request_id,conversation_id,fingerprint,status,reserved)
                VALUES($1,$2,$3,$4,'running',true)""",
                owner,
                rid,
                cid,
                fingerprint,
            )
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                provider, prompt, None, None, aspect_ratio=ratio, style=style
            ),
            timeout=100,
        )
        raw, mime, size = validate_image(result)
    except asyncio.CancelledError:
        # No success save after a disconnected handler. Ledger remains consumed.
        raise
    except Exception as exc:
        code = "image_generation_failed"
        http = 502
        if isinstance(exc, asyncio.TimeoutError):
            code, http = "image_timeout_unknown", 504
        elif str(getattr(exc, "code", "")) == "429":
            code, http = "provider_quota_exceeded", 429
        await pool.execute(
            "UPDATE image_requests SET status=$3 WHERE user_id=$1 AND request_id=$2 AND status='running'",
            owner,
            rid,
            code,
        )
        return fail(
            code,
            "Görsel üretilemedi. Otomatik tekrar yapılmadı; sağlayıcı kotasını/erişimini kontrol edin.",
            http,
        )
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT status FROM image_requests WHERE user_id=$1 AND request_id=$2 FOR UPDATE",
                owner,
                rid,
            )
            if row["status"] != "running":
                return fail(
                    "output_suppressed", "İptal edilen görsel sohbete eklenmedi.", 409
                )
            reply = await persist(
                conn,
                owner,
                cid,
                rid,
                prompt,
                request["device_id"],
                raw,
                mime,
                size,
                config["model"],
            )
    return web.json_response(reply)


async def persist(conn, owner, cid, rid, prompt, device, raw, mime, size, model):
    """Shared atomic owner-scoped image/history persistence for both providers."""
    claimed = await conn.fetchval(
        """INSERT INTO conversations(id,user_id,title) VALUES($1,$2,$3)
        ON CONFLICT(id) DO UPDATE SET updated_at=NOW() WHERE conversations.user_id=EXCLUDED.user_id RETURNING id""",
        cid,
        owner,
        prompt[:80],
    )
    if claimed is None:
        raise web.HTTPNotFound()
    uid = await conn.fetchval(
        "INSERT INTO messages(conversation_id,user_id,role,content,device_id) VALUES($1,$2,'user',$3,$4) RETURNING id",
        cid,
        owner,
        prompt,
        device,
    )
    mid = await conn.fetchval(
        "INSERT INTO messages(conversation_id,user_id,role,content,device_id) VALUES($1,$2,'assistant','Görsel oluşturuldu.',$3) RETURNING id",
        cid,
        owner,
        "local-image" if model == "stable-diffusion-1.5" else "gemini-image",
    )
    await conn.execute(
        "INSERT INTO generated_images(message_id,conversation_id,user_id,mime_type,image_data) VALUES($1,$2,$3,$4,$5)",
        mid,
        cid,
        owner,
        mime,
        raw,
    )
    await conn.execute(
        """DELETE FROM generated_images WHERE user_id=$1 AND (created_at < NOW()-INTERVAL '30 days'
        OR message_id NOT IN (SELECT message_id FROM generated_images WHERE user_id=$1 ORDER BY created_at DESC,message_id DESC LIMIT 12))""",
        owner,
    )
    reply = dict(
        status="completed",
        request_id=str(rid),
        conversation_id=str(cid),
        user_message_id=uid,
        assistant_message_id=mid,
        image_url=f"/api/image/generated/{mid}",
        mime_type=mime,
        width=size[0],
        height=size[1],
        model=model,
    )
    await conn.execute(
        "UPDATE image_requests SET status='completed',result=$3::jsonb WHERE user_id=$1 AND request_id=$2",
        owner,
        rid,
        json.dumps(reply),
    )
    return reply
