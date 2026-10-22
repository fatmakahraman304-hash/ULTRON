"""Shared HTTP client (retry, size cap, no redirects) and ops helpers (deep health, retention list)."""
import asyncio
import json
import unittest

from aiohttp import web
from aiohttp.test_utils import TestServer

import http_client
import ops


def run(c):
    return asyncio.run(c)


class Client(unittest.TestCase):
    def serve(self, case):
        hits = {"flaky": 0}

        async def flaky(request):
            hits["flaky"] += 1
            return web.Response(status=503) if hits["flaky"] == 1 else web.json_response({"ok": True})

        async def big(request):
            return web.Response(body=b"x" * 5000)

        async def redirect(request):
            raise web.HTTPFound("/secret")

        async def post_fail(request):
            hits["post"] = hits.get("post", 0) + 1
            return web.Response(status=503)

        app = web.Application()
        app.router.add_get("/flaky", flaky)
        app.router.add_get("/big", big)
        app.router.add_get("/redirect", redirect)
        app.router.add_post("/post", post_fail)

        async def go():
            async with TestServer(app) as server:
                try:
                    return await case(server, hits)
                finally:
                    await http_client.close()
        return asyncio.run(go())

    def test_retry_once_on_5xx_for_get(self):
        async def case(server, hits):
            status, body, _ = await http_client.fetch(str(server.make_url("/flaky")))
            self.assertEqual((status, json.loads(body), hits["flaky"]), (200, {"ok": True}, 2))
        self.serve(case)

    def test_post_is_never_retried(self):
        async def case(server, hits):
            status, _, _ = await http_client.fetch(str(server.make_url("/post")), method="POST", json_body={})
            self.assertEqual((status, hits["post"]), (503, 1))
        self.serve(case)

    def test_size_cap_and_no_redirect_following(self):
        async def case(server, hits):
            with self.assertRaises(ValueError):
                await http_client.fetch(str(server.make_url("/big")), max_bytes=1000)
            status, _, headers = await http_client.fetch(str(server.make_url("/redirect")))
            self.assertEqual((status, headers["Location"]), (302, "/secret"))
        self.serve(case)

    def test_session_is_reused_and_recreated_per_event_loop(self):
        async def two():
            a = http_client.session()
            return a, http_client.session()
        a, b = run(two())
        self.assertIs(a, b)
        c, _ = run(two())                      # new loop → new session, no "attached to a different loop" errors
        self.assertIsNot(a, c)
        run(http_client.close())


class FakePool:
    def __init__(self, ok=True):
        self.ok, self.sql = ok, []

    async def fetchval(self, sql, *a):
        if not self.ok:
            raise RuntimeError("db down")
        return 1

    async def execute(self, sql, *a):
        self.sql.append(sql)
        if "owner_alerts" in sql:
            raise RuntimeError("one table fails")
        return "DELETE 3"


class Ops(unittest.TestCase):
    def test_deep_health_reports_each_dependency(self):
        class Task:
            def __init__(self, done):
                self._d = done

            def done(self):
                return self._d
        import time
        good = run(ops.deep_health({"db": FakePool(), "proactive_task": Task(False), "dispatcher_status": {"last_tick_at": time.time()}}))
        self.assertTrue(good["ok"])
        stale = run(ops.deep_health({"db": FakePool(), "proactive_task": Task(False), "dispatcher_status": {"last_tick_at": time.time() - 600}}))
        self.assertFalse(stale["ok"])
        self.assertFalse(stale["checks"]["dispatcher_recent"])
        down = run(ops.deep_health({"db": FakePool(False), "proactive_task": Task(True)}))
        self.assertEqual((down["ok"], down["checks"]["database"], down["checks"]["dispatcher_running"]), (False, False, False))

    def test_maintenance_is_independent_per_table(self):
        result = run(ops.maintenance(FakePool()))
        self.assertEqual(result["owner_alerts"], -1)
        self.assertEqual(result["owner_reminders"], 3)
        self.assertEqual(len(result), len(ops.RETENTION))

    def test_retention_never_touches_pending_work_or_memory(self):
        joined = " ".join(sql for _, sql in ops.RETENTION).lower()
        self.assertNotIn("from memories", joined)
        self.assertNotIn("from messages", joined)
        self.assertIn("status in ('delivered','cancelled')", joined)       # pending reminders are never deleted
        self.assertIn("not active", joined)                                # active alerts are never deleted


if __name__ == "__main__":
    unittest.main()
