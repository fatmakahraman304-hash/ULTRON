"""ULTRON owner-initiated development requests, ChatGPT hand-off and release proof.

The consumer ChatGPT chat has no background inbox/API that a third-party
assistant can silently message. We therefore provide a deliberate user handoff.
Only server-verified GitHub Actions, Render deployment and reported desktop
checkout can move a request to completed; clients cannot mark their own work
successful. Nothing here executes model-supplied code or modifies GitHub.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
import uuid
from urllib.parse import quote

from aiohttp import ClientSession, ClientTimeout, web

REPOSITORY = "fatmakahraman304-hash/ULTRON"
BRANCH = "feat/ultron-cloud-shared-memory"
GITHUB = "https://api.github.com/repos/" + REPOSITORY
TARGETS = frozenset(("phone", "desktop", "both"))
_STATES = frozenset(("awaiting_chatgpt", "tests_pending", "tests_failed",
                     "release_pending", "desktop_pending", "completed"))
_VERIFICATION_CACHE: dict[str, tuple[float, dict]] = {}
_TIMEOUT = ClientTimeout(total=13)
_LIMIT = 1024 * 1024


def dev_intent(text: str) -> bool:
    """Conservative trigger: never mistake ordinary 'update the weather' for code editing."""
    t = re.sub(r"\s+", " ", text.casefold().strip())
    subject = bool(re.search(
        r"\b(?:ultron(?:a|u|un|umu|da|daki)?|kendini|kod(?:u|un|larını|larını)?|"
        r"arayüz(?:ü|ünü|ünü)?|uygulama(?:yı|nı)?|sistem(?:i|ini)?)\b", t
    ))
    verb = bool(re.search(
        r"(?:geliştir|güncelle|düzelt|özellik ekle|kod(?:u|larını)? değiştir|"
        r"kendini yenile|kendini güncelle|yeni özellik)", t
    ))
    return subject and verb


def handoff_text(item: dict) -> str:
    marker = "ULTRON-DEV-" + str(item["id"])
    return (
        "Bu ULTRON geliştirme isteğini bu ChatGPT sohbetinde gerçekleştir.\n"
        "Kendi özel ChatGPT sohbetini ULTRON'un otomatik açıp mesaj göndermesi mümkün değil; "
        "bu metni kullanıcı burada başlattı. Kodları GitHub bağlayıcısıyla işle.\n"
        f"İstek kodu: {marker}\n"
        f"GitHub: https://github.com/{REPOSITORY}\n"
        f"Dal: {BRANCH}\n"
        f"Hedef: {item['target']} (phone=ücretsiz iPhone web/PWA, desktop=Windows).\n"
        f"İstenen değişiklik: {item['prompt']}\n\n"
        "AGENTS.md, ULTRON_ROADMAP.md, ULTRON_PROGRESS.md, ULTRON_NEXT_TASKS.md, "
        "ULTRON_TEST_RESULTS.md oku. Yalnız çalışır değişiklikleri commit et; "
        f"son test edilecek KOD commit mesajında aynen {marker} yaz. "
        "GitHub CI'ı başarılı olana kadar düzelt. Render yayınını ve deployed SHA'yı "
        "doğrula. Windows yerel kurulumunu yapmadan bilgisayarda güncellendi deme. "
        "İzin gerektiren işlemleri kullanıcı onayına bırak. "
        "Test sonuçlarını ve eksikleri açıkça bildir; ücretli API anahtarı isteme."
    )


def _item(row) -> dict:
    item = dict(row)
    item["handoff"] = handoff_text(item)
    return item


def _http_error(error: str, status: int = 400):
    return web.json_response({"error": error}, status=status)


async def create_request(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except (ValueError, TypeError):
        return _http_error("invalid_json")
    if not isinstance(body, dict):
        return _http_error("invalid_payload")
    prompt = str(body.get("prompt") or "").strip()
    target = str(body.get("target") or "both").strip().lower()
    if not 12 <= len(prompt) <= 2000:
        return _http_error("prompt_length_12_to_2000")
    if target not in TARGETS:
        return _http_error("invalid_target")
    # Bounded requests per user; never turns unsupervised model text into code.
    recent = await request.app["db"].fetchval(
        "SELECT COUNT(*) FROM dev_requests WHERE user_id=$1 "
        "AND created_at > NOW() - INTERVAL '1 hour'", request["user_id"]
    )
    if int(recent or 0) >= 12:
        return _http_error("rate_limit_12_per_hour", 429)
    row = await request.app["db"].fetchrow(
        "INSERT INTO dev_requests(id,user_id,prompt,target,source_device) "
        "VALUES($1,$2,$3,$4,$5) RETURNING *",
        uuid.uuid4(), request["user_id"], prompt, target, request["device_id"],
    )
    return web.json_response({"ok": True, "request": _item(row)}, dumps=_json_dumps, status=201)


def _json_dumps(value):
    return json.dumps(value, ensure_ascii=False, default=str)


async def list_requests(request: web.Request) -> web.Response:
    rows = await request.app["db"].fetch(
        "SELECT * FROM dev_requests WHERE user_id=$1 ORDER BY created_at DESC LIMIT 30",
        request["user_id"]
    )
    return web.json_response({"requests": [_item(row) for row in rows]}, dumps=_json_dumps)


async def _github_json(path: str) -> dict | list:
    """Fixed GitHub origin, bounded response, reject redirects; never user URL."""
    token = os.getenv("ULTRON_GITHUB_READ_TOKEN", "").strip()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ULTRON-Development-Verification/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    async with ClientSession(timeout=_TIMEOUT, headers=headers) as session:
        async with session.get(GITHUB + path, allow_redirects=False) as response:
            if response.status != 200:
                raise RuntimeError("github_http_" + str(response.status))
            content = await response.content.read(_LIMIT + 1)
            if len(content) > _LIMIT:
                raise RuntimeError("github_response_too_large")
            payload = json.loads(content)
            if not isinstance(payload, (dict, list)):
                raise RuntimeError("github_invalid_json")
            return payload


async def _is_ancestor(sha: str, deployed: str) -> bool:
    if not re.fullmatch(r"[0-9a-f]{40}", sha or "") or not re.fullmatch(r"[0-9a-f]{40}", deployed or ""):
        return False
    if sha == deployed:
        return True
    result = await _github_json("/compare/" + sha + "..." + deployed)
    return result.get("status") in ("ahead", "identical")


def release_state(*, target: str, tests_ok: bool, tests_failed: bool,
                  deployed_ok: bool, desktop_ok: bool) -> str:
    """Pure state machine, with no optimistic 'completed' states."""
    if tests_failed:
        return "tests_failed"
    if not tests_ok:
        return "tests_pending"
    if not deployed_ok:
        return "release_pending"
    if target in ("desktop", "both") and not desktop_ok:
        return "desktop_pending"
    return "completed"


async def verify_request(request: web.Request) -> web.Response:
    ident = request.match_info["id"]
    try:
        uuid_id = uuid.UUID(ident)
    except (ValueError, AttributeError):
        return _http_error("invalid_id")
    row = await request.app["db"].fetchrow(
        "SELECT * FROM dev_requests WHERE id=$1 AND user_id=$2",
        uuid_id, request["user_id"]
    )
    if not row:
        return _http_error("not_found", 404)
    item = dict(row)
    marker = "ULTRON-DEV-" + str(uuid_id)
    # CI check is read only and rate-limited by process cache; any upstream
    # outage preserves the old truthful result, never upgrades to completed.
    cache_key = str(uuid_id) + ":" + os.getenv("RENDER_GIT_COMMIT", "")
    cached = _VERIFICATION_CACHE.get(cache_key)
    if cached and cached[0] > time.monotonic():
        return web.json_response({"ok": True, "request": _item(cached[1])}, dumps=_json_dumps)
    try:
        commits = await _github_json("/commits?sha=" + quote(BRANCH) + "&per_page=75")
        match = next((
            c for c in commits if marker in str((c.get("commit") or {}).get("message") or "")
            and re.fullmatch(r"[0-9a-f]{40}", str(c.get("sha") or ""))
        ), None)
        if not match:
            # No marker => GitHub has NOT performed this request.
            _VERIFICATION_CACHE[cache_key] = (time.monotonic()+45, item)
            return web.json_response({"ok": True, "request": _item(item)}, dumps=_json_dumps)
        sha = str(match["sha"])
        # Must have passed CI on the very SAME code commit; older successes do
        # not authorize a newer commit.
        data = await _github_json("/actions/runs?head_sha=" + sha + "&per_page=100")
        runs = [r for r in data.get("workflow_runs", [])
                if r.get("head_sha") == sha]
        green = {r.get("name") for r in runs
                 if r.get("status") == "completed" and r.get("conclusion") == "success"}
        red = {r.get("name") for r in runs
               if r.get("status") == "completed" and r.get("conclusion") in ("failure","cancelled","timed_out")}
        needed = {"ULTRON Scene Build Check"}
        if item["target"] in ("phone", "both"):
            needed.add("Cloud Queue PostgreSQL Integration")
        tests_ok = needed.issubset(green)
        tests_failed = bool(needed & red) and not tests_ok
        deployed = os.getenv("RENDER_GIT_COMMIT", "").lower()
        cloud_ok = await _is_ancestor(sha, deployed) if tests_ok else False
        local_sha = str(item.get("desktop_sha") or "").lower()
        desktop_ok = await _is_ancestor(sha, local_sha) if cloud_ok and local_sha else False
        state = release_state(target=item["target"], tests_ok=tests_ok,
                              tests_failed=tests_failed,
                              deployed_ok=cloud_ok, desktop_ok=desktop_ok)
        updated = await request.app["db"].fetchrow(
            "UPDATE dev_requests SET status=$3,commit_sha=$4,verified_tests=$5,"
            "verified_cloud=$6,updated_at=NOW() "
            "WHERE id=$1 AND user_id=$2 RETURNING *",
            uuid_id, request["user_id"], state, sha,
            tests_ok, cloud_ok,
        )
        item = dict(updated)
        _VERIFICATION_CACHE[cache_key] = (time.monotonic()+45, item)
    except (RuntimeError, asyncio.TimeoutError, ValueError, TypeError) as exc:
        return web.json_response({
            "ok": False, "error": "verification_temporarily_unavailable",
            "detail": type(exc).__name__,
            "request": _item(item)
        }, status=503, dumps=_json_dumps)
    return web.json_response({"ok": True, "request": _item(item)}, dumps=_json_dumps)


async def report_desktop_version(request: web.Request) -> web.Response:
    # This endpoint is desktop-device-token ONLY. The phone cannot assert a
    # local installation on a computer it has not accessed.
    if request.get("auth_kind") != "device":
        return _http_error("desktop_token_required", 403)
    try:
        item_id = uuid.UUID(request.match_info["id"])
    except (ValueError, AttributeError):
        return _http_error("invalid_id")
    body = await request.json()
    sha = str(body.get("commit_sha") or "").strip().lower() if isinstance(body, dict) else ""
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        return _http_error("invalid_commit_sha")
    row = await request.app["db"].fetchrow(
        "UPDATE dev_requests SET desktop_sha=$3,updated_at=NOW() "
        "WHERE id=$1 AND user_id=$2 RETURNING id",
        item_id, request["user_id"], sha,
    )
    if not row:
        return _http_error("not_found", 404)
    _VERIFICATION_CACHE.clear()
    # Recording a SHA alone never marks completed; server still checks ancestry.
    return web.json_response({"ok": True, "desktop_version_recorded": True})


def register(app: web.Application) -> None:
    app.router.add_post("/api/dev-requests", create_request)
    app.router.add_get("/api/dev-requests", list_requests)
    app.router.add_post("/api/dev-requests/{id}/verify", verify_request)
    app.router.add_post("/api/dev-requests/{id}/desktop-version", report_desktop_version)
