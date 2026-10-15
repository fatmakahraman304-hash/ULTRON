"""Actual isolated queue contracts; no production DB or inference."""
import asyncio
import json
import os
import unittest
import uuid
from pathlib import Path
import asyncpg
from aiohttp import web
from scene_queue import post_scene, get_scene
from test_scene_design import GOOD

URL=os.getenv('ULTRON_QUEUE_TEST_DATABASE_URL','')
class Request(dict):
    def __init__(self,pool,owner,body=None,ident=1):
        super().__init__(user_id=owner,auth_kind='web',device_id='ci-scene')
        self.app={'db':pool};self.body=body;self.match_info={'id':str(ident)}
    async def json(self):return self.body

@unittest.skipUnless(URL,'requires disposable PostgreSQL')
class SceneQueueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool=await asyncpg.create_pool(URL,min_size=1,max_size=4)
        await self.pool.execute(Path(__file__).with_name('schema.sql').read_text())
        self.owner='ci-scene-'+uuid.uuid4().hex
        self.body={'description':'masa','request_id':str(uuid.uuid4())}
    async def asyncTearDown(self):
        await self.pool.execute('DELETE FROM device_commands WHERE user_id=$1',self.owner)
        await self.pool.execute('DELETE FROM device_presence WHERE user_id=$1',self.owner)
        await self.pool.close()
    async def ready(self,value=True):
        await self.pool.execute("INSERT INTO device_presence(user_id,device,state,last_seen) VALUES($1,'desktop',$2::jsonb,NOW()) ON CONFLICT(user_id,device) DO UPDATE SET state=EXCLUDED.state,last_seen=NOW()",self.owner,json.dumps({'local_chat_ready':value}))
    async def post(self,body=None):return await post_scene(Request(self.pool,self.owner,body or self.body))
    async def test_dedup_after_offline_and_no_chat_or_memory(self):
        self.assertEqual((await self.post()).status,409)
        await self.ready()
        responses=await asyncio.gather(self.post(),self.post())
        ids=[json.loads(r.body)['command_id'] for r in responses];self.assertEqual(ids[0],ids[1])
        await self.ready(False)
        self.assertEqual(json.loads((await self.post()).body)['command_id'],ids[0])
        self.assertEqual((await self.post({**self.body,'description':'sandalye'})).status,409)
        for table in ['conversations','messages','memories']:
            self.assertEqual(await self.pool.fetchval(f'SELECT count(*) FROM {table} WHERE user_id=$1',self.owner),0)
        payload=await self.pool.fetchval('SELECT payload FROM device_commands WHERE id=$1',ids[0]);payload=json.loads(payload)
        self.assertEqual(payload['mode'],'local_brain');self.assertEqual(payload['turns'],[])
    async def test_owner_scope_and_validated_result(self):
        await self.ready();ident=json.loads((await self.post()).body)['command_id']
        self.assertEqual((await get_scene(Request(self.pool,'another-owner',ident=ident))).status,404)
        req=Request(self.pool,self.owner,ident=ident);req['auth_kind']='device'
        with self.assertRaises(web.HTTPForbidden):await get_scene(req)
        for result,status in [({'provider':'local-ollama','model':'qwen3:4b','assistant_reply':json.dumps(GOOD)},200),({'provider':'local-ollama','model':'qwen3:4b','assistant_reply':'{"code":"bad"}'},502),({'provider':'gemini','model':'gemini','assistant_reply':json.dumps(GOOD)},502)]:
            await self.pool.execute("UPDATE device_commands SET status='completed',result=$2::jsonb WHERE id=$1",ident,json.dumps(result))
            response=await get_scene(Request(self.pool,self.owner,ident=ident));self.assertEqual(response.status,status)
            if status==200:self.assertEqual(json.loads(json.loads(response.body)['reply']),GOOD)
    async def test_atomic_shared_capacity(self):
        await self.ready()
        replies=await asyncio.gather(*(self.post({'description':'masa','request_id':str(uuid.uuid4())}) for _ in range(4)))
        self.assertEqual(sorted(r.status for r in replies),[202,202,202,429])
