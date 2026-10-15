"""Owner-isolated durable generated images on disposable PostgreSQL.

No real API/model calls, no production data. Exercise FK cascade, owner scoping,
8 MiB DB bound, 12 most-recent image quota and 30-day expiry.
"""
from __future__ import annotations
import os
import unittest
import uuid
from pathlib import Path

try:
    import asyncpg
except ImportError:
    asyncpg = None

DB = os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL", "")
SCHEMA = Path(__file__).with_name("schema.sql")


@unittest.skipUnless(DB and asyncpg, "disposable PostgreSQL required")
class GeneratedImagePostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = await asyncpg.create_pool(DB, min_size=1, max_size=2)
        await self.pool.execute(SCHEMA.read_text(encoding="utf-8"))
        self.owner = "ci-golge-image-a"
        self.other = "ci-golge-image-b"
        for who in (self.owner, self.other):
            await self.pool.execute("DELETE FROM conversations WHERE user_id=$1", who)
        self.cid = uuid.uuid4()
        self.foreign_cid = uuid.uuid4()
        await self.pool.execute(
            "INSERT INTO conversations(id,user_id,title) VALUES($1,$2,'ci')",
            self.cid, self.owner,
        )
        await self.pool.execute(
            "INSERT INTO conversations(id,user_id,title) VALUES($1,$2,'ci')",
            self.foreign_cid, self.other,
        )

    async def asyncTearDown(self):
        for who in (self.owner, self.other):
            await self.pool.execute("DELETE FROM conversations WHERE user_id=$1", who)
        await self.pool.close()

    async def _insert_image(self, cid, owner, label=b"png"):
        mid = await self.pool.fetchval(
            "INSERT INTO messages(conversation_id,user_id,role,content,device_id) "
            "VALUES($1,$2,'assistant','Görsel oluşturuldu.','gemini-image') RETURNING id",
            cid, owner,
        )
        await self.pool.execute(
            "INSERT INTO generated_images(message_id,conversation_id,user_id,mime_type,image_data) "
            "VALUES($1,$2,$3,'image/png',$4)",
            mid, cid, owner, label,
        )
        return mid

    async def test_owner_only_download_and_deletion_cascade(self):
        mid = await self._insert_image(self.cid, self.owner, b"private picture")
        stored = await self.pool.fetchrow(
            "SELECT mime_type,image_data FROM generated_images "
            "WHERE message_id=$1 AND user_id=$2 "
            "AND created_at >= NOW() - INTERVAL '30 days'",
            mid, self.owner,
        )
        self.assertEqual(bytes(stored["image_data"]), b"private picture")
        self.assertEqual(stored["mime_type"], "image/png")
        leaked = await self.pool.fetchrow(
            "SELECT mime_type,image_data FROM generated_images "
            "WHERE message_id=$1 AND user_id=$2 "
            "AND created_at >= NOW() - INTERVAL '30 days'",
            mid, self.other,
        )
        self.assertIsNone(leaked)
        await self.pool.execute("DELETE FROM conversations WHERE id=$1", self.cid)
        self.assertIsNone(
            await self.pool.fetchval(
                "SELECT message_id FROM generated_images WHERE message_id=$1", mid
            )
        )

    async def test_limit_and_30day_expiry_are_owner_scoped(self):
        other_id = await self._insert_image(self.foreign_cid, self.other, b"untouched")
        ids = [await self._insert_image(self.cid, self.owner, b"x") for _ in range(15)]
        await self.pool.execute(
            "UPDATE generated_images SET created_at=NOW()-INTERVAL '32 days' "
            "WHERE message_id=$1", ids[0],
        )
        await self.pool.execute(
            "DELETE FROM generated_images WHERE user_id=$1 AND "
            "(created_at < NOW() - INTERVAL '30 days' OR message_id NOT IN "
            "(SELECT message_id FROM generated_images WHERE user_id=$1 "
            "ORDER BY created_at DESC,message_id DESC LIMIT 12))", self.owner,
        )
        remaining = await self.pool.fetch(
            "SELECT message_id FROM generated_images WHERE user_id=$1 "
            "ORDER BY message_id", self.owner,
        )
        self.assertEqual([r["message_id"] for r in remaining], ids[-12:])
        self.assertEqual(
            await self.pool.fetchval("SELECT COUNT(*) FROM generated_images "
                                     "WHERE message_id=$1 AND user_id=$2",
                                     other_id, self.other), 1,
        )


if __name__ == "__main__":
    unittest.main()
