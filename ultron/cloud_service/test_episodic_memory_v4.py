"""V4 deterministic and disposable-PostgreSQL contracts, not device testing."""
from __future__ import annotations

import asyncio
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from episodic_memory_v4 import (
    _web_only, create_episode, correct_episode, delete_episode, episode_history,
    episode_recall_window, episode_search_terms, format_episode_context, is_episode_recall_request,
    list_episodes, load_episode_recall_context, search_episodes,
    register_routes, validate_episode,
)
from memory_history import validate_memory_record

HERE = Path(__file__).resolve().parent
DB = os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL", "")
try:
    import asyncpg
except ImportError:
    asyncpg = None

STAMP = "2026-10-13T09:30:00+03:00"


class SecurityRequest(dict):
    def __init__(self, auth_kind="web", method="POST", headers=None,
                 content_type="application/json"):
        super().__init__(auth_kind=auth_kind)
        self.method = method
        self.headers = headers or {}
        self.content_type = content_type


class EpisodicValidationTests(unittest.TestCase):
    def test_explicit_episode_recall_phrases_and_time_windows(self):
        from conversation_persona import classify_intent

        cases = (
            "Geçen hafta ne konuşmuştuk?",
            "Dün hangi görevi tamamlamıştık?",
            "Geçen sefer verdiğim son kararı hatırla.",
            "Son 14 gün ne yaptık?",
            "What did we work on last week?",
            "What did we work on in the past 30 days?",
            "What was my last project decision?",
        )
        for text in cases:
            with self.subTest(text=text):
                self.assertTrue(is_episode_recall_request(text))
                self.assertEqual(classify_intent(text).kind, "episode_recall")
        self.assertFalse(is_episode_recall_request("Geçen hafta hava nasıldı?"))
        self.assertFalse(is_episode_recall_request("Son 0 gün ne yaptık?"))
        self.assertFalse(is_episode_recall_request("Son 366 gün ne yaptık?"))
        self.assertIn("gorev", episode_search_terms("Dün hangi görevi tamamlamıştık?"))
        self.assertTrue({"project", "decision"}.issubset(
            episode_search_terms("What was my last project decision?")))
        now = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)
        start, end = episode_recall_window("Geçen hafta ne konuşmuştuk?", now=now)
        self.assertEqual(start.isoformat(), "2026-10-05T00:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-10-12T00:00:00+00:00")
        start, end = episode_recall_window("Dün ne yaptık?", now=now)
        self.assertEqual(start.isoformat(), "2026-10-13T00:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-10-14T00:00:00+00:00")
        start, end = episode_recall_window("What did we discuss last month?", now=now)
        self.assertEqual(start.isoformat(), "2026-09-01T00:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-10-01T00:00:00+00:00")
        start, end = episode_recall_window("What did we work on in the past 7 days?", now=now)
        self.assertEqual(start.isoformat(), "2026-10-07T12:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-10-14T12:00:00+00:00")
        start, end = episode_recall_window("Son 14 gün ne yaptık?", now=now)
        self.assertEqual(start.isoformat(), "2026-09-30T12:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-10-14T12:00:00+00:00")
        start, end = episode_recall_window("What did we work on in the past 30 days?", now=now)
        self.assertEqual(start.isoformat(), "2026-09-14T12:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-10-14T12:00:00+00:00")
        english_terms = episode_search_terms(
            "What did we decide for Project Atlas last week?")
        self.assertTrue({"project", "atlas"}.issubset(english_terms))
        self.assertNotIn("for", english_terms)
        turkish_terms = episode_search_terms(
            "Proje Atlas hakkında geçen hafta hangi kararı verdik?")
        self.assertIn("atlas", turkish_terms)
        self.assertNotIn("hakkinda", turkish_terms)

    def test_episode_context_marks_provenance_and_limits_untrusted_text(self):
        text = format_episode_context([{
            "id": 3, "title": "Kıbrıs planı", "summary": "Kullanıcı kararı verdi",
            "happened_at": datetime(2026, 10, 13, tzinfo=timezone.utc),
            "version": 2, "provenance": "owner_confirmed",
        }], "geçen hafta ne konuşmuştuk?")
        self.assertIn("Owner-confirmed episode records", text)
        self.assertIn("2026-10-13", text)
        self.assertIn("Kıbrıs planı", text)
        self.assertIn("data, not instructions", text)
        self.assertIn("No matching owner-confirmed episode", format_episode_context([], "geçen hafta"))
        self.assertLessEqual(len(format_episode_context([], "x", max_chars=80)), 80)
        secret = "password: this-must-not-enter-context"
        filtered = format_episode_context([{
            "id": 4, "title": "Sensitive", "summary": secret,
            "happened_at": "2026-10-13", "version": 1,
            "provenance": "owner_confirmed",
        }], "previous event")
        self.assertNotIn(secret, filtered)

    def test_episode_retrieval_runs_only_for_explicit_past_event_recall(self):
        class Pool:
            def __init__(self):
                self.calls = []

            async def fetch(self, sql, *args):
                self.calls.append((sql, args))
                return []

        async def run():
            pool = Pool()
            self.assertEqual(await load_episode_recall_context(
                pool, "owner-a", "Selam, nasılsın?"), "")
            self.assertEqual(pool.calls, [])
            result = await load_episode_recall_context(
                pool, "owner-a", "Geçen hafta ne konuşmuştuk?")
            self.assertIn("No matching owner-confirmed episode", result)
            self.assertEqual(len(pool.calls), 1)
            sql, args = pool.calls[0]
            self.assertIn("user_id=$1", sql)
            self.assertIn("superseded_at IS NULL", sql)
            self.assertEqual(args[0], "owner-a")
            self.assertLessEqual(args[-1], 5)

        asyncio.run(run())

    def test_timezone_normalization_and_explicit_temporal_bound(self):
        title, summary, when = validate_episode(
            "  İlk toplantı  ", "  Plan onaylandı  ", STAMP,
            now=datetime(2026, 10, 14, tzinfo=timezone.utc),
        )
        self.assertEqual(title, "İlk toplantı")
        self.assertEqual(summary, "Plan onaylandı")
        self.assertEqual(when.isoformat(), "2026-10-13T06:30:00+00:00")
        for invalid in ("2026-10-13T09:30:00", "not-a-date", "2999-10-01T00:00:00Z"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_episode("Meeting", "Notes", invalid)
        with self.assertRaisesRegex(ValueError, "invalid_episode_text"):
            validate_episode("Meet\x00ing", "Notes", STAMP)

    def test_sensitive_content_rejected_in_title_and_summary(self):
        cases = [
            ("password: never-store", "summary"),
            ("Meeting", "Bearer abcdefghijklmnopqrstuvwxyz"),
            ("sk-proj-abcdefghijklmno", "summary"),
            ("Token", "api key: secret"),
        ]
        for title, summary in cases:
            with self.subTest(title=title), self.assertRaisesRegex(ValueError, "sensitive"):
                validate_episode(title, summary, STAMP)

    def test_memory_v3_key_secret_fence(self):
        with self.assertRaisesRegex(ValueError, "sensitive"):
            validate_memory_record("FACT", "password: supersecret", "harmless")

    def test_only_web_auth_may_reach_episode_api(self):
        for kind in ("device", "", "admin"):
            with self.subTest(auth=kind), self.assertRaises(web.HTTPForbidden):
                _web_only({"auth_kind": kind})
        with patch.dict("os.environ", {"ULTRON_PUBLIC_ORIGIN": "https://ultron-yubh.onrender.com"}):
            with self.assertRaises(web.HTTPForbidden):
                _web_only(SecurityRequest(headers={"Sec-Fetch-Site": "same-origin"}))
            with self.assertRaises(web.HTTPForbidden):
                _web_only(SecurityRequest(headers={"Sec-Fetch-Site": "cross-site",
                                                 "Origin": "https://ultron-yubh.onrender.com"}))
            with self.assertRaises(web.HTTPForbidden):
                _web_only(SecurityRequest(headers={"Sec-Fetch-Site": "same-origin",
                                                 "Origin": "https://attacker.example"}))
            with self.assertRaises(web.HTTPUnsupportedMediaType):
                _web_only(SecurityRequest(headers={"Origin": "https://ultron-yubh.onrender.com"},
                                          content_type="text/plain"))
            _web_only(SecurityRequest(headers={"Sec-Fetch-Site": "same-origin",
                                             "Origin": "https://ultron-yubh.onrender.com"}))


@unittest.skipUnless(DB and asyncpg, "requires disposable PostgreSQL")
class EpisodicPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = await asyncpg.create_pool(DB, min_size=1, max_size=3)
        await self.pool.execute(HERE.joinpath("schema.sql").read_text(encoding="utf-8"))
        await self.pool.execute("DELETE FROM episodic_memories WHERE user_id LIKE 'ci-episode-v4-%'")
        await self.pool.execute("DELETE FROM events WHERE user_id LIKE 'ci-episode-v4-%'")

    async def asyncTearDown(self):
        await self.pool.execute("DELETE FROM episodic_memories WHERE user_id LIKE 'ci-episode-v4-%'")
        await self.pool.execute("DELETE FROM events WHERE user_id LIKE 'ci-episode-v4-%'")
        await self.pool.close()

    async def test_real_api_requires_web_session_same_origin_and_explicit_consent(self):
        from app import auth_middleware, create_session_cookie

        owner = "ci-episode-v4-api"
        application = web.Application(middlewares=[auth_middleware])
        application["db"] = self.pool
        register_routes(application)
        client = TestClient(TestServer(application))
        self.addAsyncCleanup(client.close)
        secret = "test-only-session-secret-not-a-real-credential"
        with patch.dict("os.environ", {
            "ULTRON_SESSION_SECRET": secret,
            "ULTRON_PUBLIC_ORIGIN": "https://ultron-yubh.onrender.com",
            "ULTRON_DEVICE_TOKEN": "test-only-device-token",
        }):
            await client.start_server()
            cookie = f"ultron_session={create_session_cookie(owner)}"
            body = {"title": "Approved event", "summary": "A decision was recorded",
                    "happened_at": STAMP, "owner_confirmed": True}
            denied = await client.post("/api/episodes", json=body, headers={
                "Cookie": cookie, "Origin": "https://attacker.example",
                "Sec-Fetch-Site": "cross-site",
            })
            self.assertEqual(denied.status, 403)
            missing_origin = await client.post("/api/episodes", json=body, headers={
                "Cookie": cookie, "Sec-Fetch-Site": "same-origin",
            })
            self.assertEqual(missing_origin.status, 403)
            missing_consent = await client.post("/api/episodes", json={
                **body, "owner_confirmed": False,
            }, headers={"Cookie": cookie, "Origin": "https://ultron-yubh.onrender.com",
                        "Sec-Fetch-Site": "same-origin"})
            self.assertEqual(missing_consent.status, 400)
            oversized = await client.post("/api/episodes", data=b" " * 8193, headers={
                "Cookie": cookie, "Origin": "https://ultron-yubh.onrender.com",
                "Sec-Fetch-Site": "same-origin", "Content-Type": "application/json",
            })
            self.assertEqual(oversized.status, 413)
            self.assertEqual(await self.pool.fetchval(
                "SELECT count(*) FROM episodic_memories WHERE user_id=$1", owner
            ), 0)
            accepted = await client.post("/api/episodes", json=body, headers={
                "Cookie": cookie, "Origin": "https://ultron-yubh.onrender.com",
                "Sec-Fetch-Site": "same-origin",
            })
            self.assertEqual(accepted.status, 201, await accepted.text())
            episode_id = (await accepted.json())["episode"]["id"]
            corrected = await client.put(f"/api/episodes/{episode_id}", json={
                "title": "Corrected event", "summary": "Owner corrected the date",
                "happened_at": STAMP, "owner_confirmed": True,
            }, headers={"Cookie": cookie, "Origin": "https://ultron-yubh.onrender.com",
                       "Sec-Fetch-Site": "same-origin"})
            self.assertEqual(corrected.status, 200)
            listed = await client.get("/api/episodes", headers={
                "Cookie": cookie, "Origin": "https://ultron-yubh.onrender.com",
                "Sec-Fetch-Site": "same-origin",
            })
            item = (await listed.json())["episodes"][0]
            self.assertEqual(listed.status, 200)
            self.assertEqual(item["version"], 2)
            self.assertNotIn("user_id", item)
            self.assertNotIn("search_text", item)
            other_cookie = f"ultron_session={create_session_cookie(owner + '-other')}"
            isolated = await client.get("/api/episodes", headers={
                "Cookie": other_cookie, "Origin": "https://ultron-yubh.onrender.com",
                "Sec-Fetch-Site": "same-origin",
            })
            self.assertEqual((await isolated.json())["episodes"], [])
            history = await client.get(f"/api/episodes/{episode_id}/history", headers={
                "Cookie": cookie, "Origin": "https://ultron-yubh.onrender.com",
                "Sec-Fetch-Site": "same-origin",
            })
            self.assertEqual([row["version"] for row in (await history.json())["history"]], [2, 1])
            cross_site_read = await client.get("/api/episodes", headers={
                "Cookie": cookie, "Origin": "https://attacker.example",
                "Sec-Fetch-Site": "cross-site",
            })
            self.assertEqual(cross_site_read.status, 403)
            device = await client.get("/api/episodes", headers={
                "Authorization": "Bearer test-only-device-token",
                "Cookie": cookie, "Origin": "https://ultron-yubh.onrender.com",
            })
            self.assertEqual(device.status, 403)
            self.assertEqual(await self.pool.fetchval(
                "SELECT count(*) FROM episodic_memories WHERE user_id=$1", owner
            ), 2)
            deleted = await client.delete(f"/api/episodes/{episode_id}", headers={
                "Cookie": cookie, "Origin": "https://ultron-yubh.onrender.com",
                "Sec-Fetch-Site": "same-origin",
            })
            self.assertEqual(deleted.status, 200)
            self.assertEqual(await self.pool.fetchval(
                "SELECT count(*) FROM episodic_memories WHERE user_id=$1", owner
            ), 0)
            self.assertGreater(episode_id, 0)

    async def test_timeline_owner_isolation_correction_and_full_erase(self):
        first = await create_episode(
            self.pool, "ci-episode-v4-a", "phone", "Lesson", "Started a new project", STAMP
        )
        await create_episode(
            self.pool, "ci-episode-v4-b", "phone", "Private", "Another owner's memory", STAMP
        )
        self.assertEqual(len(await list_episodes(self.pool, "ci-episode-v4-a")), 1)
        self.assertEqual(
            await episode_history(self.pool, "ci-episode-v4-b", first["id"]), []
        )
        self.assertIsNone(await correct_episode(
            self.pool, "ci-episode-v4-b", "phone", first["id"],
            "Changed", "Should never happen", STAMP,
        ))
        updated = await correct_episode(
            self.pool, "ci-episode-v4-a", "phone", first["id"],
            "Lesson corrected", "Owner changed the details", STAMP,
        )
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["series_id"], first["series_id"])
        current = await list_episodes(self.pool, "ci-episode-v4-a")
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["id"], updated["id"])
        chain = await episode_history(self.pool, "ci-episode-v4-a", first["id"])
        self.assertEqual([x["version"] for x in chain], [2, 1])
        self.assertIsNone(await correct_episode(
            self.pool, "ci-episode-v4-a", "phone", first["id"], "Stale", "old id", STAMP,
        ))
        self.assertFalse(await delete_episode(self.pool, "ci-episode-v4-b", first["id"]))
        self.assertTrue(await delete_episode(self.pool, "ci-episode-v4-a", first["id"]))
        self.assertEqual(await episode_history(self.pool, "ci-episode-v4-a", first["id"]), [])
        self.assertEqual(await list_episodes(self.pool, "ci-episode-v4-a"), [])
        self.assertEqual(len(await list_episodes(self.pool, "ci-episode-v4-b")), 1)
        audit = await self.pool.fetch(
            "SELECT event_type,detail FROM events WHERE user_id=$1 ORDER BY id",
            "ci-episode-v4-a",
        )
        self.assertEqual([r["event_type"] for r in audit], [
            "episode_created", "episode_corrected", "episode_deleted",
        ])
        self.assertTrue(all("Started a new project" not in r["detail"] for r in audit))

    async def test_concurrent_corrections_allow_only_one_current_version(self):
        original = await create_episode(
            self.pool, "ci-episode-v4-a", "desktop", "Event", "Original", STAMP
        )
        results = await asyncio.gather(
            correct_episode(
                self.pool, "ci-episode-v4-a", "desktop", original["id"],
                "Event A", "A corrected", STAMP,
            ),
            correct_episode(
                self.pool, "ci-episode-v4-a", "phone", original["id"],
                "Event B", "B corrected", STAMP,
            ),
        )
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(len(await list_episodes(self.pool, "ci-episode-v4-a")), 1)
        history = await episode_history(self.pool, "ci-episode-v4-a", original["id"])
        self.assertEqual(len(history), 2)

    async def test_concurrent_correction_and_forget_never_resurrects_episode(self):
        for i in range(12):
            owner = f"ci-episode-v4-race-{i}"
            original = await create_episode(
                self.pool, owner, "phone", "Race", "Sensitive-free summary", STAMP
            )
            corrected, deleted = await asyncio.gather(
                correct_episode(self.pool, owner, "desktop", original["id"],
                                "Race fixed", "Updated safely", STAMP),
                delete_episode(self.pool, owner, original["id"]),
            )
            self.assertTrue(deleted)
            self.assertEqual(await list_episodes(self.pool, owner), [])
            self.assertEqual(await episode_history(self.pool, owner, original["id"]), [])

    async def test_search_is_owner_scoped_temporal_ranked_current_only_and_audited(self):
        await self.pool.execute(
            "DELETE FROM events WHERE user_id LIKE 'ci-episode-v4-search-%'"
        )
        owner = "ci-episode-v4-search-a"
        other = "ci-episode-v4-search-b"
        now = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)
        old = await create_episode(self.pool, owner, "phone", "Project Atlas",
                                   "Reviewed the rover battery and route", "2026-10-06T10:00:00Z")
        recent = await create_episode(self.pool, owner, "desktop", "Project Atlas",
                                      "Approved the final deployment map", "2026-10-08T10:00:00Z")
        await create_episode(self.pool, other, "phone", "Project Atlas",
                             "OTHER_OWNER_SECRET deployment map", "2026-10-08T10:00:00Z")
        await correct_episode(self.pool, owner, "phone", old["id"], "Old title",
                              "Superseded battery decision", "2026-10-06T10:00:00Z")
        rows = await search_episodes(self.pool, owner, "Project Atlas geçen hafta", now=now)
        self.assertEqual([row["id"] for row in rows], [recent["id"]])
        self.assertNotIn("OTHER_OWNER_SECRET", str(rows))
        self.assertNotIn("Superseded", str(rows))
        self.assertEqual(await self.pool.fetchval(
            "SELECT count(*) FROM events WHERE user_id=$1 AND event_type LIKE 'episode_%'", owner
        ), 3)
        audit = await self.pool.fetch(
            "SELECT detail FROM events WHERE user_id=$1 AND event_type LIKE 'episode_%'", owner
        )
        self.assertTrue(all("Atlas" not in row["detail"] and "battery" not in row["detail"]
                            for row in audit))

    async def test_schema_upgrade_preserves_existing_episode_rows_and_searches_them(self):
        owner = "ci-episode-v4-migration"
        await self.pool.execute("DROP INDEX IF EXISTS idx_episodes_current_search")
        await self.pool.execute("ALTER TABLE episodic_memories DROP COLUMN search_text")
        row = await self.pool.fetchrow(
            """INSERT INTO episodic_memories
               (user_id,series_id,version,title,summary,happened_at,provenance,device_id)
               VALUES($1,gen_random_uuid(),1,$2,$3,$4,'owner_confirmed','phone')
               RETURNING id""",
            owner, "GÖREV Atlas", "Geçmiş görev ve rota kararı", datetime(2026,10,7,tzinfo=timezone.utc),
        )
        await self.pool.execute(HERE.joinpath("schema.sql").read_text(encoding="utf-8"))
        found = await search_episodes(self.pool, owner, "Gorevi Atlas")
        self.assertEqual([item["id"] for item in found], [row["id"]])
        self.assertEqual(await self.pool.fetchval(
            "SELECT count(*) FROM episodic_memories WHERE user_id=$1", owner
        ), 1)


if __name__ == "__main__":
    unittest.main()
