"""Owner-opted-in automatic learning from explicit first-person chat statements.

No external model/API, scraping, background listener or training run.
Only patterns asserting a preference, goal or project in the owner's own
message are eligible. Secrets, high-risk personal data and model instructions
are not automatically memorized. Entries never overwrite existing memories.
"""
from __future__ import annotations

import hashlib
import re

from aiohttp import web

# Explicit owner assertions rather than model guesses or assistant answers.
_PATTERNS = (
    ("PREFERENCE", re.compile(r"^(?:benim\s+)?tercihim\s*[:：]\s*(.+)$", re.I)),
    ("GOAL", re.compile(r"^(?:benim\s+)?hedefim\s*[:：]\s*(.+)$", re.I)),
    ("PROJECT", re.compile(r"^(?:benim\s+)?projem\s*[:：]\s*(.+)$", re.I)),
    ("PREFERENCE", re.compile(r"^i\s+prefer\s*[:：]\s*(.+)$", re.I)),
    ("GOAL", re.compile(r"^my\s+goal\s+is\s*[:：]\s*(.+)$", re.I)),
    ("PROJECT", re.compile(r"^my\s+project\s+is\s*[:：]\s*(.+)$", re.I)),
)
_DENIED = re.compile(
    r"(?:şifre|parola|password|passphrase|pin\s*(?:kod|code)|api[_ -]?key|"
    r"token|secret|gizli\s*anahtar|otp|doğrulama\s*kodu|"
    r"kimlik\s*no|pasaport\s*no|iban|hesap\s*no|kart\s*no|"
    r"cvv|cvc|kredi\s*kart|"
    r"sağlık|hastalık|teşhis|ilaç|medical|diagnos|"
    r"ev\s*adresim|home\s*address|telefon\s*numaram|phone\s*number|"
    r"e-?posta\s*adresim|email\s*address)",
    re.I,
)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_LONG_DIGITS = re.compile(r"(?:\d[ -]?){8,}")
_URL = re.compile(r"https?://|www\.", re.I)


def extract_owner_statement(text: object) -> tuple[str, str, str] | None:
    if not isinstance(text, str) or not 1 <= len(text) <= 450:
        return None
    statement = text.strip()
    if (not statement or statement.startswith((">", "\"", "'", "`", "-", "#"))
            or "\n" in statement or "\r" in statement
            or _DENIED.search(statement) or _EMAIL.search(statement)
            or _LONG_DIGITS.search(statement) or _URL.search(statement)):
        return None
    for category, pattern in _PATTERNS:
        match = pattern.fullmatch(statement)
        if match:
            value = match.group(1).strip()
            if not 3 <= len(value) <= 180 or any(ord(c) < 32 for c in value):
                return None
            if _DENIED.search(value):
                return None
            normalized = " ".join(value.casefold().split())
            digest = hashlib.sha256((category + ":" + normalized).encode("utf-8")).hexdigest()[:20]
            return category, "autolearn:" + category.lower() + ":" + digest, value
    return None


def require_browser(request, *, write: bool = False):
    if request.get("auth_kind") != "web":
        raise web.HTTPForbidden(text='{"error":"browser_session_required"}', content_type="application/json")
    if write:
        if request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            raise web.HTTPForbidden(text='{"error":"cross_site_denied"}', content_type="application/json")
        if request.content_type != "application/json":
            raise web.HTTPUnsupportedMediaType(text='{"error":"json_required"}', content_type="application/json")


async def get_auto_learning(request):
    require_browser(request)
    enabled = await request.app["db"].fetchval(
        "SELECT enabled FROM owner_auto_learning WHERE user_id=$1",
        request["user_id"],
    )
    return web.json_response({
        "enabled": bool(enabled), "scope": "explicit_owner_chat_statements_only",
        "model_retraining": False, "background_surveillance": False,
        "secret_filter": True,
    })


async def set_auto_learning(request):
    require_browser(request, write=True)
    try:
        body = await request.json()
    except (ValueError, TypeError):
        return web.json_response({"error": "invalid_json"}, status=400)
    if not isinstance(body, dict) or type(body.get("enabled")) is not bool:
        return web.json_response({"error": "enabled_boolean_required"}, status=400)
    # Defaults OFF for every account; browser owner can reverse the decision.
    enabled = body["enabled"]
    await request.app["db"].execute(
        "INSERT INTO owner_auto_learning(user_id,enabled) VALUES($1,$2) "
        "ON CONFLICT(user_id) DO UPDATE SET enabled=EXCLUDED.enabled, updated_at=NOW()",
        request["user_id"], enabled,
    )
    return web.json_response({"enabled": enabled, "scope": "explicit_owner_chat_statements_only"})


async def learn_from_owner_message(pool, user_id: str, text: str) -> bool:
    """Only called after an accepted owner text chat; no tool/model outputs used."""
    candidate = extract_owner_statement(text)
    if candidate is None:
        return False
    category, key, value = candidate
    # Atomic feature flag check with the write so disabling doesn't race a save.
    async with pool.acquire() as conn:
        async with conn.transaction():
            enabled = await conn.fetchval(
                "SELECT enabled FROM owner_auto_learning WHERE user_id=$1 FOR UPDATE",
                user_id,
            )
            if not enabled:
                return False
            saved = await conn.fetchval(
                "INSERT INTO memories(user_id,category,key,value,updated_by_device) "
                "VALUES($1,$2,$3,$4,'opt-in-auto-learning') "
                "ON CONFLICT(user_id,key) DO NOTHING RETURNING key",
                user_id, category, key, value,
            )
            return saved is not None


def register_routes(app):
    app.router.add_get("/api/auto-learning", get_auto_learning)
    app.router.add_put("/api/auto-learning", set_auto_learning)
