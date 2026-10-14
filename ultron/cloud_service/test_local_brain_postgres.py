"""Real disposable PostgreSQL tests for free iPhone <-> desktop chat lifecycle."""
import asyncio
import json
import os
import unittest
import uuid
from pathlib import Path

_IMPORT_ERROR = None
try:
    import asyncpg
    from local_brain_bridge import (
        post_local_chat,get_local_chat,save_pending_local_replies,cancel_local_chat,
    )
    from app import append_device_command_progress
except ImportError as exc:
    asyncpg=None
    _IMPORT_ERROR = exc

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


@unittest.skipUnless(bool(DATABASE),"requires disposable Postgres")
class LocalChatPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        if asyncpg is None:
            raise RuntimeError(
                "Postgres URL is configured but local chat test dependencies failed to import"
            ) from _IMPORT_ERROR
        self.pool=await asyncpg.create_pool(DATABASE,min_size=1,max_size=4)
        async with self.pool.acquire() as db:
            await db.execute(SCHEMA.read_text(encoding="utf-8"))
            await db.execute("DELETE FROM local_chat_cancellations WHERE user_id LIKE 'ci-local%'")
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

    async def test_lost_submit_response_replays_same_request_even_if_desktop_goes_offline(self):
        await self.online()
        body={"message":"Synthetic local test", "request_id":str(uuid.uuid4())}
        first=await post_local_chat(Request(self.pool,body=body))
        self.assertEqual(first.status,202)
        await self.pool.execute("UPDATE device_presence SET last_seen=NOW()-INTERVAL '1 minute' WHERE user_id='ci-local'")
        replay=await post_local_chat(Request(self.pool,body=body))
        self.assertEqual(replay.status,202)
        self.assertEqual(json.loads(first.text)["command_id"],json.loads(replay.text)["command_id"])
        self.assertEqual(await self.pool.fetchval("SELECT count(*) FROM messages WHERE user_id='ci-local'"),1)
        changed=await post_local_chat(Request(self.pool,body={**body,"message":"Different text"}))
        self.assertEqual(changed.status,409)
        self.assertNotIn("desktop_offline",changed.text)

    async def test_same_request_id_concurrent_posts_create_one_task(self):
        await self.online()
        body={"message":"Synthetic local test", "request_id":str(uuid.uuid4()),"conversation_id":str(uuid.uuid4())}
        results=await asyncio.gather(*(post_local_chat(Request(self.pool,body=body)) for _ in range(2)))
        self.assertEqual([r.status for r in results],[202,202])
        self.assertEqual(json.loads(results[0].text)["command_id"],json.loads(results[1].text)["command_id"])
        self.assertEqual(await self.pool.fetchval("SELECT count(*) FROM device_commands WHERE user_id='ci-local'"),1)

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

    async def test_one_pending_request_per_thread_preserves_reply_order(self):
        await self.online()
        cid=str(uuid.uuid4())
        first=await post_local_chat(Request(self.pool,body={
            "message":"Python kodu yaz, detaylı anlat",
            "conversation_id":cid,
        }))
        self.assertEqual(first.status,202)
        pending=json.loads(first.text)["command_id"]
        blocked=await post_local_chat(Request(self.pool,body={
            "message":"Devam et","conversation_id":cid,
        }))
        self.assertEqual(blocked.status,429)
        self.assertEqual(json.loads(blocked.text)["error"],"local_chat_thread_busy")
        self.assertEqual(await self.pool.fetchval(
            "SELECT COUNT(*) FROM messages WHERE user_id='ci-local'"),1)

        # Other threads can still use the remaining slots.
        separate=await post_local_chat(Request(self.pool,body={
            "message":"Mimarlık sorusu","conversation_id":str(uuid.uuid4()),
        }))
        self.assertEqual(separate.status,202)
        third=await post_local_chat(Request(self.pool,body={
            "message":"Bir başka soru","conversation_id":str(uuid.uuid4()),
        }))
        self.assertEqual(third.status,202)
        full=await post_local_chat(Request(self.pool,body={
            "message":"Dördüncü soru","conversation_id":str(uuid.uuid4()),
        }))
        self.assertEqual(full.status,429)
        self.assertEqual(json.loads(full.text)["error"],"local_brain_busy")

        # The completed response becomes visible to the next same-thread turn.
        await self.pool.execute(
            "UPDATE device_commands SET status='completed',result=$1::jsonb "
            "WHERE id=$2",json.dumps({
                "assistant_reply":"Kodun ilk bölümü hazır.",
                "model":"qwen3:4b",
                "provider":"local-ollama",
            }),pending,
        )
        # Phone stopped polling: the next submission must still recover history.
        resumed=await post_local_chat(Request(self.pool,body={
            "message":"Devam et","conversation_id":cid,
        }))
        self.assertEqual(resumed.status,202)
        new_command=json.loads(resumed.text)["command_id"]
        payload=await self.pool.fetchval(
            "SELECT payload FROM device_commands WHERE id=$1",new_command,
        )
        self.assertIn("Kodun ilk bölümü hazır.",str(payload))

    async def test_simultaneous_same_thread_posts_are_atomically_serialized(self):
        await self.online()
        cid=str(uuid.uuid4())
        async def submit(n):
            return await post_local_chat(Request(self.pool,body={
                "message":f"Konuşma mesajı {n}", "conversation_id":cid,
            }))
        responses=await asyncio.wait_for(
            asyncio.gather(submit(1),submit(2)),timeout=15,
        )
        statuses=sorted(r.status for r in responses)
        self.assertEqual(statuses,[202,429])
        self.assertEqual(await self.pool.fetchval(
            "SELECT COUNT(*) FROM messages WHERE user_id='ci-local'"),1)
        self.assertEqual(await self.pool.fetchval(
            "SELECT COUNT(*) FROM device_commands WHERE user_id='ci-local'"),1)

    async def test_history_recovers_unpolled_reply_once_and_only_for_owner(self):
        await self.online()
        created=await post_local_chat(Request(self.pool,body={"message":"Synthetic question"}))
        cid=json.loads(created.text)["command_id"]
        await self.pool.execute(
            "UPDATE device_commands SET status='completed',result=$1::jsonb WHERE id=$2",
            json.dumps({"assistant_reply":"Synthetic delayed reply", "provider":"local-ollama", "model":"qwen3:4b"}),cid)
        await save_pending_local_replies(self.pool,"ci-local-other")
        self.assertEqual(await self.pool.fetchval("SELECT count(*) FROM messages WHERE user_id='ci-local' AND role='assistant'"),0)
        await asyncio.gather(save_pending_local_replies(self.pool,"ci-local"),save_pending_local_replies(self.pool,"ci-local"))
        self.assertEqual(await self.pool.fetchval("SELECT count(*) FROM messages WHERE user_id='ci-local' AND role='assistant'"),1)
        result=json.loads((await get_local_chat(Request(self.pool,id=cid))).text)
        self.assertIsInstance(result["assistant_message_id"],int)

    async def test_queued_cancel_is_owner_and_request_key_scoped(self):
        await self.online()
        request_id, request_key = str(uuid.uuid4()), "a" * 64
        submitted=await post_local_chat(Request(self.pool,body={
            "message":"Cancelable queued chat", "request_id":request_id,
            "request_key":request_key,
        }))
        self.assertEqual(submitted.status,202)
        command_id=json.loads(submitted.text)["command_id"]

        wrong_owner=await cancel_local_chat(Request(self.pool,owner="ci-local-other",body={
            "request_id":request_id,"request_key":request_key,
        }))
        wrong_key=await cancel_local_chat(Request(self.pool,body={
            "request_id":request_id,"request_key":"b"*64,
        }))
        self.assertEqual(wrong_owner.status,404)
        self.assertEqual(wrong_key.status,404)
        self.assertEqual(await self.pool.fetchval(
            "SELECT status FROM device_commands WHERE id=$1",command_id),"queued")

        stopped=await cancel_local_chat(Request(self.pool,body={
            "request_id":request_id,"request_key":request_key,
        }))
        payload=json.loads(stopped.text)
        self.assertEqual(payload["status"],"cancelled_before_start")
        self.assertFalse(payload["provider_stopped"])
        self.assertTrue(payload["prevented_start"])
        self.assertEqual(await self.pool.fetchval(
            "SELECT status FROM device_commands WHERE id=$1",command_id),"cancelled")
        self.assertEqual(json.loads((await get_local_chat(
            Request(self.pool,id=command_id))).text)["status"],"output_suppressed")

    async def test_cancel_before_queue_post_leaves_owner_scoped_tombstone(self):
        request_id, request_key = str(uuid.uuid4()), "e" * 64
        cancelled=await cancel_local_chat(Request(self.pool,body={
            "request_id":request_id,"request_key":request_key,
        }))
        payload=json.loads(cancelled.text)
        self.assertEqual(payload["status"],"cancelled_before_start")
        self.assertTrue(payload["prevented_start"])
        self.assertFalse(payload["provider_stopped"])

        await self.online()
        submitted=await post_local_chat(Request(self.pool,body={
            "message":"Must not start after the stop command", "request_id":request_id,
            "request_key":request_key,
        }))
        self.assertEqual(submitted.status,200)
        self.assertEqual(json.loads(submitted.text)["status"],"cancelled_before_start")
        self.assertEqual(await self.pool.fetchval(
            "SELECT COUNT(*) FROM device_commands WHERE user_id='ci-local'"),0)
        self.assertEqual(await self.pool.fetchval(
            "SELECT request_key_hash FROM local_chat_cancellations "
            "WHERE user_id='ci-local' AND request_id=$1",uuid.UUID(request_id)),
            __import__("hashlib").sha256(request_key.encode()).hexdigest())

    async def test_concurrent_submit_and_cancel_cannot_leave_a_live_queue_item(self):
        await self.online()
        request_id, request_key = str(uuid.uuid4()), "f" * 64
        body={"message":"Race submit against stop", "request_id":request_id,
              "request_key":request_key,"conversation_id":str(uuid.uuid4())}
        submitted, cancelled = await asyncio.gather(
            post_local_chat(Request(self.pool,body=body)),
            cancel_local_chat(Request(self.pool,body={
                "request_id":request_id,"request_key":request_key,
            })),
        )
        self.assertIn(submitted.status,(200,202))
        self.assertIn(json.loads(cancelled.text)["status"],
                      ("cancelled_before_start","cancellation_requested","cancelled"))
        self.assertEqual(await self.pool.fetchval(
            "SELECT COUNT(*) FROM device_commands WHERE user_id='ci-local' "
            "AND status IN ('queued','delivered')"),0)

    async def test_delivered_local_qwen_late_result_is_not_stored_or_returned(self):
        await self.online()
        request_id, request_key = str(uuid.uuid4()), "c" * 64
        submitted=await post_local_chat(Request(self.pool,body={
            "message":"Interrupt delivered chat", "request_id":request_id,
            "request_key":request_key,
        }))
        command_id=json.loads(submitted.text)["command_id"]
        await self.pool.execute(
            "UPDATE device_commands SET status='delivered' WHERE id=$1",command_id)

        stopped=await cancel_local_chat(Request(self.pool,body={
            "request_id":request_id,"request_key":request_key,
        }))
        payload=json.loads(stopped.text)
        self.assertEqual(payload["status"],"cancellation_requested")
        self.assertFalse(payload["provider_stopped"])
        await self.pool.execute(
            "UPDATE device_commands SET status='completed',result=$1::jsonb WHERE id=$2",
            json.dumps({"assistant_reply":"Late Qwen reply","model":"qwen3:4b"}),
            command_id,
        )
        await save_pending_local_replies(self.pool,"ci-local")
        result=json.loads((await get_local_chat(
            Request(self.pool,id=command_id))).text)
        self.assertEqual(result["status"],"output_suppressed")
        self.assertEqual(await self.pool.fetchval(
            "SELECT COUNT(*) FROM messages WHERE user_id='ci-local' AND role='assistant'"),0)

    async def test_worker_ack_confirms_only_the_cancelled_owned_qwen_stream(self):
        await self.online()
        request_id, request_key = str(uuid.uuid4()), "d" * 64
        submitted=await post_local_chat(Request(self.pool,body={
            "message":"Interrupt and acknowledge", "request_id":request_id,
            "request_key":request_key,
        }))
        command_id=json.loads(submitted.text)["command_id"]
        await self.pool.execute(
            "UPDATE device_commands SET status='delivered',delivery_attempt=3 WHERE id=$1",
            command_id,
        )
        pending=await cancel_local_chat(Request(self.pool,body={
            "request_id":request_id,"request_key":request_key,
        }))
        self.assertEqual(json.loads(pending.text)["status"],"cancellation_requested")
        self.assertFalse(json.loads(pending.text)["provider_stopped"])

        worker=Request(self.pool,body={
            "delivery_attempt":3,"stage":"cancelled",
            "message":"Ollama response transport closed.",
        },id=command_id)
        worker["auth_kind"]="device"
        acknowledged=await append_device_command_progress(worker)
        self.assertTrue(json.loads(acknowledged.text)["provider_stopped"])
        self.assertTrue(await self.pool.fetchval(
            "SELECT provider_stopped FROM local_chat_requests WHERE command_id=$1",
            command_id,
        ))

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
