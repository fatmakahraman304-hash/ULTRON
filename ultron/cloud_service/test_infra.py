"""Security headers, error middleware, login guard and rate limits."""
import asyncio
import json
import unittest

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

import infra


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class Buckets(unittest.TestCase):
    def test_burst_then_refill(self):
        clock = Clock()
        b = infra.TokenBuckets(clock=clock)
        self.assertEqual([b.take("k", 3, 10.0) for _ in range(3)], [0.0, 0.0, 0.0])
        wait = b.take("k", 3, 10.0)
        self.assertGreater(wait, 9.0)
        clock.t += 10
        self.assertEqual(b.take("k", 3, 10.0), 0.0)
        self.assertEqual(b.take("other", 3, 10.0), 0.0)     # independent keys

    def test_bounded_memory(self):
        b = infra.TokenBuckets(max_keys=50)
        for i in range(500):
            b.take(f"k{i}", 2, 5.0)
        self.assertLessEqual(len(b._b), 50)


class Login(unittest.TestCase):
    def test_lockout_after_repeated_failures_and_recovery(self):
        clock = Clock()
        g = infra.LoginGuard(max_fail=3, window=60, lockout=120, clock=clock)
        for _ in range(2):
            g.failure("1.2.3.4")
        self.assertEqual(g.retry_after("1.2.3.4"), 0)
        g.failure("1.2.3.4")
        self.assertGreater(g.retry_after("1.2.3.4"), 100)
        self.assertEqual(g.retry_after("9.9.9.9"), 0)
        clock.t += 121
        self.assertEqual(g.retry_after("1.2.3.4"), 0)

    def test_old_failures_expire_and_success_resets(self):
        clock = Clock()
        g = infra.LoginGuard(max_fail=3, window=60, lockout=120, clock=clock)
        g.failure("a"); g.failure("a")
        clock.t += 61
        g.failure("a")
        self.assertEqual(g.retry_after("a"), 0)
        g.failure("a"); g.success("a"); g.failure("a"); g.failure("a")
        self.assertEqual(g.retry_after("a"), 0)


def make_app(buckets=None):
    async def ok(request):
        return web.json_response({"ok": True})

    async def boom(request):
        raise RuntimeError("secret internals sk-12345")

    async def teapot(request):
        raise web.HTTPForbidden()

    @web.middleware
    async def fake_auth(request, handler):
        request["user_id"] = "owner"
        return await handler(request)

    app = web.Application(middlewares=[infra.error_middleware, fake_auth, infra.make_rate_limit_middleware(buckets)])
    app.router.add_get("/api/ok", ok)
    app.router.add_post("/api/chat", ok)
    app.router.add_get("/api/boom", boom)
    app.router.add_get("/api/forbidden", teapot)
    app.on_response_prepare.append(infra.add_security_headers)
    return app


class Http(unittest.TestCase):
    def run_client(self, coro_fn, buckets=None):
        async def go():
            async with TestClient(TestServer(make_app(buckets))) as client:
                return await coro_fn(client)
        return asyncio.run(go())

    def test_security_headers_and_request_id(self):
        async def case(c):
            r = await c.get("/api/ok")
            self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
            self.assertIn("frame-ancestors 'none'", r.headers["Content-Security-Policy"])
            self.assertEqual(r.headers["Cache-Control"], "private, no-store")
            self.assertEqual(len(r.headers["X-Request-Id"]), 16)
            r2 = await c.get("/api/ok", headers={"X-Request-Id": "abc12345def"})
            self.assertEqual(r2.headers["X-Request-Id"], "abc12345def")
            bad = await c.get("/api/ok", headers={"X-Request-Id": "x" * 100})
            self.assertNotEqual(bad.headers["X-Request-Id"], "x" * 100)
        self.run_client(case)

    def test_unexpected_exception_is_a_safe_json_500(self):
        async def case(c):
            r = await c.get("/api/boom")
            body = await r.json()
            self.assertEqual(r.status, 500)
            self.assertEqual(body["error"], "internal_error")
            self.assertNotIn("secret", json.dumps(body))
            self.assertEqual(body["request_id"], r.headers["X-Request-Id"])
            self.assertEqual((await c.get("/api/forbidden")).status, 403)   # HTTP exceptions pass through
        self.run_client(case)

    def test_rate_limit_returns_429_with_retry_after(self):
        clock = Clock()
        buckets = infra.TokenBuckets(clock=clock)
        async def case(c):
            statuses = [(await c.post("/api/chat")).status for _ in range(22)]
            self.assertEqual(statuses[:20], [200] * 20)
            self.assertEqual(statuses[20], 429)
            r = await c.post("/api/chat")
            self.assertGreaterEqual(int(r.headers["Retry-After"]), 1)
            self.assertEqual((await r.json())["error"], "rate_limited")
            self.assertEqual((await c.get("/api/ok")).status, 200)        # other routes unaffected
            clock.t += 4
            self.assertEqual((await c.post("/api/chat")).status, 200)
        self.run_client(case, buckets)

    def test_client_key_ignores_spoofable_leading_forwarded_entries(self):
        class R:
            headers = {"X-Forwarded-For": "1.1.1.1, 5.6.7.8"}   # attacker-supplied first, proxy-appended last
            remote = "10.0.0.1"
        self.assertEqual(infra.client_key(R()), "5.6.7.8")
        R.headers = {}
        self.assertEqual(infra.client_key(R()), "10.0.0.1")


if __name__ == "__main__":
    unittest.main()
