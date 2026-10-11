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

    async def test_busy_desktop_can_claim_controls_without_agent(self):
        agent_id = await self.add()
        wake_id = await self.add("wake")
        result = await self.handlers["claim_device_commands"](
            FakeRequest(self.pool, {"target": "desktop", "include_agent_tasks": False})
        )
        self.assertEqual([row["id"] for row in result["commands"]], [wake_id])
        row = await self.pool.fetchrow(
            "SELECT status, delivery_attempt FROM device_commands WHERE id=$1",
            agent_id,
        )
        self.assertEqual(row["status"], "queued")
        self.assertEqual(row["delivery_attempt"], 0)
        # A free local agent can subsequently claim that waiting task.
        claimed = await self.claim()
        self.assertEqual([row["id"] for row in claimed], [agent_id])

    async def test_lost_local_claim_response_retries_with_new_fence(self):
        # The browser request exists in Postgres but never reached the
        # laptop; only the server's initial 'claimed' progress is recorded.
        cid = await self.pool.fetchval(
            """INSERT INTO device_commands(user_id,target,command,payload)
               VALUES('owner','desktop','agent_task',
                      '{"mode":"local_brain","text":"test"}'::jsonb)
               RETURNING id"""
        )
        first = (await self.claim())[0]
        self.assertEqual(first["id"],cid)
        self.assertEqual(first["delivery_attempt"],1)
        await self.pool.execute(
            "UPDATE device_commands SET delivered_at=NOW()-INTERVAL '14 seconds' WHERE id=$1",
            cid,
        )
        second = (await self.claim())[0]
        self.assertEqual(second["id"],cid)
        self.assertEqual(second["delivery_attempt"],2)
        row=await self.pool.fetchrow(
            "SELECT retry_count,progress FROM device_commands WHERE id=$1",cid)
        progress = json.loads(row["progress"]) if isinstance(row["progress"], str) else row["progress"]
        stages=[item["stage"] for item in progress]
        self.assertEqual(row["retry_count"],1)
        self.assertIn("redelivery",stages)
        with self.assertRaises(HTTPNotFound):
            await self.handlers["append_device_command_progress"](
                self.req(cid,{"delivery_attempt":1,"stage":"executing"}))
        await self.handlers["append_device_command_progress"](
            self.req(cid,{"delivery_attempt":2,"stage":"executing","message":"started"}))
        await self.pool.execute(
            "UPDATE device_commands SET delivered_at=NOW()-INTERVAL '14 seconds' WHERE id=$1",
            cid,
        )
        # An acknowledged (possibly running) model is never auto-requeued.
        self.assertEqual(await self.claim(),[])
        check=await self.pool.fetchrow(
            "SELECT status,delivery_attempt,retry_count FROM device_commands WHERE id=$1",cid)
        self.assertEqual((check["status"],check["delivery_attempt"],check["retry_count"]),
                         ("delivered",2,1))

    async def test_general_agent_claim_is_not_replayed(self):
        cid=await self.add("agent_task")
        first=(await self.claim())[0]
        self.assertEqual(first["id"],cid)
        await self.pool.execute(
            "UPDATE device_commands SET delivered_at=NOW()-INTERVAL '14 seconds' WHERE id=$1",
            cid)
        self.assertEqual(await self.claim(),[])
        row=await self.pool.fetchrow(
            "SELECT status,retry_count FROM device_commands WHERE id=$1",cid)
        self.assertEqual((row["status"],row["retry_count"]),("delivered",0))

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
