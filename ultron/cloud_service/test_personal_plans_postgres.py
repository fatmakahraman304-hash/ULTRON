"""Disposable real PostgreSQL owner-plan ACL and lifecycle regression tests."""
import json
import os
import unittest
from pathlib import Path

try:
    import asyncpg
    from aiohttp import web
    from personal_plans import create_plan, list_plans, update_plan, set_plan_done, delete_plan, export_owner_plans_ics
except ImportError:
    asyncpg = None
    web = None

DB = os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL", "")


class Request(dict):
    def __init__(self, pool, owner="ci-plan-1", body=None, method="GET",
                 id="", auth="web", headers=None, content_type="application/json", query=None):
        super().__init__(user_id=owner, auth_kind=auth)
        self.app = {"db": pool}
        self.payload = body if body is not None else {}
        self.method = method
        self.match_info = {"id": str(id)}
        self.headers = headers or {}
        self.content_type = content_type
        self.query = query or {}

    async def json(self):
        return self.payload


@unittest.skipUnless(bool(DB and asyncpg and web), "disposable Postgres with aiohttp required")
class ManualPlanPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = await asyncpg.create_pool(DB, min_size=1, max_size=3)
        await self.pool.execute(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        await self.pool.execute("DELETE FROM owner_plans WHERE user_id LIKE 'ci-plan-%'")

    async def asyncTearDown(self):
        await self.pool.execute("DELETE FROM owner_plans WHERE user_id LIKE 'ci-plan-%'")
        await self.pool.close()

    async def test_create_read_done_undo_delete_with_isolation(self):
        data = {"title": "İngilizce dersim", "date": "2026-10-15",
                "time": "16:30", "note": "B2"}
        result = await create_plan(Request(self.pool, body=data, method="POST"))
        self.assertEqual(result.status, 201)
        p = json.loads(result.text)
        self.assertFalse(p["notification_sent"])
        pid = p["plan"]["id"]
        self.assertEqual(p["plan"]["scheduled_time"], "16:30")
        listing = await list_plans(Request(self.pool))
        self.assertEqual(len(json.loads(listing.text)["plans"]), 1)
        self.assertEqual(len(json.loads((await list_plans(
            Request(self.pool, owner="ci-plan-2"))).text)["plans"]), 0)
        for handler, method, body in [
            (update_plan, "PUT", {"title": "Başka kişinin planı", "date": "2026-10-20"}),
            (set_plan_done, "PATCH", {"is_done": True}),
            (delete_plan, "DELETE", {}),
        ]:
            with self.assertRaises(web.HTTPNotFound):
                await handler(Request(self.pool, owner="ci-plan-2", id=pid,
                                      method=method, body=body))
        edited = await update_plan(Request(self.pool, id=pid, method="PUT", body={
            "title": "Ders ertelendi", "date": "2026-10-23", "time": "18:45", "note": "Yeni oda"
        }))
        new = json.loads(edited.text)
        self.assertEqual(new["plan"]["id"], pid)
        self.assertEqual(new["plan"]["scheduled_date"], "2026-10-23")
        self.assertEqual(new["plan"]["scheduled_time"], "18:45")
        self.assertEqual(new["plan"]["note"], "Yeni oda")
        self.assertFalse(new["notification_sent"])
        verify = json.loads((await list_plans(Request(self.pool))).text)["plans"][0]
        self.assertEqual(verify["title"], "Ders ertelendi")
        self.assertEqual(verify["note"], "Yeni oda")
        done = await set_plan_done(Request(self.pool, id=pid, method="PATCH",
                                          body={"is_done": True}))
        self.assertTrue(json.loads(done.text)["plan"]["is_done"])
        undone = await set_plan_done(Request(self.pool, id=pid, method="PATCH",
                                            body={"is_done": False}))
        self.assertFalse(json.loads(undone.text)["plan"]["is_done"])
        deleted = await delete_plan(Request(self.pool, id=pid, method="DELETE"))
        self.assertTrue(json.loads(deleted.text)["deleted"])
        self.assertEqual(len(json.loads((await list_plans(Request(self.pool))).text)["plans"]), 0)

    async def test_denies_unauthenticated_or_cross_site_writes(self):
        data = {"title": "Test", "date": "2026-10-15"}
        with self.assertRaises(web.HTTPForbidden):
            await create_plan(Request(self.pool, body=data, method="POST", auth="device"))
        with self.assertRaises(web.HTTPForbidden):
            await create_plan(Request(self.pool, body=data, method="POST",
                                      headers={"Sec-Fetch-Site": "cross-site"}))
        with self.assertRaises(web.HTTPForbidden):
            await update_plan(Request(self.pool, id=1, body=data, method="PUT",
                                      headers={"Sec-Fetch-Site": "cross-site"}))
        with self.assertRaises(web.HTTPUnsupportedMediaType):
            await create_plan(Request(self.pool, body=data, method="POST",
                                      content_type="text/plain"))
        self.assertEqual(await self.pool.fetchval(
            "SELECT COUNT(*) FROM owner_plans WHERE user_id LIKE 'ci-plan-%'"), 0)

    async def test_explicit_ics_owner_scope_no_private_notes_or_alarm(self):
        data = {"title": "Ders; toplantı", "date": "2026-10-18",
                "time": "12:30", "note": "MY_PRIVATE_NOTE_002"}
        added = await create_plan(Request(self.pool, body=data, method="POST"))
        self.assertEqual(added.status, 201)
        a = await export_owner_plans_ics(Request(self.pool, query={"tz": "Europe/Istanbul"}))
        self.assertEqual(a.status, 200)
        self.assertTrue(a.content_type.startswith("text/calendar"))
        self.assertEqual(a.headers.get("Cache-Control"), "private, no-store")
        self.assertIn("attachment", a.headers.get("Content-Disposition", ""))
        text = a.body.decode("utf-8")
        self.assertIn("DTSTART:20261018T093000Z", text)
        self.assertIn("SUMMARY:Ders\\; toplantı", text)
        self.assertNotIn("MY_PRIVATE_NOTE_002", text)
        self.assertNotIn("VALARM", text)
        other = await export_owner_plans_ics(Request(self.pool, owner="ci-plan-2"))
        self.assertNotIn("BEGIN:VEVENT", other.body.decode("utf-8"))
        with self.assertRaises(web.HTTPForbidden):
            await export_owner_plans_ics(Request(self.pool, auth="device"))
        bad = await export_owner_plans_ics(Request(self.pool, query={"tz": "Invalid/Zone"}))
        self.assertEqual(bad.status, 400)

    async def test_rejects_invalid_fields_and_state(self):
        for item in [
            {"title": "Plan", "date": "2026-02-31"},
            {"title": "Plan", "date": "2026-11-05", "time": "89:00"},
            {"title": "", "date": "2026-11-05"},
        ]:
            resp = await create_plan(Request(self.pool, body=item, method="POST"))
            self.assertEqual(resp.status, 400)
        resp = await create_plan(Request(self.pool, body={"title": "Plan", "date": "2026-11-05"}, method="POST"))
        pid = json.loads(resp.text)["plan"]["id"]
        bad_edit = await update_plan(Request(self.pool, method="PUT", id=pid,
            body={"title": "Çöpe", "date": "2026-02-30"}))
        self.assertEqual(bad_edit.status, 400)
        self.assertEqual(await self.pool.fetchval(
            "SELECT title FROM owner_plans WHERE id=$1", pid), "Plan")
        bad = await set_plan_done(Request(self.pool, method="PATCH", id=pid, body={"is_done": "true"}))
        self.assertEqual(bad.status, 400)
        with self.assertRaises(web.HTTPBadRequest):
            await delete_plan(Request(self.pool, method="DELETE", id="1 OR 1=1"))


if __name__ == "__main__":
    unittest.main()
