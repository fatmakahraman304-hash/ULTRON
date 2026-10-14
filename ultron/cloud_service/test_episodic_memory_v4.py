"""V4 deterministic and disposable-PostgreSQL contracts, not device testing."""
from __future__ import annotations

import asyncio
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

from aiohttp import web
from episodic_memory_v4 import (
    _web_only, create_episode, correct_episode, delete_episode, episode_history,
    list_episodes, validate_episode,
)
from memory_history import validate_memory_record

HERE = Path(__file__).resolve().parent
DB = os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL", "")
try:
    import asyncpg
except ImportError:
    asyncpg = None

STAMP = "2026-10-13T09:30:00+03:00"


class EpisodicValidationTests(unittest.TestCase):
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
        _web_only({"auth_kind": "web"})


@unittest.skipUnless(DB and asyncpg, "requires disposable PostgreSQL")
class EpisodicPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = await asyncpg.create_pool(DB, min_size=1, max_size=3)
        await self.pool.execute(HERE.joinpath("schema.sql").read_text(encoding="utf-8"))
        await self.pool.execute("DELETE FROM episodic_memories WHERE user_id LIKE 'ci-episode-v4-%'")

    async def asyncTearDown(self):
        await self.pool.execute("DELETE FROM episodic_memories WHERE user_id LIKE 'ci-episode-v4-%'")
        await self.pool.close()

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


if __name__ == "__main__":
    unittest.main()
