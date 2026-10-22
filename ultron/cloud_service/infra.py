"""Cross-cutting service infrastructure: security headers, error/request-id middleware,
login brute-force protection and per-owner rate limits for the expensive endpoints.

All state is in memory and bounded (single Render instance); a restart resets the counters.
"""
from __future__ import annotations

import json
import logging
import secrets
import time
from collections import OrderedDict
from typing import Callable

from aiohttp import web

log = logging.getLogger("golge.http")
SLOW_REQUEST_SECONDS = 8.0

# (path prefix, burst, refill seconds per token) — only applied to authenticated owners.
RATE_RULES: dict[str, tuple[int, float]] = {
    "/api/chat": (20, 3.0),            # 20 burst, then one every 3 s
    "/api/local-chat": (20, 3.0),
    "/api/vision": (8, 10.0),
    "/api/document": (6, 15.0),
    "/api/camera-frame": (12, 5.0),
    "/api/image/generate": (4, 30.0),
    "/api/listening-analysis": (6, 20.0),
    "/api/laptop-task": (10, 6.0),
    "/api/mission": (6, 15.0),
    "/api/push/test": (3, 60.0),
    "/api/live": (10, 10.0),
}


class TokenBuckets:
    """Bounded LRU of token buckets."""

    def __init__(self, max_keys: int = 2000, clock: Callable[[], float] = time.monotonic):
        self._b: "OrderedDict[str, list[float]]" = OrderedDict()
        self._max, self._clock = max_keys, clock

    def take(self, key: str, burst: int, refill: float) -> float:
        """Return 0.0 if allowed, else seconds until the next token."""
        now = self._clock()
        tokens, stamp = self._b.pop(key, [float(burst), now])
        tokens = min(float(burst), tokens + (now - stamp) / refill)
        wait = 0.0
        if tokens >= 1.0:
            tokens -= 1.0
        else:
            wait = (1.0 - tokens) * refill
        self._b[key] = [tokens, now]
        while len(self._b) > self._max:
            self._b.popitem(last=False)
        return wait


class LoginGuard:
    """Blocks password guessing: 6 failures per client in 10 minutes → 15 minute lockout."""

    def __init__(self, max_fail: int = 6, window: float = 600.0, lockout: float = 900.0,
                 clock: Callable[[], float] = time.monotonic, max_keys: int = 2000):
        self.max_fail, self.window, self.lockout, self.clock, self.max_keys = max_fail, window, lockout, clock, max_keys
        self._fails: "OrderedDict[str, list[float]]" = OrderedDict()
        self._locked: dict[str, float] = {}

    def retry_after(self, client: str) -> int:
        until = self._locked.get(client, 0.0)
        now = self.clock()
        if until > now:
            return int(until - now) + 1
        self._locked.pop(client, None)
        return 0

    def failure(self, client: str) -> None:
        now = self.clock()
        recent = [t for t in self._fails.pop(client, []) if now - t < self.window] + [now]
        self._fails[client] = recent
        if len(recent) >= self.max_fail:
            self._locked[client] = now + self.lockout
            self._fails.pop(client, None)
        while len(self._fails) > self.max_keys:
            self._fails.popitem(last=False)
        if len(self._locked) > self.max_keys:
            self._locked = {k: v for k, v in self._locked.items() if v > now}

    def success(self, client: str) -> None:
        self._fails.pop(client, None)


def client_key(request: web.Request) -> str:
    """The last X-Forwarded-For entry is the one appended by Render's own proxy; earlier
    entries are client-supplied and can be spoofed to dodge the login limiter."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",")[-1].strip() if forwarded else (request.remote or "?")
    return ip[:64] or "?"


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(self), microphone=(self), geolocation=(self), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    # Not a full script policy (the page uses inline scripts); only the directives that are safe today.
    "Content-Security-Policy": "frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'",
}


async def add_security_headers(request: web.Request, response: web.StreamResponse) -> None:
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    if request.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "private, no-store")
    rid = request.get("request_id")
    if rid:
        response.headers.setdefault("X-Request-Id", rid)


def _json_error(status: int, code: str, rid: str, extra: dict | None = None, headers: dict | None = None) -> web.Response:
    return web.Response(status=status, text=json.dumps({"error": code, "request_id": rid, **(extra or {})}, ensure_ascii=False),
                        content_type="application/json", headers=headers)


@web.middleware
async def error_middleware(request: web.Request, handler):
    """Outermost: request id, timing, and a safe JSON body for unexpected exceptions."""
    rid = request.headers.get("X-Request-Id", "")
    request["request_id"] = rid if rid.isalnum() and 8 <= len(rid) <= 40 else secrets.token_hex(8)
    started = time.monotonic()
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - last line of defence; never echo the message to clients
        log.error("unhandled %s on %s %s rid=%s", type(exc).__name__, request.method, request.path, request["request_id"])
        return _json_error(500, "internal_error", request["request_id"])
    finally:
        took = time.monotonic() - started
        if took >= SLOW_REQUEST_SECONDS and not request.path.startswith(("/api/live", "/api/chat")):
            log.warning("slow %s %s %.1fs rid=%s", request.method, request.path, took, request["request_id"])


def make_rate_limit_middleware(buckets: TokenBuckets | None = None):
    buckets = buckets or TokenBuckets()

    @web.middleware
    async def rate_limit_middleware(request: web.Request, handler):
        if request.method == "POST" or request.path == "/api/live":
            for prefix, (burst, refill) in RATE_RULES.items():
                if request.path == prefix or request.path.startswith(prefix + "/"):
                    owner = request.get("user_id") or client_key(request)
                    wait = buckets.take(f"{prefix}:{owner}", burst, refill)
                    if wait > 0:
                        retry = max(1, int(wait) + 1)
                        raise web.HTTPTooManyRequests(
                            text=json.dumps({"error": "rate_limited", "retry_after": retry,
                                             "detail": "Çok hızlı gidiyorsun; birkaç saniye sonra tekrar dene."}, ensure_ascii=False),
                            content_type="application/json", headers={"Retry-After": str(retry)})
                    break
        return await handler(request)

    rate_limit_middleware.buckets = buckets  # type: ignore[attr-defined]
    return rate_limit_middleware
