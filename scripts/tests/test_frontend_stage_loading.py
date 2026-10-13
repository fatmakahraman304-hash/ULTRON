"""Real Chromium check that the initial dashboard defers its WebGL stage."""
import asyncio
import json
import unittest
from pathlib import Path

from aiohttp import web
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[2]
DIST=ROOT/'ultron/frontend/dist'


class FrontendStageLoadingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        app=web.Application()
        app.router.add_get('/',self.index)
        app.router.add_get('/api/{tail:.*}',self.api)
        app.router.add_get('/ws',self.websocket)
        app.router.add_static('/assets/',DIST/'assets',show_index=False)
        if (DIST/'handtracking').is_dir():app.router.add_static('/handtracking/',DIST/'handtracking',show_index=False)
        self.runner=web.AppRunner(app,access_log=None)
        await self.runner.setup()
        site=web.TCPSite(self.runner,'127.0.0.1',0)
        await site.start()
        self.url='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])+'/'
        self.playwright=await async_playwright().start()
        self.browser=await self.playwright.chromium.launch(args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        self.context=await self.browser.new_context(viewport={'width':1280,'height':900},service_workers='block')
        self.page=await self.context.new_page()
        self.requests=[]
        self.errors=[]
        self.stage_chunk_requested=asyncio.Event()
        self.release_stage_chunk=asyncio.Event()
        self.page.on('request',lambda request:self.requests.append(request.url))
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        for chunk in self.webgl_chunks():
            await self.page.route(f'**/{chunk}',self.hold_stage_chunk)

    async def asyncTearDown(self):
        self.release_stage_chunk.set()
        await self.browser.close()
        await self.playwright.stop()
        await self.runner.cleanup()

    async def api(self,request):
        return web.json_response({'ok':True,'messages':[],'devices':[],'requests':[],'memories':[],'plans':[],'commands':[]})

    async def index(self,request):
        return web.FileResponse(DIST/'index.html')

    @staticmethod
    def webgl_chunks():
        return [p.name for p in (DIST/'assets').glob('*.js') if 'WebGLRenderer' in p.read_text(encoding='utf-8',errors='replace')]

    async def hold_stage_chunk(self,route):
        self.stage_chunk_requested.set()
        await self.release_stage_chunk.wait()
        await route.continue_()

    async def websocket(self,request):
        ws=web.WebSocketResponse()
        await ws.prepare(request)
        await ws.close()
        return ws

    async def test_chat_shell_paints_before_webgl_chunk_then_real_scene_loads(self):
        await self.page.goto(self.url,wait_until='domcontentloaded')
        webgl_chunks=self.webgl_chunks()
        self.assertTrue(webgl_chunks,'production build should contain its real Three.js renderer')
        await asyncio.wait_for(self.stage_chunk_requested.wait(),10)
        loading=self.page.locator('.center-stage-loading')
        await loading.wait_for(timeout=5000)
        await self.page.get_by_role('textbox',name='Mesaj').fill('Hızlı yazı testi')
        self.assertFalse(await self.page.locator('.center-stage').count(),
                         'the chat should remain usable while the WebGL dependency is held')

        self.release_stage_chunk.set()
        await self.page.locator('.center-stage').wait_for(timeout=15000)
        await self.page.locator('.center-stage canvas').wait_for(timeout=15000)
        self.assertTrue(any(any(chunk in url for chunk in webgl_chunks) for url in self.requests),
                        'the 3D renderer should load after the short shell-first delay')
        self.assertEqual(self.errors,[])


if __name__=='__main__':
    unittest.main(verbosity=2)
