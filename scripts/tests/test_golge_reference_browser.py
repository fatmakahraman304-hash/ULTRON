"""Real Chromium mobile layout regression for the GÖLGE concept screenshot.

Test uses synthetic chat data, not private messages, a real microphone or an
authenticated production service. Catches accidental return of central phone orb and fixed-composer overlap.
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

    async def test_phone_chat_without_large_orb_and_without_composer_overlap(self):
        initial=await self.page.evaluate("""() => {
          const hero=document.querySelector('.golge-welcome');
          const orb=document.querySelector('.golge-welcome-orb');
          const chat=document.querySelector('#chatView').getBoundingClientRect();
          const list=document.querySelector('#messages').getBoundingClientRect();
          const wallpaper=getComputedStyle(document.body,'::before');
          return {
            hero:!!hero,orb:!!orb,topGap:list.top-chat.top,
            wallpaperImage:wallpaper.backgroundImage,
            wallpaperPosition:wallpaper.position,
          };
        }""")
        self.assertFalse(initial["hero"])
        self.assertFalse(initial["orb"])
        self.assertLess(initial["topGap"],30)
        # The wallpaper is a fixed pseudo-element so it does not travel with
        # the independently scrolling message list. The body itself is
        # intentionally transparent/flat on mobile.
        self.assertIn("golge-night-lake.webp",initial["wallpaperImage"])
        self.assertEqual(initial["wallpaperPosition"],"fixed")
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
            hasOrb:!!$('.golge-welcome-orb'),
            hasHero:!!$('.golge-welcome'),
            chat:rect('#chatView'),
            messagePanel:rect('#messages'),
            composer:rect('#chatView .composer'),
            scrollTop:list.scrollTop,
            scrollRange:list.scrollHeight-list.clientHeight,
            windowY:window.scrollY,
            wallpaperImage:getComputedStyle(document.body,'::before').backgroundImage,
            wallpaperPosition:getComputedStyle(document.body,'::before').position,
            menu:!!$('#panelMenuToggle'),
            microphone:!!$('#voiceBtn'),
            attachment:!!$('#plusBtn'),
          };
        }""")
        self.assertGreater(state["scrollRange"],40)
        self.assertGreater(state["scrollTop"],40)
        self.assertFalse(state["hasOrb"])
        self.assertFalse(state["hasHero"])
        self.assertLess(state["messagePanel"]["top"]-state["chat"]["top"],30)
        self.assertLessEqual(state["messagePanel"]["bottom"],state["composer"]["top"]+6)
        self.assertTrue(state["menu"] and state["microphone"] and state["attachment"])
        self.assertLess(state["windowY"],4)
        self.assertIn("golge-night-lake.webp",state["wallpaperImage"])
        self.assertEqual(state["wallpaperPosition"],"fixed")
        # CSS, not an edited screenshot: inspect computed pseudo-elements
        # on both message roles and the online badge on the actual mobile DOM.
        red_marks=await self.page.evaluate("""() => {
          const $=s=>document.querySelector(s);
          const assistant=getComputedStyle($('#messages .msg.assistant'),'::after');
          const owner=getComputedStyle($('#messages .msg.user'),'::after');
          const ownerLabel=getComputedStyle($('#messages .msg.user'),'::before');
          const online=getComputedStyle($('.online'));
          const readyDot=getComputedStyle($('.online .dot'));
          return {
            assistantDisplay:assistant.display,assistantContent:assistant.content,
            ownerDisplay:owner.display,ownerContent:owner.content,
            ownerLabelColor:ownerLabel.color,
            badgeBorderColor:online.borderTopColor,
            badgeDotColor:readyDot.backgroundColor,
          };
        }""")
        self.assertEqual(red_marks["assistantDisplay"],"none")
        self.assertEqual(red_marks["ownerDisplay"],"none")
        self.assertEqual(red_marks["assistantContent"],"none")
        self.assertEqual(red_marks["ownerContent"],"none")
        self.assertEqual(red_marks["ownerLabelColor"],"rgb(184, 213, 219)")
        self.assertEqual(red_marks["badgeBorderColor"],"rgb(49, 84, 96)")
        self.assertEqual(red_marks["badgeDotColor"],"rgb(4, 219, 173)")
        # The real menu handler is still available without permanently shown tabs.
        await self.page.locator("#panelMenuToggle").click()
        self.assertEqual(await self.page.locator("#panelMenuToggle").get_attribute("aria-expanded"),"true")


if __name__=="__main__":
    unittest.main()
