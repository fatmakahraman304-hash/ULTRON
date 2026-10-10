"""Real disposable PostgreSQL tests for free iPhone <-> desktop chat lifecycle."""
import json
import os
import unittest
from pathlib import Path

try:
    import asyncpg
    from local_brain_bridge import post_local_chat,get_local_chat
except ImportError:
    asyncpg=None

DATABASE=os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL","")
SCHEMA=Path(__file__).with_name("schema.sql")


class Request(dict):
    def __init__(self,pool,owner="ci-local",body=None,id=""):
        super().__init__(user_id=owner,auth_kind="web",device_id="ci-iphone")
        async def memory(*args):
            return "The owner prefers concise Turkish."
        async def history(*args):
            return ""
        self.app={"db":pool,"local_memory_context":memory,"local_recent_context":history}
        self.body=body or {}
        self.match_info={"id":str(id)}

    async def json(self):
        return self.body


@unittest.skipUnless(bool(DATABASE and asyncpg),"requires disposable Postgres and aiohttp")
class LocalChatPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool=await asyncpg.create_pool(DATABASE,min_size=1,max_size=4)
        async with self.pool.acquire() as db:
            await db.execute(SCHEMA.read_text(encoding="utf-8"))
            await db.execute("DELETE FROM local_chat_requests WHERE user_id LIKE 'ci-local%'")
            await db.execute("DELETE FROM device_commands WHERE user_id LIKE 'ci-local%'")
            await db.execute("DELETE FROM messages WHERE user_id LIKE 'ci-local%'")
            await db.execute("DELETE FROM conversations WHERE user_id LIKE 'ci-local%'")
            await db.execute("DELETE FROM device_presence WHERE user_id LIKE 'ci-local%'")

    async def asyncTearDown(self):
        await self.pool.close()

    async def online(self):
        await self.pool.execute(
            "INSERT INTO device_presence(user_id,device,state) VALUES('ci-local','desktop','{\"local_chat_ready\":true}'::jsonb)"
            " ON CONFLICT(user_id,device) DO UPDATE SET last_seen=NOW(),state=EXCLUDED.state"
        )

    async def test_offline_does_not_fall_back_to_gemini(self):
        response=await post_local_chat(Request(self.pool,body={"message":"Merhaba"}))
        self.assertEqual(response.status,409)
        self.assertIn("desktop_offline",response.text)
        self.assertEqual(await self.pool.fetchval(
            "SELECT COUNT(*) FROM device_commands WHERE user_id='ci-local'"),0)

    async def test_online_without_ollama_readiness_rejects_before_any_write(self):
        await self.online()
        for state in ({}, {"local_chat_ready":False}, {"local_chat_ready":"true"}):
            await self.pool.execute("UPDATE device_presence SET state=$1::jsonb WHERE user_id='ci-local'",json.dumps(state))
            result=await post_local_chat(Request(self.pool,body={"message":"Merhaba"}))
            self.assertEqual(result.status,409)
            self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM device_commands WHERE user_id='ci-local'"),0)
            self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM messages WHERE user_id='ci-local'"),0)

    async def test_exact_one_reply_persisted_after_verified_queue_result(self):
        await self.online()
        created=await post_local_chat(Request(self.pool,body={"message":"Merhaba ULTRON"}))
        self.assertEqual(created.status,202)
        body=json.loads(created.text)
        command_id=body["command_id"]
        self.assertEqual(body["provider"],"local")
        job=await self.pool.fetchrow("SELECT payload,status FROM device_commands WHERE id=$1",command_id)
        self.assertEqual(json.loads(job["payload"])["mode"],"local_brain")
        self.assertEqual(job["status"],"queued")
        self.assertIn("Turkish",json.loads(job["payload"])["system"])
        # Untrusted other owner cannot read any response.
        hidden=await get_local_chat(Request(self.pool,owner="ci-local-other",id=command_id))
        self.assertEqual(hidden.status,404)
        waiting=await get_local_chat(Request(self.pool,id=command_id))
        self.assertEqual(json.loads(waiting.text)["status"],"queued")
        # Simulate the desktop's *authenticated* complete endpoint persisting a result.
        await self.pool.execute(
            "UPDATE device_commands SET status='completed',result=$1::jsonb WHERE id=$2",
            json.dumps({"assistant_reply":"Merhaba efendim.","model":"qwen3:4b"}),command_id
        )
        first=await get_local_chat(Request(self.pool,id=command_id))
        self.assertEqual(first.status,200)
        self.assertEqual(json.loads(first.text)["reply"],"Merhaba efendim.")
        second=await get_local_chat(Request(self.pool,id=command_id))
        self.assertEqual(second.status,200)
        self.assertEqual(await self.pool.fetchval(
            "SELECT COUNT(*) FROM messages WHERE user_id='ci-local' "
            "AND device_id='desktop-local-ollama'"),1)

    async def test_bad_payload_and_session_directions(self):
        wrong=Request(self.pool,body={"message":"Merhaba"})
        wrong["auth_kind"]="device"
        from aiohttp import web
        with self.assertRaises(web.HTTPForbidden):
            await post_local_chat(wrong)
        await self.online()
        for message in ("","a"*3001):
            result=await post_local_chat(Request(self.pool,body={"message":message}))
            self.assertEqual(result.status,400)


if __name__=="__main__":
    unittest.main()
