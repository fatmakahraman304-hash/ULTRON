"""Disposable PostgreSQL integration for delivery-attempt fencing (never production DB)."""
import asyncio
import json
import os
import unittest
from pathlib import Path
from test_device_queue_contract import FakeRequest,HTTPConflict,HTTPNotFound,load_handlers
try:
    import asyncpg
except ImportError:
    asyncpg=None

DB=os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL","")

@unittest.skipUnless(DB and asyncpg is not None,"requires disposable PostgreSQL")
class DeviceQueuePostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool=await asyncpg.create_pool(DB,min_size=1,max_size=4)
        async with self.pool.acquire() as conn:
            await conn.execute(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
            await conn.execute("DELETE FROM device_commands WHERE user_id='owner'")
        self.handlers=load_handlers()

    async def asyncTearDown(self):
        await self.pool.close()

    async def add(self,command="agent_task"):
        return await self.pool.fetchval(
            "INSERT INTO device_commands(user_id,target,command,payload) VALUES('owner','desktop',$1,'{}'::jsonb) RETURNING id",command)

    async def claim(self):
        return (await self.handlers["claim_device_commands"](FakeRequest(self.pool,{"target":"desktop"})))["commands"]

    def req(self,cid,body):
        return FakeRequest(self.pool,body,command_id=str(cid))

    async def test_parallel_claim_keeps_single_agent_lane(self):
        await self.add();await self.add()
        first,second=await asyncio.gather(self.claim(),self.claim())
        rows=first+second
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["delivery_attempt"],1)
        active=await self.pool.fetchval("SELECT COUNT(*) FROM device_commands WHERE status='delivered'")
        self.assertEqual(active,1)

    async def test_stale_worker_cannot_finish_after_retry(self):
        cid=await self.add()
        self.assertEqual((await self.claim())[0]["delivery_attempt"],1)
        retry=await self.handlers["complete_device_command"](self.req(cid,{
            "delivery_attempt":1,"status":"failed","result":{"retryable":True,"message":"temporary"}}))
        self.assertEqual(retry["command"]["status"],"queued")
        await self.pool.execute("UPDATE device_commands SET run_after=NOW()-INTERVAL '1 second' WHERE id=$1",cid)
        self.assertEqual((await self.claim())[0]["delivery_attempt"],2)
        with self.assertRaises(HTTPConflict):
            await self.handlers["complete_device_command"](self.req(cid,{
                "delivery_attempt":1,"status":"completed","result":{"message":"stale"}}))
        result=await self.handlers["complete_device_command"](self.req(cid,{
            "delivery_attempt":2,"status":"completed","result":{"message":"fresh"}}))
        self.assertEqual(result["command"]["result"]["message"],"fresh")

    async def test_stale_worker_cannot_renew_progress_or_checkpoint(self):
        cid=await self.add()
        await self.claim()
        await self.pool.execute("UPDATE device_commands SET status='queued',delivered_at=NULL,run_after=NOW()-INTERVAL '1 second' WHERE id=$1",cid)
        self.assertEqual((await self.claim())[0]["delivery_attempt"],2)
        for stage in ("lease","executing"):
            with self.assertRaises(HTTPNotFound):
                await self.handlers["append_device_command_progress"](self.req(cid,{
                    "delivery_attempt":1,"stage":stage,"message":"stale"}))
        with self.assertRaises(HTTPNotFound):
            await self.handlers["save_device_command_checkpoint"](self.req(cid,{
                "delivery_attempt":1,"step_index":90,"state":{"stale":True}}))
        row=await self.pool.fetchrow("SELECT checkpoint,progress FROM device_commands WHERE id=$1",cid)
        checkpoint = json.loads(row["checkpoint"]) if isinstance(row["checkpoint"],str) else row["checkpoint"]
        progress = json.loads(row["progress"]) if isinstance(row["progress"],str) else row["progress"]
        self.assertEqual(checkpoint,{})
        self.assertFalse(any(v.get("message")=="stale" for v in progress))
        ok=await self.handlers["save_device_command_checkpoint"](self.req(cid,{
            "delivery_attempt":2,"step_index":2,"state":{"safe":True}}))
        self.assertEqual(ok["command"]["checkpoint"]["state"],{"safe":True})

    async def test_legacy_control_completion(self):
        cid=await self.add("wake")
        self.assertEqual((await self.claim())[0]["id"],cid)
        result=await self.handlers["complete_device_command"](self.req(cid,{
            "status":"completed","result":{"message":"awake"}}))
        self.assertEqual(result["command"]["status"],"completed")

if __name__=="__main__":
    unittest.main()
