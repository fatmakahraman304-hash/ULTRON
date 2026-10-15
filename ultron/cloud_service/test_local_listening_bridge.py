"""Offline fake-DB tests for owner-only ephemeral Qwen listening queue."""
import json
import unittest
import uuid

from aiohttp import web
from local_listening_bridge import (
    _identity, _validated_analysis, post_local_listening_analysis,
    get_local_listening_analysis,
)


class Context:
    def __init__(self, obj):
        self.obj=obj
    async def __aenter__(self):
        return self.obj
    async def __aexit__(self, *args):
        return False


class FakePool:
    def __init__(self, ready=True, status="completed"):
        self.ready=ready
        self.status=status
        self.commands=[]
        self.queries=[]
        self.saved=None

    def acquire(self):
        return Context(self)

    def transaction(self):
        return Context(self)

    async def execute(self, sql,*args):
        self.queries.append(("execute",sql,args))
        return "UPDATE 1"

    async def fetchval(self, sql,*args):
        self.queries.append(("fetchval",sql,args))
        if "local_listening_analysis_ready" in sql:
            return self.ready
        if "COUNT(*)" in sql:
            return 0
        raise AssertionError(sql)

    async def fetchrow(self,sql,*args):
        self.queries.append(("fetchrow",sql,args))
        if "SELECT id,payload" in sql:
            return self.saved
        if "INSERT INTO device_commands" in sql:
            self.saved={"id":42,"payload":json.loads(args[1])}
            return {"id":42}
        if "SELECT id,status,result,payload" in sql:
            return {"id":42,"status":self.status,
                    "result":{"stage":"map","analysis":"Karar: sade çizim.",
                              "provider":"local-ollama","model":"qwen3:4b"},
                    "payload":{"stage":"map","mode":"local_listening_analysis"}}
        raise AssertionError(sql)


class FakeRequest(dict):
    def __init__(self, body=None, kind="web", owner="owner-a", db=None):
        super().__init__(auth_kind=kind,user_id=owner,device_id="iphone-web")
        self._body=body
        self.app={"db":db or FakePool()}
        self.match_info={"id":"42"}

    async def json(self):
        return self._body


class LocalListenQueueTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.body={"stage":"map","text":"Proje hakkında konuşma.","part":1,
                   "total":1,"request_id":str(uuid.uuid4())}

    async def test_owner_submit_uses_readonly_mode_and_no_memory_or_chat_writes(self):
        db=FakePool()
        request=FakeRequest(self.body,db=db)
        response=await post_local_listening_analysis(request)
        self.assertEqual(response.status,202)
        payload=db.saved["payload"]
        self.assertEqual(payload["mode"],"local_listening_analysis")
        self.assertEqual(payload["stage"],"map")
        self.assertIn("proje hakkında konuşma",payload["text"].lower())
        self.assertIn("READ-ONLY",payload["system"])
        self.assertEqual(payload["request_id"],self.body["request_id"])
        insert=[q for q in db.queries if "INSERT INTO" in q[1]]
        self.assertEqual(len(insert),1)
        self.assertIn("device_commands",insert[0][1])
        self.assertNotIn("messages",insert[0][1])
        self.assertNotIn("memories",insert[0][1])
        self.assertNotIn("local_chat_requests",insert[0][1])

    async def test_identity_collision_is_conflict_not_second_queue_job(self):
        db=FakePool()
        response1=await post_local_listening_analysis(FakeRequest(self.body,db=db))
        self.assertEqual(response1.status,202)
        altered={**self.body,"text":"Farklı konu"}
        response2=await post_local_listening_analysis(FakeRequest(altered,db=db))
        self.assertEqual(response2.status,409)
        self.assertEqual(len([q for q in db.queries if "INSERT INTO" in q[1]]),1)

    async def test_same_request_id_replay_is_single_enqueue(self):
        db=FakePool()
        await post_local_listening_analysis(FakeRequest(self.body,db=db))
        second=await post_local_listening_analysis(FakeRequest(self.body,db=db))
        self.assertEqual(second.status,202)
        self.assertEqual(json.loads(second.body)["id"],42)
        self.assertTrue(json.loads(second.body)["replayed"])
        self.assertEqual(len([q for q in db.queries if "INSERT INTO" in q[1]]),1)

    async def test_old_worker_must_not_accept_chunk(self):
        db=FakePool(ready=False)
        response=await post_local_listening_analysis(FakeRequest(self.body,db=db))
        self.assertEqual(response.status,409)
        self.assertEqual(json.loads(response.body)["error"],"local_analysis_offline")
        self.assertIsNone(db.saved)

    async def test_only_authenticated_web_owner_can_submit_and_poll(self):
        for function in (post_local_listening_analysis,get_local_listening_analysis):
            with self.subTest(function=function.__name__):
                with self.assertRaises(web.HTTPForbidden):
                    await function(FakeRequest(self.body,kind="device"))

    async def test_completed_poll_validates_source_and_scrubs_transcript(self):
        db=FakePool()
        response=await get_local_listening_analysis(FakeRequest(self.body,db=db))
        self.assertEqual(response.status,200)
        payload=json.loads(response.body)
        self.assertEqual(payload["provider"],"local-ollama")
        self.assertEqual(payload["analysis"],"Karar: sade çizim.")
        self.assertTrue(any("payload=payload - 'text' - 'system'" in q[1] for q in db.queries))
        self.assertTrue(all("user_id=$2" in q[1] for q in db.queries if "SELECT id,status" in q[1]))

    async def test_every_worker_stage_and_unicode_final_remain_readable_after_scrubbing(self):
        for stage in ('map', 'reduce', 'final'):
            with self.subTest(stage=stage):
                db=FakePool()
                original=db.fetchrow
                async def fetchrow(sql, *args):
                    row=await original(sql, *args)
                    if 'SELECT id,status,result,payload' in sql:
                        row['payload']['stage']=stage
                        row['result']['stage']=stage
                        row['result']['analysis']='😀'*5000 if stage=='final' else 'Karar: açık kaynak.'
                    return row
                db.fetchrow=fetchrow
                for _ in range(2):
                    response=await get_local_listening_analysis(FakeRequest(self.body,db=db))
                    self.assertEqual(response.status,200)
                    value=json.loads(response.body)
                    self.assertEqual(value['status'],'completed')
                    self.assertEqual(value['stage'],stage)
                    self.assertEqual(value['model'],'qwen3:4b')
                    if stage=='final':self.assertEqual(len(value['analysis']),5000)

    async def test_failed_poll_never_leaks_worker_result(self):
        db=FakePool(status="failed")
        response=await get_local_listening_analysis(FakeRequest(self.body,db=db))
        self.assertEqual(json.loads(response.body)["status"],"failed")
        self.assertNotIn("Karar",response.body.decode())

    def test_reject_foreign_model_and_incomplete_thinking(self):
        for value in [
            {"provider":"local-ollama","model":"llava:7b","stage":"map","analysis":"Fake"},
            {"provider":"gemini","model":"qwen3:4b","stage":"map","analysis":"Fake"},
            {"provider":"local-ollama","model":"qwen3:4b","stage":"reduce","analysis":"Fake"},
            {"provider":"local-ollama","model":"qwen3:4b","stage":"map","analysis":"<think>\\nunfinished"},
        ]:
            self.assertIsNone(_validated_analysis(value,"map"))


if __name__=="__main__":
    unittest.main()
