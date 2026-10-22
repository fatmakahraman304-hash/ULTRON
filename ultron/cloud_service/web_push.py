"""Web Push for the installed GÖLGE PWA (RFC 8030 + RFC 8291 aes128gcm + RFC 8292 VAPID).

Implemented directly on `cryptography` so deployment needs no extra native build.
VAPID keys are created on first use and stored in the database. Subscription
endpoints are restricted to the real browser push services (SSRF guard).
"""
from __future__ import annotations

import base64
import json
import os
import struct
import time
from typing import Any
from urllib.parse import urlsplit

from aiohttp import web
import http_client
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

PUSH_HOST_SUFFIXES = ("push.apple.com", "web.push.apple.com", "fcm.googleapis.com", "push.services.mozilla.com",
                      "notify.windows.com", "updates.push.services.mozilla.com")
MAX_PAYLOAD = 3800


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64u_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def valid_endpoint(endpoint: object) -> bool:
    if not isinstance(endpoint, str) or not 20 <= len(endpoint) <= 900:
        return False
    parts = urlsplit(endpoint)
    host = (parts.hostname or "").lower()
    return (parts.scheme == "https" and not parts.username and parts.port in (None, 443)
            and any(host == s or host.endswith("." + s) for s in PUSH_HOST_SUFFIXES))


def _public_bytes(key: ec.EllipticCurvePrivateKey) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


def encrypt(payload: bytes, p256dh: str, auth: str, *, ephemeral: ec.EllipticCurvePrivateKey | None = None,
            salt: bytes | None = None) -> bytes:
    """RFC 8291 aes128gcm body for one push message (single record)."""
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload_too_large")
    ua_public = b64u_decode(p256dh)
    auth_secret = b64u_decode(auth)
    if len(ua_public) != 65 or len(auth_secret) != 16:
        raise ValueError("invalid_subscription_keys")
    ephemeral = ephemeral or ec.generate_private_key(ec.SECP256R1())
    salt = salt or os.urandom(16)
    as_public = _public_bytes(ephemeral)
    shared = ephemeral.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public))
    prk = HKDF(hashes.SHA256(), 32, auth_secret, b"WebPush: info\0" + ua_public + as_public).derive(shared)
    cek = HKDF(hashes.SHA256(), 16, salt, b"Content-Encoding: aes128gcm\0").derive(prk)
    nonce = HKDF(hashes.SHA256(), 12, salt, b"Content-Encoding: nonce\0").derive(prk)
    ciphertext = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)  # 0x02 = last-record delimiter
    return salt + struct.pack(">IB", 4096, len(as_public)) + as_public + ciphertext


def vapid_authorization(endpoint: str, private_key: ec.EllipticCurvePrivateKey, subject: str, *, now: float | None = None) -> str:
    parts = urlsplit(endpoint)
    claims = {"aud": f"{parts.scheme}://{parts.netloc}", "exp": int((now or time.time()) + 12 * 3600), "sub": subject}
    signing = b64u(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode()) + "." + \
        b64u(json.dumps(claims, separators=(",", ":")).encode())
    r, s = decode_dss_signature(private_key.sign(signing.encode(), ec.ECDSA(hashes.SHA256())))
    token = signing + "." + b64u(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
    return f"vapid t={token}, k={b64u(_public_bytes(private_key))}"


async def load_vapid(pool: Any) -> tuple[ec.EllipticCurvePrivateKey, str]:
    row = await pool.fetchrow("SELECT private_pem,public_key FROM push_config WHERE id=1")
    if row is None:
        key = ec.generate_private_key(ec.SECP256R1())
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()).decode()
        await pool.execute("INSERT INTO push_config(id,private_pem,public_key) VALUES(1,$1,$2) ON CONFLICT DO NOTHING",
                           pem, b64u(_public_bytes(key)))
        row = await pool.fetchrow("SELECT private_pem,public_key FROM push_config WHERE id=1")
    return serialization.load_pem_private_key(row["private_pem"].encode(), None), row["public_key"]


async def send_push(pool: Any, sub: dict, message: dict, *, urgency: str = "normal", ttl: int = 3600,
                    session: object | None = None) -> str:
    """Return 'ok', 'gone' (subscription removed) or 'error'."""
    if not valid_endpoint(sub["endpoint"]):
        return "gone"
    key, _ = await load_vapid(pool)
    body = encrypt(json.dumps(message, ensure_ascii=False).encode(), sub["p256dh"], sub["auth"])
    headers = {"Authorization": vapid_authorization(sub["endpoint"], key, os.getenv("GOLGE_PUSH_SUBJECT", "mailto:admin@golge.invalid")),
               "Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream",
               "TTL": str(ttl), "Urgency": urgency}
    try:
        status, _, _ = await http_client.fetch(sub["endpoint"], method="POST", data=body, headers=headers, timeout=10, max_bytes=100_000)
    except Exception:
        return "error"
    if status in (200, 201, 202):
        await pool.execute("UPDATE push_subscriptions SET last_ok=NOW() WHERE endpoint=$1", sub["endpoint"])
        return "ok"
    if status in (404, 410):
        await pool.execute("DELETE FROM push_subscriptions WHERE endpoint=$1", sub["endpoint"])
        return "gone"
    return "error"


async def push_to_user(pool: Any, user_id: str, message: dict, **kw) -> int:
    subs = await pool.fetch("SELECT endpoint,p256dh,auth FROM push_subscriptions WHERE user_id=$1", user_id)
    sent = 0
    for sub in subs:
        if await send_push(pool, dict(sub), message, **kw) == "ok":
            sent += 1
    return sent


# ── HTTP ────────────────────────────────────────────────────────────────────

def _web_only(request: web.Request) -> None:
    if request.get("auth_kind") != "web":
        raise web.HTTPForbidden(text='{"error":"browser_session_required"}', content_type="application/json")
    if request.method != "GET" and request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
        raise web.HTTPForbidden(text='{"error":"cross_origin_denied"}', content_type="application/json")


async def public_key(request: web.Request) -> web.Response:
    _web_only(request)
    _, pub = await load_vapid(request.app["db"])
    count = await request.app["db"].fetchval("SELECT COUNT(*) FROM push_subscriptions WHERE user_id=$1", request["user_id"])
    return web.json_response({"public_key": pub, "subscribed_devices": int(count or 0)})


async def subscribe(request: web.Request) -> web.Response:
    _web_only(request)
    try:
        body = await request.json()
        endpoint, keys = body["endpoint"], body["keys"]
        p256dh, auth = str(keys["p256dh"]), str(keys["auth"])
        if not valid_endpoint(endpoint) or len(b64u_decode(p256dh)) != 65 or len(b64u_decode(auth)) != 16:
            raise ValueError()
    except (KeyError, TypeError, ValueError, AttributeError):
        return web.json_response({"error": "invalid_subscription"}, status=400)
    count = await request.app["db"].fetchval("SELECT COUNT(*) FROM push_subscriptions WHERE user_id=$1", request["user_id"])
    if int(count or 0) >= 8:
        return web.json_response({"error": "too_many_devices"}, status=409)
    await request.app["db"].execute(
        "INSERT INTO push_subscriptions(endpoint,user_id,p256dh,auth) VALUES($1,$2,$3,$4) "
        "ON CONFLICT(endpoint) DO UPDATE SET user_id=EXCLUDED.user_id,p256dh=EXCLUDED.p256dh,auth=EXCLUDED.auth",
        endpoint, request["user_id"], p256dh, auth)
    return web.json_response({"subscribed": True})


async def unsubscribe(request: web.Request) -> web.Response:
    _web_only(request)
    try:
        endpoint = (await request.json())["endpoint"]
    except (KeyError, TypeError, ValueError):
        return web.json_response({"error": "invalid_request"}, status=400)
    await request.app["db"].execute("DELETE FROM push_subscriptions WHERE endpoint=$1 AND user_id=$2", endpoint, request["user_id"])
    return web.json_response({"subscribed": False})


async def test_push(request: web.Request) -> web.Response:
    _web_only(request)
    sent = await push_to_user(request.app["db"], request["user_id"],
                              {"title": "GÖLGE", "body": "Bildirimler çalışıyor ✓", "tag": "golge-test"}, ttl=60)
    return web.json_response({"sent": sent})


def register_routes(app: web.Application) -> None:
    app.router.add_get("/api/push/key", public_key)
    app.router.add_post("/api/push/subscribe", subscribe)
    app.router.add_delete("/api/push/subscribe", unsubscribe)
    app.router.add_post("/api/push/test", test_push)
