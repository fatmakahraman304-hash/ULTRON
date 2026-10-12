"""Real temporary PostgreSQL contract tests, never use production DATABASE_URL.

Run only with ULTRON_TEST_DATABASE_URL set to a CI service database.
No real Ollama, Render, user secrets, or external cloud requests.
"""
import json
import os
import uuid
import unittest
from pathlib import Path

import asyncpg
from aiohttp import web

from local_listening_bridge import post_local_listening_analysis, get_local_listening_analysis


TEST_URL = os.getenv("ULTRON_TEST_DATABASE_URL", "").strip()


class Request(dict):
    def __init__(self, pool, owner, body=None, task_id=1, kind="web"):
        super().__init__(auth_kind=kind,user_id=owner,device_id="iphone-test")
        self.app={"db":pool}
        self.match_info={"id":str(task_id)}
        self._body=body

    async def json(self):
        return self._body


@unittest.skipUnless(TEST_URL, "No isolated test PostgreSQL configured")
class PostgresListeningContract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        if not TEST_URL:
            return
        self.pool=await asyncpg.create_pool(TEST_URL,min_size=1,max_size=3)
        schema=Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        await self.pool.execute(schema)
        self.owner="test-owner-"+uuid.uuid4().hex
        self.other="test-other-"+uuid.uuid4().hex
        self.ident=str(uuid.uuid4())
        self.input={"stage":"map","text":"Bu mimarlık projesinde sade renkleri konuşuyoruz.",
                    "part":1,"total":1,"request_id":self.ident}

    async def asyncTearDown(self):
        if not TEST_URL:
            return
        await self.pool.execute("DELETE FROM device_commands WHERE user_id=ANY($1::text[])",[self.owner,self.other])
        await self.pool.execute("DELETE FROM device_presence WHERE user_id=ANY($1::text[])",[self.owner,self.other])
        await self.pool.close()

    async def enable_worker(self,owner=None,local=True):
        await self.pool.execute(
            "INSERT INTO device_presence(user_id,device,state,last_seen) "
            "VALUES($1,'desktop',$2::jsonb,NOW()) "
            "ON CONFLICT (user_id,device) DO UPDATE SET state=EXCLUDED.state,last_seen=NOW()",
            owner or self.owner,
            json.dumps({"local_listening_analysis_ready":local}),
        )

    async def queue(self,owner=None,body=None):
        return await post_local_listening_analysis(
            Request(self.pool,owner or self.owner,body or self.input)
        )

    async def test_capability_and_owner_isolation(self):
        no_worker=await self.queue()
        self.assertEqual(no_worker.status,409)
        self.assertEqual(json.loads(no_worker.body)["error"],"local_analysis_offline")
        await self.enable_worker()
        queued=await self.queue()
        self.assertEqual(queued.status,202)
        job=json.loads(queued.body)["id"]
        foreign=await get_local_listening_analysis(Request(self.pool,self.other,task_id=job))
        self.assertEqual(foreign.status,404)
        with self.assertRaises(web.HTTPForbidden):
            await get_local_listening_analysis(Request(self.pool,self.owner,task_id=job,kind="device"))

    async def test_same_uuid_retries_do_not_duplicate_queue_rows(self):
        await self.enable_worker()
        first=await self.queue()
        self.assertEqual(first.status,202)
        second=await self.queue()
        self.assertEqual(second.status,202)
        a=json.loads(first.body);b=json.loads(second.body)
        self.assertEqual(a["id"],b["id"])
        self.assertTrue(b["replayed"])
        rows=await self.pool.fetchval(
            "SELECT COUNT(*) FROM device_commands WHERE user_id=$1",self.owner)
        self.assertEqual(rows,1)
        changed={**self.input,"text":"Başka içerik"}
        conflict=await self.queue(body=changed)
        self.assertEqual(conflict.status,409)

    async def test_verified_local_reply_scrubs_raw_text_without_memory_or_message_writes(self):
        await self.enable_worker()
        created=await self.queue()
        command_id=json.loads(created.body)["id"]
        before=await self.pool.fetchval("SELECT payload->>'text' FROM device_commands WHERE id=$1",command_id)
        self.assertIn("mimarlık",before.lower())
        await self.pool.execute(
            "UPDATE device_commands SET status='completed',completed_at=NOW(),result=$2::jsonb WHERE id=$1",
            command_id,
            json.dumps({"provider":"local-ollama","model":"qwen3:4b","stage":"map",
                        "analysis":"Karar: sade mimarlık."}),
        )
        result=await get_local_listening_analysis(Request(self.pool,self.owner,task_id=command_id))
        self.assertEqual(result.status,200)
        data=json.loads(result.body)
        self.assertEqual(data["analysis"],"Karar: sade mimarlık.")
        self.assertEqual(data["provider"],"local-ollama")
        fields=await self.pool.fetchrow(
            "SELECT payload ? 'text' AS text_saved,payload ? 'system' AS system_saved "
            "FROM device_commands WHERE id=$1",command_id)
        self.assertFalse(fields["text_saved"])
        self.assertFalse(fields["system_saved"])
        for table in ("messages","memories","events"):
            count=await self.pool.fetchval(
                f"SELECT COUNT(*) FROM {table} WHERE user_id=$1",self.owner)
            self.assertEqual(count,0,table)

    async def test_expired_job_is_undeliverable_and_scrubbed(self):
        await self.enable_worker()
        created=await self.queue()
        ident=json.loads(created.body)["id"]
        await self.pool.execute(
            "UPDATE device_commands SET created_at=NOW()-INTERVAL '31 minutes' WHERE id=$1",ident)
        result=await get_local_listening_analysis(Request(self.pool,self.owner,task_id=ident))
        self.assertEqual(result.status,200)
        self.assertEqual(json.loads(result.body)["status"],"expired")
        row=await self.pool.fetchrow(
            "SELECT status,payload FROM device_commands WHERE id=$1",ident)
        self.assertEqual(row["status"],"expired")
        self.assertNotIn("text",json.loads(row["payload"]))
        self.assertNotIn("system",json.loads(row["payload"]))

    async def test_invalid_model_is_never_accepted(self):
        await self.enable_worker()
        ident=json.loads((await self.queue()).body)["id"]
        await self.pool.execute(
            "UPDATE device_commands SET status='completed',result=$2::jsonb WHERE id=$1",
            ident,json.dumps({"provider":"local-ollama","model":"llava:7b",
                              "stage":"map","analysis":"Fake"}))
        result=await get_local_listening_analysis(Request(self.pool,self.owner,task_id=ident))
        self.assertEqual(result.status,502)
        self.assertEqual(json.loads(result.body)["error"],"invalid_local_analysis")


if __name__=="__main__":
    unittest.main()
