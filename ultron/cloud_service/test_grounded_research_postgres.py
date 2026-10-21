"""Real isolated PostgreSQL + authenticated HTTP; the Google model is a fixture."""
import os
import asyncio
import json
import uuid
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import asyncpg
import app as cloud
from test_grounded_search import sdk_response
from grounded_search import parse_grounding
from local_brain_bridge import post_local_chat

DB=os.getenv('ULTRON_QUEUE_TEST_DATABASE_URL','')

@unittest.skipUnless(DB, 'requires disposable PostgreSQL')
class GroundedResearchPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool=await asyncpg.create_pool(DB,min_size=1,max_size=3)
        await self.pool.execute(Path(__file__).with_name('schema.sql').read_text())
        # Run the additive schema twice to verify idempotent upgrade.
        await self.pool.execute(Path(__file__).with_name('schema.sql').read_text())
        self.owner='grounding-test-'+str(uuid.uuid4())
        @web.middleware
        async def fixture_auth(request,handler):
            # Controlled test identity; production auth/CSRF is tested separately.
            request['user_id']=request.headers.get('X-Fixture-Owner',self.owner)
            request['device_id']='fixture-phone'
            request['auth_kind']='web'
            return await handler(request)
        app=web.Application(middlewares=[fixture_auth]);app['db']=self.pool
        app.router.add_post('/api/chat',cloud.chat);app.router.add_get('/api/messages',cloud.list_messages)
        app.router.add_post('/api/chat/cancel',cloud.cancel_chat)
        app.router.add_post('/api/local-chat',post_local_chat)
        self.client=TestClient(TestServer(app));await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        await self.pool.execute('DELETE FROM conversations WHERE user_id=$1',self.owner)
        await self.pool.close()

    async def test_grounded_answer_is_single_pass_persisted_and_owner_isolated(self):
        evidence=parse_grounding(sdk_response(widget='<a href="https://www.google.com/search?q=pil">Google</a>'),model='fixture')
        with patch.object(cloud,'research_for_chat',AsyncMock(return_value=evidence)) as search, \
             patch.object(cloud,'_memory_context',AsyncMock(return_value='private memory never sent')), \
             patch.object(cloud,'_gemini_reply') as second_model:
            response=await self.client.post('/api/chat',json={'message':'Güncel pil fiyatları neler?'})
            self.assertEqual(response.status,200)
            data=await response.json();second_model.assert_not_called()
            self.assertEqual(search.call_args.args,('Güncel pil fiyatları neler?',))
        row=await self.pool.fetchrow('SELECT content,research_metadata FROM messages WHERE id=$1',data['assistant_message_id'])
        self.assertIn('https://example.org/report',row['content'])
        self.assertEqual(json.loads(row['research_metadata'])['provider'],'google_search')
        own=await (await self.client.get('/api/messages')).json()
        self.assertEqual(own['messages'][-1]['research_metadata'],row['research_metadata'])
        other=await (await self.client.get('/api/messages',headers={'X-Fixture-Owner':'other-fixture-owner'})).json()
        self.assertEqual(other['messages'],[])
        foreign=await self.client.post('/api/chat',headers={'X-Fixture-Owner':'other-fixture-owner'},
            json={'message':'Selam','conversation_id':data['conversation_id']})
        self.assertEqual(foreign.status,404)

    async def test_no_evidence_returns_honest_answer_without_generation(self):
        with patch.object(cloud,'research_for_chat',AsyncMock(return_value={'ok':False,'status':'search_unavailable'})), \
             patch.object(cloud,'_memory_context',AsyncMock(return_value='')), \
             patch.object(cloud,'_gemini_reply') as model:
            response=await self.client.post('/api/chat',json={'message':'Bugün benzin fiyatları kaç TL?'})
            data=await response.json();model.assert_not_called()
            self.assertIn('doğrulayamıyorum',data['reply'])
            self.assertEqual(data['research']['status'],'search_unavailable')

    async def test_contextual_research_followup_uses_only_previous_user_query(self):
        conv=uuid.uuid4()
        await self.pool.execute('INSERT INTO conversations(id,user_id,title) VALUES($1,$2,$3)',conv,self.owner,'fixture')
        await self.pool.execute("INSERT INTO messages(conversation_id,user_id,role,content) VALUES($1,$2,'user',$3)",conv,self.owner,'Araştır: yeni pil teknolojileri')
        with patch.object(cloud,'research_for_chat',AsyncMock(return_value={'ok':False,'status':'search_unavailable'})) as search, \
             patch.object(cloud,'_memory_context',AsyncMock(return_value='PRIVATE_PROFILE')):
            response=await self.client.post('/api/chat',json={'message':'Araştırmaya devam et','conversation_id':str(conv)})
            self.assertEqual(response.status,200)
            self.assertEqual(search.call_args.args,('Araştır: yeni pil teknolojileri. Araştırmaya devam et',))

    async def test_public_research_is_rejected_before_any_desktop_task_is_created(self):
        for message in ('Bugün dolar kaç TL?', 'Araştırmaya devam et'):
            response = await self.client.post('/api/local-chat', json={'message':message})
            self.assertEqual(response.status, 409)
            self.assertEqual((await response.json())['error'], 'research_requires_cloud')
        self.assertEqual(await self.pool.fetchval('SELECT count(*) FROM local_chat_requests WHERE user_id=$1', self.owner), 0)
        self.assertEqual(await self.pool.fetchval('SELECT count(*) FROM device_commands WHERE user_id=$1', self.owner), 0)

    async def test_cancelled_grounding_never_saves_late_answer_or_citations(self):
        started, release = asyncio.Event(), asyncio.Event()
        async def delayed_search(*args, **kwargs):
            started.set()
            await release.wait()
            return parse_grounding(sdk_response(), model='fixture')
        identity = {'request_id':str(uuid.uuid4()),'request_key':'c'*64}
        with patch.object(cloud, 'research_for_chat', delayed_search), \
             patch.object(cloud, '_memory_context', AsyncMock(return_value='')):
            task = asyncio.create_task(self.client.post('/api/chat', json={**identity,'message':'Bugün benzin fiyatları kaç TL?'}))
            await asyncio.wait_for(started.wait(), 3)
            cancel = await self.client.post('/api/chat/cancel', json=identity)
            self.assertFalse((await cancel.json())['provider_stopped'])
            release.set()
            data = await (await task).json()
            self.assertEqual(data['status'], 'output_suppressed')
        self.assertEqual(await self.pool.fetchval("SELECT count(*) FROM messages WHERE user_id=$1 AND role='assistant'", self.owner), 0)
