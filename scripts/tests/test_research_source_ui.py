"""Actual Chromium; controlled API/model fixtures, no real provider/device claim."""
import os
import unittest
from pathlib import Path
from aiohttp import web
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / 'ultron/cloud_service/static'
DIST = ROOT / 'ultron/frontend/dist'
TEXT = 'DEMO TEST — Güncel değer 42 TL.\n\nKaynak: [Kontrollü rapor](https://example.org/report)\n<script>window.sourceExecuted=true</script>'
META = {'provider':'google_search', 'search_suggestions_html':
        '<a href="https://www.google.com/search?q=fixture" target="_blank">Google test araması</a>'
        '<script>parent.sourceExecuted=true</script><img src="https://example.org/leak">'}

class ResearchSourceBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.invocations = []
        app = web.Application()
        app.router.add_get('/', lambda _: web.FileResponse(DIST / 'index.html'))
        app.router.add_get('/phone', lambda _: web.FileResponse(STATIC / 'index.html'))
        app.router.add_get('/ws', self.websocket)
        app.router.add_route('*', '/api/{tail:.*}', self.api)
        app.router.add_static('/assets/', DIST / 'assets')
        app.router.add_static('/static/', STATIC)
        self.runner = web.AppRunner(app, access_log=None)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '127.0.0.1', 0)
        await site.start()
        self.url = 'http://127.0.0.1:' + str(site._server.sockets[0].getsockname()[1])
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        self.context = await self.browser.new_context(viewport={'width':1366,'height':768}, service_workers='block')
        self.page = await self.context.new_page()
        self.outbound = []
        async def prevent_external(route):
            if not route.request.url.startswith(self.url):
                self.outbound.append(route.request.url)
                await route.fulfill(status=200, content_type='text/html', body='Controlled link target')
            else:
                await route.continue_()
        await self.context.route('**/*', prevent_external)

    async def asyncTearDown(self):
        await self.context.close()
        await self.browser.close()
        await self.pw.stop()
        await self.runner.cleanup()

    async def websocket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for _ in ws:
            pass
        return ws

    async def api(self, request):
        if request.path == '/api/merged/invoke':
            body = await request.json()
            self.invocations.append(body)
            return web.json_response({'ok':True,'text':TEXT,'research':META,'request_id':body['request_id']})
        return web.json_response({'ok':True,'user_id':'fixture','messages':[],'devices':[],
                                  'commands':[],'requests':[],'memories':[],'plans':[]})

    async def verify(self, container):
        link = container.get_by_role('link', name='Kontrollü rapor')
        await link.wait_for()
        self.assertEqual(await link.get_attribute('href'), 'https://example.org/report')
        self.assertEqual(await link.get_attribute('rel'), 'noopener noreferrer')
        self.assertIn('<script>', await container.inner_text())
        frame = container.locator('iframe[title="Google arama önerileri"]')
        await frame.wait_for()
        self.assertNotIn('allow-scripts', await frame.get_attribute('sandbox'))
        self.assertNotIn('allow-same-origin', await frame.get_attribute('sandbox'))
        self.assertIn("default-src 'none'", await frame.get_attribute('srcdoc'))
        await self.page.wait_for_timeout(100)
        self.assertFalse(await self.page.evaluate('Boolean(window.sourceExecuted)'))
        self.assertNotIn('https://example.org/leak', self.outbound)
        async with self.context.expect_page() as popup:
            await link.click()
        opened = await popup.value
        await opened.wait_for_load_state()
        self.assertEqual(opened.url, 'https://example.org/report')
        self.assertTrue(await opened.evaluate('window.opener === null'))
        await opened.close()

    async def screenshot(self, name):
        directory = os.getenv('GOLGE_BROWSER_ARTIFACTS')
        if directory:
            Path(directory).mkdir(parents=True, exist_ok=True)
            await self.page.screenshot(path=str(Path(directory) / name))

    async def test_desktop_actual_invoke_renders_source_and_isolates_widget(self):
        await self.page.goto(self.url)
        await self.page.get_by_role('textbox', name='Mesaj', exact=True).fill('Güncel pil fiyatları neler?')
        await self.page.get_by_role('button', name='Gönder', exact=True).click()
        await self.verify(self.page.locator('.message.assistant').last)
        self.assertEqual(len(self.invocations), 1)
        await self.screenshot('research-desktop-fixture.png')

    async def test_iphone_actual_pwa_message_renderer_and_reload_metadata(self):
        await self.page.set_viewport_size({'width':390, 'height':844})
        await self.page.goto(self.url + '/phone')
        # Wait for boot/auth to finish before injecting this renderer fixture.
        await self.page.locator('#splash').wait_for(state='detached')
        await self.page.evaluate('''({text,meta}) => {
            document.querySelector('#splash')?.classList.add('hidden');
            document.querySelector('#login').classList.add('hidden');
            document.querySelector('#app').classList.remove('hidden');
            document.querySelector('#chatView').classList.add('active');
            addMessage('assistant',text,{research_metadata:JSON.stringify(meta)});
        }''', {'text':TEXT,'meta':META})
        await self.verify(self.page.locator('#messages'))
        self.assertTrue(await self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        await self.screenshot('research-phone-fixture.png')

if __name__ == '__main__':
    unittest.main(verbosity=2)
