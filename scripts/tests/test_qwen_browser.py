"""Real Chromium + HTTP + PostgreSQL + desktop handler; providers are explicit fakes.
Run only against ULTRON_QUEUE_TEST_DATABASE_URL (disposable). No hardware claims.
"""
from __future__ import annotations
import ast
import asyncio
import json
import os
import sys
import time
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'ultron/cloud_service'), str(ROOT / 'ultron/backend')]
from aiohttp import web
from playwright.async_api import async_playwright
from cloud_client import CloudClient, CloudDeliveryRejected
from cloud_delivery import RemoteLeaseGuard
from integration import local_cloud_brain
import app as cloud

DATABASE = os.getenv('ULTRON_QUEUE_TEST_DATABASE_URL', '')


def desktop_handler():
    tree = ast.parse((ROOT / 'mark_app.py').read_text())
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)
              and n.name == '_handle_cloud_remote_command')
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), fn], type_ignores=[])
    ast.fix_missing_locations(module)
    ns = dict(asyncio=asyncio, time=time, RemoteLeaseGuard=RemoteLeaseGuard,
              CloudDeliveryRejected=CloudDeliveryRejected)
    exec(compile(module, 'mark_app.py', 'exec'), ns)
    return ns[fn.name]


@unittest.skipUnless(DATABASE, 'requires disposable PostgreSQL')
class QwenBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict(os.environ, {'DATABASE_URL': DATABASE,
            'ULTRON_SESSION_SECRET': 'synthetic-browser-session-only',
            'ULTRON_PASSWORD': 'synthetic-browser-password-only',
            'ULTRON_DEVICE_TOKEN': 'synthetic-browser-device-only'})
        self.env.start()
        self.owner = patch.object(cloud, 'DEFAULT_USER_ID', 'ci-browser')
        self.owner.start()
        self.calls = []
        self.cloud_calls = []
        self.delay = .15
        async def tags(request):
            return web.json_response({'models':[{'name':'qwen3:4b'}]})
        async def inference(request):
            body = await request.json()
            self.calls.append(body)
            await asyncio.sleep(self.delay)
            return web.json_response({'model':body['model'], 'done':True,
                'message':{'role':'assistant','content':'Sentetik yerel yanıt ' + str(len(self.calls)) + '.'}})
        ollama = web.Application()
        ollama.router.add_get('/api/tags', tags)
        ollama.router.add_post('/api/chat', inference)
        self.ollama_runner, ollama_url = await self.serve(ollama)
        self.ollama_patch = patch.object(local_cloud_brain, '_OLLAMA', ollama_url)
        self.ollama_patch.start()
        local_cloud_brain._MODELS_CACHE = (0., [])
        def gemini(*args, **kwargs):
            self.cloud_calls.append(args)
            return 'Sentetik bulut yanıtı.'
        self.gemini_patch = patch.object(cloud, '_gemini_reply', gemini)
        self.gemini_patch.start()
        self.app = cloud.build_app()
        self.runner, self.url = await self.serve(self.app)
        self.pool = self.app['db']
        for table in ('local_chat_requests','device_commands','messages','conversations','device_presence'):
            await self.pool.execute(f"DELETE FROM {table} WHERE user_id='ci-browser'")
        self.client = CloudClient()
        self.client.base_url = self.url
        await self.client.heartbeat({'local_chat_ready':True})
        self.handle = desktop_handler()
        self.worker = asyncio.create_task(self.work())
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(args=['--no-sandbox'])
        self.context = await self.browser.new_context(service_workers='block')
        await self.context.add_cookies([{'name':cloud.COOKIE_NAME,
            'value':cloud.create_session_cookie('ci-browser'), 'url':self.url}])
        self.page = await self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        await self.page.goto(self.url)
        await self.page.wait_for_function("!document.querySelector('#app').classList.contains('hidden') && !document.querySelector('#splash')?.classList.contains('active')")
        await self.page.evaluate('voiceEnabled=false')

    async def serve(self, app):
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, '127.0.0.1', 0)
        await site.start()
        return runner, 'http://127.0.0.1:' + str(site._server.sockets[0].getsockname()[1])

    async def work(self):
        while True:
            await self.client.heartbeat({'local_chat_ready':True})
            for command in await self.client.claim_desktop_commands():
                await self.handle(SimpleNamespace(), self.client, command)
            await asyncio.sleep(.1)

    async def stop_worker(self):
        self.worker.cancel()
        await asyncio.gather(self.worker, return_exceptions=True)

    async def asyncTearDown(self):
        await self.stop_worker()
        await self.browser.close()
        await self.playwright.stop()
        self.client._local_executor.shutdown(wait=True)
        self.client._executor.shutdown(wait=True)
        await self.runner.cleanup()
        await self.ollama_runner.cleanup()
        self.gemini_patch.stop()
        self.ollama_patch.stop()
        self.owner.stop()
        self.env.stop()

    async def send(self, text):
        await self.page.locator('#message').fill(text)
        await self.page.evaluate('send(false)')
        await self.page.wait_for_function('!chatSending')

    async def assert_order(self, count):
        await self.page.evaluate('loadMessages()')
        nodes = self.page.locator('#messages .msg[data-cloud-id]')
        self.assertEqual(await nodes.count(), count)
        ids = await nodes.evaluate_all('(nodes)=>nodes.map(n=>Number(n.dataset.cloudId))')
        self.assertEqual(ids, sorted(set(ids)))
        self.assertEqual(await self.page.locator('#busy').inner_text(), '')
        self.assertTrue(await self.page.locator('#sendBtn').is_enabled())
        self.assertEqual(self.errors, [])

    async def test_live_flags_double_send_and_followup_keep_local_history(self):
        await self.page.evaluate("liveDesired=true;voiceListening=true;brainMode='gemini'")
        await self.page.locator('#message').fill('2009 C180 hakkında konuşalım.')
        await self.page.evaluate('Promise.all([send(false),send(false),loadMessages()])')
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.cloud_calls, [])
        await self.send('Peki onun yakıt tüketimi?')
        self.assertEqual(len(self.calls), 2)
        turns = self.calls[-1]['messages']
        self.assertTrue(any(m['role']=='assistant' and 'Sentetik yerel yanıt 1.' in m['content'] for m in turns))
        await self.assert_order(4)
        row = await self.pool.fetchrow("SELECT status,result FROM device_commands WHERE user_id='ci-browser' ORDER BY id DESC LIMIT 1")
        self.assertEqual(row['status'], 'completed')
        result = json.loads(row['result'])
        self.assertEqual((result['provider'], result['model']), ('local-ollama', 'qwen3:4b'))

    async def test_lost_post_and_completion_responses_do_not_repeat_inference(self):
        posts = []
        async def lose_first(route):
            posts.append(route.request.post_data)
            response = await route.fetch()
            if len(posts)==1:
                await route.abort('connectionreset')
            else:
                await route.fulfill(response=response)
        await self.page.route('**/api/local-chat', lose_first)
        original = self.client._sync_request
        completions = []
        def lose_completion(method, path, *args, **kwargs):
            result = original(method, path, *args, **kwargs)
            if path.endswith('/complete'):
                completions.append(result)
                if len(completions)==1:
                    raise urllib.error.URLError('synthetic lost completion response')
            return result
        with patch.object(self.client, '_sync_request', lose_completion):
            await self.send('Kısa bir selam ver.')
            for _ in range(40):
                if len(completions)==2:
                    break
                await asyncio.sleep(.1)
        self.assertEqual(len(posts),2)
        self.assertEqual(posts[0],posts[1])
        self.assertEqual(len(self.calls),1)
        self.assertEqual(len(completions),2)
        self.assertTrue(completions[-1]['replayed'])
        self.assertEqual(self.cloud_calls,[])
        await self.assert_order(2)

    async def test_offline_desktop_uses_cloud_without_local_task(self):
        await self.stop_worker()
        await self.client.heartbeat({'local_chat_ready':False})
        await self.send('Merhaba, nasılsın?')
        self.assertEqual(len(self.cloud_calls),1)
        self.assertEqual(self.calls,[])
        self.assertEqual(await self.pool.fetchval("SELECT count(*) FROM device_commands WHERE user_id='ci-browser'"),0)
        await self.assert_order(2)

    async def test_long_inference_survives_lease_window_and_one_poll_disconnect(self):
        self.delay=22
        polls=[]
        async def lose_one_poll(route):
            polls.append(route.request.url)
            if len(polls)==1:
                await route.abort('connectionreset')
            else:
                await route.continue_()
        await self.page.route('**/api/local-chat/*',lose_one_poll)
        await self.send('Uzun süren sentetik yanıt denemesi.')
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.cloud_calls,[])
        self.assertGreater(len(polls),2)
        row=await self.pool.fetchrow("SELECT status,delivery_attempt,retry_count FROM device_commands WHERE user_id='ci-browser'")
        self.assertEqual(dict(row),{'status':'completed','delivery_attempt':1,'retry_count':0})
        await self.assert_order(2)

    async def test_new_service_worker_removes_old_shell_and_loads_current_transport(self):
        context = await self.browser.new_context(service_workers='allow')
        page = await context.new_page()
        try:
            # Seed an old release cache before the real worker is installed.
            await page.goto(self.url + '/health')
            await page.evaluate("""async()=>{
              const cache=await caches.open('ultron-shell-v55');
              await cache.put('/static/auto-brain.js',new Response('window.STALE_ROUTER=true'));
              const registration=await navigator.serviceWorker.register('/static/sw.js',{updateViaCache:'none'});
              await registration.update();
            }""")
            await page.wait_for_function("""async()=>{
              const keys=await caches.keys();
              const r=await navigator.serviceWorker.getRegistration('/static/');
              return r?.active && keys.includes('ultron-shell-v57')&&!keys.includes('ultron-shell-v55');
            }""")
            await page.goto(self.url + '/static/index.html')
            await page.wait_for_function("typeof window.ULTRONChatTransport?.localAnswer==='function'")
            self.assertFalse(await page.evaluate('!!window.STALE_ROUTER'))
            response = await page.request.get(self.url + '/static/chat-transport.js')
            self.assertIn('no-store', response.headers.get('cache-control',''))
            self.assertIn('request_id', await response.text())
        finally:
            await context.close()

    async def test_closed_phone_recovers_completed_reply_from_history(self):
        self.delay=.8
        await self.page.locator('#message').fill('Sentetik gecikme denemesi.')
        await self.page.evaluate('void send(false)')
        for _ in range(50):
            if self.calls:
                break
            await asyncio.sleep(.05)
        self.assertEqual(len(self.calls),1)
        await self.page.reload()
        for _ in range(60):
            await self.page.evaluate('loadMessages()')
            if await self.page.locator('#messages .assistant[data-cloud-id]').count():
                break
            await asyncio.sleep(.1)
        await self.assert_order(2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
