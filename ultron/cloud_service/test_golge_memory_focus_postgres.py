"""Disposable PostgreSQL: real owner/thread-scoped continuation -> memory recall.

No Gemini, Qwen, UI automation, production DB or external credentials.
"""
from __future__ import annotations
import os
import unittest
import uuid
from pathlib import Path

try:
    import asyncpg
    from conversation_turns import load_contextual_thread_turns
    from personal_context_focus import (
        load_focused_owner_context, memory_focus_question
    )
except ImportError:
    asyncpg = None

HERE = Path(__file__).resolve().parent
DB = os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL", "")


@unittest.skipUnless(DB and asyncpg, "requires disposable PostgreSQL")
class OwnerMemoryFocusIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = await asyncpg.create_pool(DB, min_size=1, max_size=3)
        await self.pool.execute(HERE.joinpath("schema.sql").read_text(encoding="utf-8"))
        await self.pool.execute("DELETE FROM messages WHERE user_id LIKE 'ci-mfocus-%'")
        await self.pool.execute("DELETE FROM conversations WHERE user_id LIKE 'ci-mfocus-%'")
        await self.pool.execute("DELETE FROM memories WHERE user_id LIKE 'ci-mfocus-%'")
        self.conv = uuid.uuid4()
        self.other = uuid.uuid4()
        for ident, owner in [(self.conv,"ci-mfocus-a"),(self.other,"ci-mfocus-b")]:
            await self.pool.execute(
                "INSERT INTO conversations(id,user_id,title) VALUES($1,$2,'test')",
                ident, owner,
            )

    async def asyncTearDown(self):
        await self.pool.execute("DELETE FROM messages WHERE user_id LIKE 'ci-mfocus-%'")
        await self.pool.execute("DELETE FROM conversations WHERE user_id LIKE 'ci-mfocus-%'")
        await self.pool.execute("DELETE FROM memories WHERE user_id LIKE 'ci-mfocus-%'")
        await self.pool.close()

    async def test_long_continue_discovers_old_project_without_other_owner(self):
        await self.pool.execute(
            "INSERT INTO memories(user_id,category,key,value,updated_at) VALUES "
            "('ci-mfocus-a','PROJECT','Mercedes C180 2009','Ön fren bakımı',NOW()-INTERVAL '2 days'),"
            "('ci-mfocus-b','PROJECT','Mercedes C180 PRIVATE','OTHER_OWNER_SECRET',NOW())"
        )
        # Category is deliberately a constant to match the legacy schema.
        await self.pool.execute(
            "INSERT INTO memories(user_id,category,key,value) "
            "SELECT 'ci-mfocus-a','FACT','Unrelated record ' || n, "
            "'Unrelated value ' || n FROM generate_series(1,135) AS x(n)"
        )
        await self.pool.execute(
            "INSERT INTO messages(conversation_id,user_id,role,content) VALUES "
            "($1,'ci-mfocus-a','user','Mercedes C180 2009 fren bakımını geliştir'),"
            "($1,'ci-mfocus-a','assistant','İlk adımı tamamladım')",
            self.conv
        )
        for n in range(36):
            await self.pool.execute(
                "INSERT INTO messages(conversation_id,user_id,role,content) "
                "VALUES($1,'ci-mfocus-a','user','Devam et'),"
                "($1,'ci-mfocus-a','assistant',$2)",
                self.conv, "Adım %d" % n,
            )
        await self.pool.execute(
            "INSERT INTO messages(conversation_id,user_id,role,content) "
            "VALUES($1,'ci-mfocus-b','user','OTHER_OWNER_SECRET')",
            self.other
        )
        current = await self.pool.fetchval(
            "INSERT INTO messages(conversation_id,user_id,role,content) "
            "VALUES($1,'ci-mfocus-a','user','Devam et') RETURNING id", self.conv
        )
        turns = await load_contextual_thread_turns(
            self.pool, "ci-mfocus-a", self.conv,
            question="Devam et", before_id=current,
            max_chars=2600, limit=12,
        )
        focused_query = memory_focus_question("Devam et", turns)
        self.assertIn("Mercedes C180", focused_query)
        baseline = await load_focused_owner_context(
            self.pool, "ci-mfocus-a", "Devam et")
        self.assertNotIn("Mercedes C180 2009", baseline)
        better = await load_focused_owner_context(
            self.pool, "ci-mfocus-a", focused_query)
        self.assertIn("Mercedes C180 2009", better)
        self.assertNotIn("OTHER_OWNER_SECRET", better)
        self.assertLessEqual(len(better), 3400)
        other = await load_focused_owner_context(self.pool, "ci-mfocus-b", focused_query)
        self.assertNotIn("Ön fren bakımı", other)
        wrong_thread = await load_contextual_thread_turns(
            self.pool, "ci-mfocus-b", self.conv,
            question="Devam et", before_id=current,
        )
        self.assertEqual(wrong_thread, [])

    async def test_topic_switch_does_not_retrieve_previous_project(self):
        await self.pool.execute(
            "INSERT INTO messages(conversation_id,user_id,role,content) "
            "VALUES($1,'ci-mfocus-a','user','Mercedes C180 hakkında konuşalım'),"
            "($1,'ci-mfocus-a','assistant','Tamam')", self.conv
        )
        for n in range(16):
            await self.pool.execute(
                "INSERT INTO messages(conversation_id,user_id,role,content) "
                "VALUES($1,'ci-mfocus-a','user','Devam et'),"
                "($1,'ci-mfocus-a','assistant',$2)", self.conv, "Cevap %d"%n
            )
        await self.pool.execute(
            "INSERT INTO messages(conversation_id,user_id,role,content) "
            "VALUES($1,'ci-mfocus-a','user','Konuyu değiştir, eski işi bırak.'),"
            "($1,'ci-mfocus-a','assistant','Konu kapandı')", self.conv
        )
        current = await self.pool.fetchval(
            "INSERT INTO messages(conversation_id,user_id,role,content) "
            "VALUES($1,'ci-mfocus-a','user','Devam et') RETURNING id", self.conv
        )
        history = await load_contextual_thread_turns(
            self.pool,"ci-mfocus-a",self.conv,
            question="Devam et",before_id=current,max_chars=1800,limit=12
        )
        self.assertEqual(memory_focus_question("Devam et", history), "Devam et")


if __name__ == "__main__":
    unittest.main()
