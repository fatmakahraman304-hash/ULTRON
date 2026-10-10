"""Private owner-reviewed conversation notes, distinct from assistant memory.

Drafting reads up to 80 messages ONLY in an authenticated owner conversation.
Drafts are deterministic excerpts, not an LLM-authored/exhaustive summary.
No server-side draft persistence. Create/update/delete require explicit user
interaction and never affect personal memories or external providers.
"""
from __future__ import annotations

import re
import uuid
from aiohttp import web
from conversation_turns import select_recap_turns

_ID = re.compile(r"[1-9][0-9]{0,17}\Z")
_SENSITIVE = re.compile(
    r"(?i)(?:şifre|parola|password|passphrase|pin kod|api[_ -]?key|"
    r"secret|token|otp|iban|cvv|cvc|kredi kart|kimlik no|pasaport no|"
    r"doğrulama kod|medical record|email password)"
)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b")
_NUMBERS = re.compile(r"(?:\d[ -]?){9,}")


def _browser(request, *, write=False):
    if request.get("auth_kind") != "web":
        raise web.HTTPForbidden(text='{"error":"browser_session_required"}',
                                content_type="application/json")
    if write:
        if request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            raise web.HTTPForbidden(text='{"error":"cross_site_denied"}',
                                    content_type="application/json")
        if request.content_type != "application/json" and request.method != "DELETE":
            raise web.HTTPUnsupportedMediaType(text='{"error":"json_required"}',
                                               content_type="application/json")


def _conversation_uuid(raw):
    if not isinstance(raw, str):
        raise web.HTTPBadRequest(text='{"error":"conversation_id_required"}',
                                 content_type="application/json")
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError, TypeError):
        raise web.HTTPBadRequest(text='{"error":"invalid_conversation_id"}',
                                 content_type="application/json")


def _note_id(request):
    raw = request.match_info.get("id", "")
    if not isinstance(raw, str) or not _ID.fullmatch(raw):
        raise web.HTTPBadRequest(text='{"error":"invalid_id"}', content_type="application/json")
    return int(raw)


def validate_note(payload):
    if not isinstance(payload, dict):
        raise ValueError("invalid_body")
    title, body = payload.get("title"), payload.get("body")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 140:
        raise ValueError("invalid_title")
    if not isinstance(body, str) or not 1 <= len(body.strip()) <= 3000:
        raise ValueError("invalid_note")
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in title + body):
        raise ValueError("control_character")
    return title.strip(), body.strip()


async def _verified_conversation(request, ident):
    exists = await request.app["db"].fetchval(
        "SELECT id FROM conversations WHERE id=$1 AND user_id=$2",
        ident, request["user_id"],
    )
    if exists is None:
        raise web.HTTPNotFound(text='{"error":"conversation_not_found"}',
                               content_type="application/json")


def _preview_text(rows):
    """Show a reviewable transcript excerpt; omit common secret-looking lines.

    This is NOT a guaranteed PII scanner or a semantic LLM summary.
    The owner must examine the complete draft before explicit saving.
    """
    safe = []
    for record in rows:
        role = record.get("role") if hasattr(record, "get") else None
        content = record.get("content") if hasattr(record, "get") else None
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        candidate = " ".join(content.strip().split())[:420]
        if not candidate or _SENSITIVE.search(candidate) or _EMAIL.search(candidate) or _NUMBERS.search(candidate):
            continue
        safe.append({"role":role,"content":candidate})
    chosen = select_recap_turns(safe, max_chars=2400, max_turns=12)
    return "\n".join(("Sen: " if row["role"]=="user" else "ULTRON: ")+row["content"]
                     for row in chosen)[:3000]


async def draft_note(request):
    _browser(request)
    conv = _conversation_uuid(request.query.get("conversation_id"))
    await _verified_conversation(request, conv)
    rows = await request.app["db"].fetch(
        "SELECT role,content FROM messages WHERE conversation_id=$1 AND user_id=$2 "
        "AND role IN ('user','assistant') ORDER BY id DESC LIMIT 80",
        conv, request["user_id"],
    )
    body = _preview_text(list(reversed(rows)))
    return web.json_response({
        "draft": {"title":"Sohbetten not","body":body,"conversation_id":str(conv)},
        "saved":False, "is_exhaustive":False, "memory_saved":False,
        "requires_manual_review":True,
    },headers={"Cache-Control":"private, no-store"})


async def list_notes(request):
    _browser(request)
    conv = _conversation_uuid(request.query.get("conversation_id"))
    await _verified_conversation(request, conv)
    rows = await request.app["db"].fetch(
        "SELECT id,conversation_id,title,body FROM conversation_notes "
        "WHERE user_id=$1 AND conversation_id=$2 ORDER BY id DESC LIMIT 30",
        request["user_id"], conv,
    )
    return web.json_response({
        "notes":[{"id":r["id"],"conversation_id":str(r["conversation_id"]),
                  "title":r["title"],"body":r["body"]} for r in rows],
        "external_sync":False,"added_to_model_memory":False,
    },headers={"Cache-Control":"private, no-store"})


async def create_note(request):
    _browser(request, write=True)
    try:
        payload = await request.json()
        title, body = validate_note(payload)
    except (ValueError, TypeError):
        return web.json_response({"error":"invalid_note_fields"},status=400)
    conv = _conversation_uuid(payload.get("conversation_id"))
    await _verified_conversation(request, conv)
    # Limit retained private notes. Database never auto-saves a proposed draft.
    count = await request.app["db"].fetchval(
        "SELECT COUNT(*) FROM conversation_notes WHERE user_id=$1 AND conversation_id=$2",
        request["user_id"], conv,
    )
    if count >= 30:
        return web.json_response({"error":"conversation_note_limit"},status=429)
    row = await request.app["db"].fetchrow(
        "INSERT INTO conversation_notes(user_id,conversation_id,title,body) "
        "VALUES($1,$2,$3,$4) RETURNING id",
        request["user_id"], conv, title, body,
    )
    return web.json_response({"note_id":row["id"],"saved":True,
                              "memory_saved":False},status=201)


async def edit_note(request):
    _browser(request, write=True)
    nid = _note_id(request)
    try:
        title, body = validate_note(await request.json())
    except (ValueError, TypeError):
        return web.json_response({"error":"invalid_note_fields"},status=400)
    row = await request.app["db"].fetchrow(
        "UPDATE conversation_notes SET title=$3,body=$4,updated_at=NOW() "
        "WHERE id=$1 AND user_id=$2 RETURNING id",
        nid, request["user_id"], title, body,
    )
    if row is None:
        raise web.HTTPNotFound(text='{"error":"not_found"}',content_type="application/json")
    return web.json_response({"note_id":row["id"],"saved":True,
                              "memory_saved":False})


async def delete_note(request):
    _browser(request, write=True)
    nid = _note_id(request)
    row = await request.app["db"].fetchrow(
        "DELETE FROM conversation_notes WHERE id=$1 AND user_id=$2 RETURNING id",
        nid, request["user_id"],
    )
    if row is None:
        raise web.HTTPNotFound(text='{"error":"not_found"}',content_type="application/json")
    return web.json_response({"deleted":True,"memory_unchanged":True})


def register_conversation_note_routes(app):
    app.router.add_get("/api/conversation-notes/preview", draft_note)
    app.router.add_get("/api/conversation-notes", list_notes)
    app.router.add_post("/api/conversation-notes", create_note)
    app.router.add_put("/api/conversation-notes/{id}", edit_note)
    app.router.add_delete("/api/conversation-notes/{id}", delete_note)
