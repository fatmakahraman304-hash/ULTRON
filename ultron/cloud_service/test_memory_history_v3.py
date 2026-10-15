"""Owner-scoped memory correction history; disposable PostgreSQL only."""
from __future__ import annotations

import os
import unittest
import asyncio
from pathlib import Path

from memory_history import (
    delete_owner_memory, list_owner_memory_history, upsert_owner_memory,
    validate_memory_record,
)
from personal_context_focus import (
    is_memory_history_request, load_focused_owner_context,
    select_memory_history_context,
)

HERE = Path(__file__).resolve().parent
DB = os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL", "")


class MemoryValidationTests(unittest.TestCase):
    def test_credentials_never_enter_current_or_history_memory(self):
        with self.assertRaisesRegex(ValueError, "sensitive"):
            validate_memory_record("FACT", "server", "password: never-store-this")
        with self.assertRaisesRegex(ValueError, "sensitive"):
            validate_memory_record("FACT", "api", "AIza0123456789abcdefghijkl")

    def test_old_values_are_included_only_as_explicitly_requested_historical_data(self):
        rows = [{"category": "PREFERENCE", "key": "theme", "value": "red",
                 "version": 1, "valid_until": "2026-10-13T00:00:00Z"}]
        self.assertTrue(is_memory_history_request("Önceki kararım neydi?"))
        self.assertTrue(is_memory_history_request("What was my previous decision?"))
        history = select_memory_history_context(rows, "previous decision")
        self.assertIn("OUTDATED PREFERENCE v1", history)
        self.assertIn("never current", history)
        self.assertFalse(is_memory_history_request("Selam, nasılsın?"))

    def test_legacy_secret_values_are_filtered_from_current_and_old_context(self):
        from personal_context_focus import select_personal_context
        memories = [{"category": "FACT", "key": "server", "value": "password: dont-show"},
                    {"category": "PREFERENCE", "key": "language", "value": "Türkçe"}]
        current = select_personal_context(memories, [], "server language")
        old = select_memory_history_context([
            {"category": "FACT", "key": "server", "value": "Bearer abcdefghijklmnopqrstuvwxyz",
             "version": 1, "valid_until": "2026-10-13"},
            {"category": "PREFERENCE", "key": "language", "value": "English",
             "version": 1, "valid_until": "2026-10-13"},
        ], "server language")
        self.assertNotIn("dont-show", current)
        self.assertIn("Türkçe", current)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", old)
        self.assertIn("English", old)

    def test_current_chat_context_does_not_query_or_include_superseded_values(self):
        class Pool:
            def __init__(self):
                self.history_queries = 0

            async def fetch(self, sql, *args):
                if "memory_history" in sql:
                    self.history_queries += 1
                    return [{"category": "PREFERENCE", "key": "theme", "value": "red",
                             "version": 1, "valid_until": "2026-10-13T00:00:00Z"}]
                if "owner_plans" in sql:
                    return []
                if "FROM memories" in sql:
                    return [{"category": "PREFERENCE", "key": "theme", "value": "blue"}]
                raise AssertionError(sql)

        pool = Pool()
        current = asyncio.run(load_focused_owner_context(pool, "owner-a", "Selam"))
        self.assertIn("blue", current)
        self.assertNotIn("red", current)
        self.assertEqual(pool.history_queries, 0)

        historical = asyncio.run(load_focused_owner_context(
            pool, "owner-a", "Önceki kararım neydi?"
        ))
        self.assertIn("blue", historical)
        self.assertIn("OUTDATED PREFERENCE v1", historical)
        self.assertIn("red", historical)
        self.assertEqual(pool.history_queries, 1)

    def test_unmatched_history_query_does_not_fall_back_to_unrelated_old_values(self):
        class Pool:
            async def fetch(self, sql, *args):
                if "memory_history" in sql:
                    self.assert_owner_scope(sql, args)
                    return []
                if "owner_plans" in sql:
                    return []
                if "FROM memories" in sql:
                    return []
                raise AssertionError(sql)

            @staticmethod
            def assert_owner_scope(sql, args):
                if "WHERE user_id=$1" not in sql or args[0] != "owner-a":
                    raise AssertionError("history query escaped owner scope")

        context = asyncio.run(load_focused_owner_context(
            Pool(), "owner-a", "What was my previous decision about engine X?"
        ))
        self.assertNotIn("OUTDATED", context)
        self.assertNotIn("other project", context)


try:
    import asyncpg
except ImportError:
    asyncpg = None


@unittest.skipUnless(DB and asyncpg, "requires disposable PostgreSQL")
class MemoryHistoryPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = await asyncpg.create_pool(DB, min_size=1, max_size=3)
        await self.pool.execute(HERE.joinpath("schema.sql").read_text(encoding="utf-8"))
        await self.pool.execute("DELETE FROM memory_history WHERE user_id LIKE 'ci-memv3-%'")
        await self.pool.execute("DELETE FROM memories WHERE user_id LIKE 'ci-memv3-%'")

    async def asyncTearDown(self):
        await self.pool.execute("DELETE FROM memory_history WHERE user_id LIKE 'ci-memv3-%'")
        await self.pool.execute("DELETE FROM memories WHERE user_id LIKE 'ci-memv3-%'")
        await self.pool.close()

    async def test_correction_preserves_owner_history_without_retrieving_it_as_current(self):
        first = await upsert_owner_memory(
            self.pool, "ci-memv3-a", "phone", "PREFERENCE", "theme", "red"
        )
        current = await upsert_owner_memory(
            self.pool, "ci-memv3-a", "phone", "PREFERENCE", "theme", "blue"
        )
        await upsert_owner_memory(
            self.pool, "ci-memv3-b", "phone", "PREFERENCE", "theme", "green"
        )
        history = await list_owner_memory_history(self.pool, "ci-memv3-a", "theme")
        other_history = await list_owner_memory_history(self.pool, "ci-memv3-b", "theme")
        self.assertEqual(first["version"], 1)
        self.assertEqual((current["value"], current["version"]), ("blue", 2))
        self.assertEqual([(r["value"], r["version"]) for r in history], [("red", 1)])
        self.assertEqual(other_history, [])
        row = await self.pool.fetchrow(
            "SELECT category,key,value,version FROM memories WHERE user_id=$1 AND key=$2",
            "ci-memv3-a", "theme",
        )
        self.assertEqual((row["value"], row["version"]), ("blue", 2))

    async def test_repeated_same_value_is_idempotent_and_delete_purges_history(self):
        await upsert_owner_memory(
            self.pool, "ci-memv3-a", "phone", "FACT", "car", "C180"
        )
        second = await upsert_owner_memory(
            self.pool, "ci-memv3-a", "phone", "FACT", "car", "E220d"
        )
        repeated = await upsert_owner_memory(
            self.pool, "ci-memv3-a", "phone", "FACT", "car", "E220d"
        )
        self.assertEqual(second["version"], 2)
        self.assertEqual(repeated["version"], 2)
        self.assertEqual(len(await list_owner_memory_history(
            self.pool, "ci-memv3-a", "car")), 1)
        self.assertTrue(await delete_owner_memory(self.pool, "ci-memv3-a", "car"))
        self.assertEqual(await list_owner_memory_history(
            self.pool, "ci-memv3-a", "car"), [])
        self.assertIsNone(await self.pool.fetchrow(
            "SELECT 1 FROM memories WHERE user_id=$1 AND key=$2",
            "ci-memv3-a", "car",
        ))

    async def test_concurrent_corrections_preserve_a_single_serial_history(self):
        await upsert_owner_memory(self.pool, "ci-memv3-a", "phone", "FACT", "color", "red")
        await asyncio.gather(
            upsert_owner_memory(self.pool, "ci-memv3-a", "phone", "FACT", "color", "blue"),
            upsert_owner_memory(self.pool, "ci-memv3-a", "phone", "FACT", "color", "green"),
        )
        current = await self.pool.fetchrow(
            "SELECT value,version FROM memories WHERE user_id=$1 AND key='color'",
            "ci-memv3-a",
        )
        history = await list_owner_memory_history(self.pool, "ci-memv3-a", "color")
        self.assertEqual(current["version"], 3)
        self.assertEqual(len(history), 2)
        self.assertEqual({row["value"] for row in history} | {current["value"]},
                         {"red", "blue", "green"})


if __name__ == "__main__":
    unittest.main()
