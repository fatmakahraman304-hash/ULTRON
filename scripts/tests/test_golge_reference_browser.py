"""Real Chromium mobile layout regression for the GÖLGE concept screenshot.

Test uses synthetic chat data, not private messages, a real microphone or an
authenticated production service. Catches fixed-composer overlap and lost orb.
"""
import asyncio
import unittest
from pathlib import Path
from aiohttp import web
from playwright.async_api import async_playwright

STATIC=Path(__file__).resolve().parents[2]/"ultron/cloud_service/static"


class GolgeReferenceMobileBrowser(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async def index(_):
            return web.FileResponse(STATIC/"index.html")
        async def asset(req):
            name=req.match_info["name"]
            candidate=(STATIC/name).resolve()
            if STATIC.resolve() not in candidate.parents or not candidate.is_file():
                raise web.HTTPNotFound()
            return web.FileResponse(candidate)
        async def mock_api(_):
            return web.json_response({
                "ok":True,"user_id":"ci-synthetic","messages":[],
                "devices":[],"commands":[],"memories":[],"plans":[],
                "connected":False,"status":"idle",
            })
        self.app=web.Application()
        self.app.router.add_get("/",index)
        self.app.router.add_get("/static/{name:.*}",asset)
        self.app.router.add_route("*","/api/{tail:.*}",mock_api)
        self.runner=web.AppRunner(self.app);await self.runner.setup()
        self.site=web.TCPSite(self.runner,"127.0.0.1",0);await self.site.start()
        self.port=self.site._server.sockets[0].getsockname()[1]
        self.playwright=await async_playwright().start()
        self.browser=await self.playwright.chromium.launch(headless=True)
        self.page=await self.browser.new_page(viewport={"width":390,"height":844},
                                              device_scale_factor=2,is_mobile=True,
                                              has_touch=True)
        await self.page.goto(f"http://127.0.0.1:{self.port}/",wait_until="domcontentloaded")
        await self.page.evaluate("""() => {
          document.querySelector('#splash').classList.add('hidden');
          document.querySelector('#login').classList.add('hidden');
          document.querySelector('#app').classList.remove('hidden');
          document.querySelector('#chatView').classList.add('active');
        }""")

    async def asyncTearDown(self):
        await self.page.close()
        await self.browser.close()
        await self.playwright.stop()
        await self.runner.cleanup()

    async def test_cyan_orb_chat_and_composer_remain_visible_with_long_history(self):
        initial=await self.page.evaluate("""() => {
          const orb=document.querySelector('.golge-welcome-orb');
          const composer=document.querySelector('#chatView .composer');
          const css=getComputedStyle(document.querySelector('body')).backgroundImage;
          return {orb:orb.getBoundingClientRect().toJSON(),
                  composer:composer.getBoundingClientRect().toJSON(),css};
        }""")
        self.assertGreater(initial["orb"]["width"],145)
        self.assertLess(initial["orb"]["bottom"],initial["composer"]["top"])
        self.assertIn("radial-gradient",initial["css"])
        await self.page.evaluate("""() => {
          const list=document.querySelector('#messages');
          for(let i=0;i<36;i++){
            const e=document.createElement('div');
            e.className='msg '+(i%2===0?'user':'assistant');
            e.textContent='Sahte test mesajı '+i+' · GÖLGE sohbet arayüzü düzeni.';
            list.appendChild(e);
          }
          scrollChatToBottom(false);
        }""")
        await self.page.wait_for_timeout(220)
        state=await self.page.evaluate("""() => {
          const $=s=>document.querySelector(s);
          const rect=s=>$(s).getBoundingClientRect().toJSON();
          const list=$('#messages');
          return {
            orb:rect('.golge-welcome-orb'),
            hero:rect('.golge-welcome'),
            messagePanel:rect('#messages'),
            composer:rect('#chatView .composer'),
            scrollTop:list.scrollTop,
            scrollRange:list.scrollHeight-list.clientHeight,
            windowY:window.scrollY,
            menu:!!$('#panelMenuToggle'),
            microphone:!!$('#voiceBtn'),
            attachment:!!$('#plusBtn'),
          };
        }""")
        self.assertGreater(state["scrollRange"],40)
        self.assertGreater(state["scrollTop"],40)
        self.assertGreater(state["orb"]["width"],105)
        self.assertGreater(state["hero"]["height"],135)
        self.assertLess(state["hero"]["bottom"],state["messagePanel"]["bottom"])
        self.assertLessEqual(state["messagePanel"]["bottom"],state["composer"]["top"]+6)
        self.assertTrue(state["menu"] and state["microphone"] and state["attachment"])
        self.assertLess(state["windowY"],4)
        # The real menu handler is still available without permanently shown tabs.
        await self.page.locator("#panelMenuToggle").click()
        self.assertEqual(await self.page.locator("#panelMenuToggle").get_attribute("aria-expanded"),"true")


if __name__=="__main__":
    unittest.main()
