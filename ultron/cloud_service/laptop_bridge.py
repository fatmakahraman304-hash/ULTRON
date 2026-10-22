"""Phone chat → laptop bridge: anything the laptop GÖLGE can do, from text chat.

The phone already had this by voice (send_laptop_task). This routes explicit
text requests — "laptop: …", "bilgisayarda … aç", "ekranıma bak" — through the
same paired agent_task queue and returns the laptop's real result into the
conversation. Nothing is claimed unless the laptop reports it.
Destructive requests need the explicit "laptop:" prefix as confirmation, and an
offline laptop is told so instead of silently queueing surprising work.
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from typing import Any

from aiohttp import web

if __package__:
    from .text_normalization import fold_turkish
else:
    from text_normalization import fold_turkish

WAIT_SECONDS = 35.0
POLL_SECONDS = 1.0
MAX_TASK_CHARS = 4000

_PREFIX = re.compile(r"^\s*(?:laptop|laptopa|bilgisayar|bilgisayara|pc|masaustu)\s*[:\-–,]\s*(.+)$", re.S)
_TARGET = re.compile(r"\b(?:laptop|bilgisayar|pc|masaustu)\w*\b")
_TARGET_ACTION = re.compile(
    r"\b(?:ac|acar misin|ac\w*|kapat|calistir|baslat|ara|arat|bak|goster|listele|oku|yaz|indir|kaydet|gonder|tasi|"
    r"kopyala|durdur|duraklat|devam|ses|sesi|parlaklik|ekran|ekrani|dosya|klasor|uygulama|program|tarayici|"
    r"cek|al|calar|cal|kilitle|uyut|yeniden|ne yapiyor|durumu|bak|kontrol|tara|yedekle|temizle|sil)\b")
_SCREEN = re.compile(
    r"\bekran(?:im|imi|imda|imin|in|a|da|i)?\b.{0,40}\b(?:analiz|bak|oku|ozetle|incele|anlat|aciklayi?n|ne var|goruntu|screenshot|ne gor)"
    r"|\bekran (?:analizi|goruntusu|goruntusu al|yakala)\b|\bekranda ne var\b|\bekranima bak\b|\bwhat(?:'s| is) on (?:my )?screen\b")
_DESTRUCTIVE = re.compile(
    r"\b(?:bilgisayar\w*|laptop\w*|pc|masaustu\w*)\b.{0,30}\b(?:kapat|yeniden baslat|restart|shutdown|uyut|format)\w*"
    r"|\b(?:sil|silsin|silelim|format|formatla|uninstall|kaldir|temizle)\b")
# Words that make a message obviously not a laptop command even if it mentions a computer.
_NOT_COMMAND = re.compile(r"\b(?:nedir|nasil calisir|ne demek|neden|niye|nicin|fiyat|oner|tavsiye|hangisi|karsilastir|why|what is|how does)\b")


def classify(text: str) -> dict | None:
    """Return {"task","kind","confirmed","destructive"} or None for normal chat."""
    raw = str(text or "").strip()
    if not raw or len(raw) > MAX_TASK_CHARS:
        return None
    folded = fold_turkish(raw)
    prefixed = _PREFIX.match(raw)
    if prefixed:
        task = prefixed.group(1).strip()
        screen = bool(_SCREEN.search(fold_turkish(task)))
        return {"task": _screen_task(task) if screen else task, "kind": "screen" if screen else "general",
                "confirmed": True, "destructive": bool(_DESTRUCTIVE.search(fold_turkish(task)))}
    if _NOT_COMMAND.search(folded):
        return None
    screen = bool(_SCREEN.search(folded))
    targeted = bool(_TARGET.search(folded)) and bool(_TARGET_ACTION.search(folded))
    if not (screen or targeted):
        return None
    return {"task": _screen_task(raw) if screen else raw, "kind": "screen" if screen else "general",
            "confirmed": False, "destructive": bool(_DESTRUCTIVE.search(folded))}


def _screen_task(request: str) -> str:
    return ("Laptop ekranının şu anki görüntüsünü al (screen_process / ekran görme aracını kullan) ve "
            "gördüğünü Türkçe, kısa ve somut biçimde anlat. Sahibinin isteği: " + request.strip()[:600])


def reply_from_command(row: dict) -> tuple[str, str]:
    """(status, user-facing text) from a device_commands row; status in done/failed/pending."""
    status = row.get("status")
    result = row.get("result") or {}
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except ValueError:
            result = {}
    text = str(result.get("assistant_reply") or result.get("message") or "").strip()
    if status == "completed":
        return "completed", text or "Laptop görevi tamamlandı."
    if status in ("failed", "cancelled", "expired"):
        reason = {"failed": "başarısız oldu", "cancelled": "iptal edildi", "expired": "zaman aşımına uğradı"}[status]
        return "failed", f"Laptop görevi {reason}." + (f" {text}" if text else "")
    return "pending", ""


async def _ensure_conversation(pool: Any, user_id: str, conversation_id: str, title: str) -> uuid.UUID | None:
    try:
        conv = uuid.UUID(conversation_id) if conversation_id else uuid.uuid4()
    except ValueError:
        return None
    claimed = await pool.fetchval(
        "INSERT INTO conversations(id,user_id,title) VALUES($1,$2,$3) "
        "ON CONFLICT(id) DO UPDATE SET updated_at=NOW() WHERE conversations.user_id=EXCLUDED.user_id RETURNING id",
        conv, user_id, title[:80])
    return conv if claimed else None


async def _store_assistant(pool: Any, user_id: str, conv: uuid.UUID, text: str) -> int:
    mid = await pool.fetchval(
        "INSERT INTO messages(conversation_id,user_id,role,content,device_id) "
        "VALUES($1,$2,'assistant',$3,'laptop-agent') RETURNING id", conv, user_id, text)
    await pool.execute("UPDATE conversations SET updated_at=NOW() WHERE id=$1", conv)
    return int(mid)


async def _claim_delivery(pool: Any, user_id: str, command_id: int) -> bool:
    """Exactly-once chat delivery of a finished laptop result."""
    row = await pool.fetchrow(
        "UPDATE device_commands SET result = result || '{\"chat_delivered\": true}'::jsonb "
        "WHERE id=$1 AND user_id=$2 AND target='desktop' AND command='agent_task' "
        "AND status IN ('completed','failed','cancelled','expired') AND NOT (result ? 'chat_delivered') RETURNING id",
        command_id, user_id)
    return row is not None


async def route(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except (ValueError, TypeError):
        return web.json_response({"error": "invalid_json"}, status=400)
    text = str((body or {}).get("message", "")).strip() if isinstance(body, dict) else ""
    intent = classify(text)
    if intent is None:
        return web.json_response({"routed": False})
    pool, user_id = request.app["db"], request["user_id"]
    conv = await _ensure_conversation(pool, user_id, str(body.get("conversation_id", "")).strip(), text)
    if conv is None:
        return web.json_response({"error": "invalid_conversation_id"}, status=400)
    user_mid = await pool.fetchval(
        "INSERT INTO messages(conversation_id,user_id,role,content,device_id) VALUES($1,$2,'user',$3,$4) RETURNING id",
        conv, user_id, text, request["device_id"])
    base = {"routed": True, "conversation_id": str(conv), "user_message_id": int(user_mid)}

    async def answer(status: str, reply: str, **extra) -> web.Response:
        mid = await _store_assistant(pool, user_id, conv, reply)
        return web.json_response({**base, "status": status, "reply": reply, "assistant_message_id": mid, **extra})

    if intent["destructive"] and not intent["confirmed"]:
        return await answer("needs_confirmation",
            "Bu işlem geri alınamayabilir, bu yüzden göndermedim. Gerçekten istiyorsan mesajın başına "
            "“laptop:” yazıp tekrar gönder (örn. “laptop: bilgisayarı kapat”).")
    online = bool(await pool.fetchval(
        "SELECT COALESCE(last_seen > NOW() - INTERVAL '15 seconds', FALSE) FROM device_presence "
        "WHERE user_id=$1 AND device='desktop'", user_id))
    if not online:
        return await answer("offline",
            "Laptop GÖLGE şu an çevrimdışı görünüyor, bu yüzden görevi göndermedim (sonradan sürpriz bir işlem "
            "çalışmasın diye kuyruğa da almadım). Laptop açılıp bağlanınca tekrar dene.")
    row = await pool.fetchrow(
        "INSERT INTO device_commands(user_id,target,command,payload,source_device) "
        "VALUES($1,'desktop','agent_task',$2::jsonb,$3) RETURNING id",
        user_id, json.dumps({"text": intent["task"], "origin": "chat", "plan": []}, ensure_ascii=False),
        request["device_id"])
    command_id = int(row["id"])
    deadline = asyncio.get_event_loop().time() + WAIT_SECONDS
    while True:
        cmd = await pool.fetchrow("SELECT status,result FROM device_commands WHERE id=$1 AND user_id=$2", command_id, user_id)
        state, reply = reply_from_command(dict(cmd) if cmd else {})
        if state != "pending" or asyncio.get_event_loop().time() >= deadline:
            break
        await asyncio.sleep(POLL_SECONDS)
    if state == "pending":
        return await answer("pending",
            "Görevi laptopa gönderdim, çalışıyor. Bitince sonucu buraya yazacağım.",
            task_id=command_id, kind=intent["kind"])
    await _claim_delivery(pool, user_id, command_id)
    return await answer(state, reply, task_id=command_id, kind=intent["kind"])


async def poll(request: web.Request) -> web.Response:
    raw = request.match_info.get("id", "")
    if not re.fullmatch(r"[1-9]\d{0,17}", raw):
        raise web.HTTPBadRequest(text='{"error":"invalid_id"}', content_type="application/json")
    pool, user_id = request.app["db"], request["user_id"]
    cmd = await pool.fetchrow(
        "SELECT status,result FROM device_commands WHERE id=$1 AND user_id=$2 AND target='desktop' AND command='agent_task'",
        int(raw), user_id)
    if cmd is None:
        raise web.HTTPNotFound(text='{"error":"not_found"}', content_type="application/json")
    state, reply = reply_from_command(dict(cmd))
    if state == "pending":
        return web.json_response({"status": "pending"})
    out: dict = {"status": state, "reply": reply, "delivered": False}
    try:
        conv = uuid.UUID(request.query.get("conversation_id", ""))
    except ValueError:
        return web.json_response(out)
    if await _claim_delivery(pool, user_id, int(raw)):
        owner = await pool.fetchval("SELECT user_id FROM conversations WHERE id=$1", conv)
        if owner == user_id:
            out["assistant_message_id"] = await _store_assistant(pool, user_id, conv, reply)
            out["delivered"] = True
    return web.json_response(out)


def register_routes(app: web.Application) -> None:
    app.router.add_post("/api/laptop-task", route)
    app.router.add_get("/api/laptop-task/{id}", poll)
