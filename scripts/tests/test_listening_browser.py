"""Chromium mobile-viewport smoke: synthetic microphone, real UI event flow.

This is NOT a physical iPhone, real microphone, Ollama or Gemini test.
All speech segments, API results and approvals are intentionally synthetic.
"""
import asyncio
import json
import unittest
from pathlib import Path
from aiohttp import web
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "ultron/cloud_service/static"
MIC_STUB = r"""
(() => {
 window.__testApproved = true;
 window.__testConfirmCount = 0;
 window.confirm = function(message){
   window.__testConfirmCount++;
   window.__testLastConsent = message;
   return window.__testApproved;
 };
 window.__testSpeech = {
   instance: null,
   emit(text) {
     const r=this.instance;
     if (!r||!r.onresult) throw new Error('SpeechRecognition inactive');
     const row=[{transcript:text}];
     row.isFinal=true;
     const index=r.results.length;
     r.results.push(row);
     r.onresult({resultIndex:index,results:r.results});
   }
 };
 class FakeRecognition {
   constructor(){this.results=[];this.stopped=false;window.__testSpeech.instance=this;}
   start(){this.started=true;}
   stop(){this.stopped=true;}
 }
 window.SpeechRecognition=FakeRecognition;
 window.webkitSpeechRecognition=FakeRecognition;
})();
"""

class ListeningBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async def index(_): return web.FileResponse(STATIC / "index.html")
        app=web.Application()
        app.router.add_get("/",index)
        app.router.add_static("/static/",STATIC)
        self.runner=web.AppRunner(app,access_log=None)
        await self.runner.setup()
        server=web.TCPSite(self.runner,"127.0.0.1",0)
        await server.start()
        self.url="http://127.0.0.1:"+str(server._server.sockets[0].getsockname()[1])
        self.playwright=await async_playwright().start()
        self.browser=await self.playwright.chromium.launch(args=["--no-sandbox"])
        self.context=await self.browser.new_context(
            viewport={"width":390,"height":844},service_workers="block")
        await self.context.add_init_script(script=MIC_STUB)
        self.api_calls=[]
        async def api(route):
            request=route.request
            path=request.url.split("/api/",1)[-1].split("?",1)[0]
            body=request.post_data_json if request.method=="POST" else None
            self.api_calls.append((path,body))
            if path=="device-presence":
                value={"devices":[]}
            elif path=="listening-analysis":
                value={"stage":body["stage"],
                       "analysis": "Not: iş uygulanmadı" if body["stage"]=="map" else "Özet: tasarım kararı. Hiçbir işlem uygulanmadı.",
                       "saved":False}
            elif path=="health":
                value={"ok":True}
            else:
                value={"messages":[],"devices":[],"requests":[],"memories":[],
                       "plans":[],"commands":[],"ok":True}
            await route.fulfill(status=200,content_type="application/json",
                                body=json.dumps(value,ensure_ascii=False))
        await self.context.route("**/api/**",api)
        self.page=await self.context.new_page()
        self.errors=[]
        self.page.on("pageerror",lambda err:self.errors.append(str(err)))
        await self.page.goto(self.url)
        await self.page.wait_for_function(
            "!document.querySelector('#app').classList.contains('hidden')")
        await self.page.evaluate("voiceEnabled=false")

    async def asyncTearDown(self):
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()
        await self.runner.cleanup()

    async def arm_and_emit(self):
        await self.page.locator("#message").fill("1 saat dinle beni")
        await self.page.locator("#sendBtn").click()
        await self.page.wait_for_function("longListenController.active()===true")
        await self.page.evaluate(
            "window.__testSpeech.emit('Bugün çizim tasarımında sade bir plan seçiyorum')")
        await self.page.evaluate(
            "window.__testSpeech.emit('İkinci karar: uygulanmasını istemiyorum')")
        text=await self.page.evaluate("longListenController.transcript()")
        self.assertIn("sade bir plan",text)
        self.assertEqual([x for x in self.api_calls if x[0]=="listening-analysis"],[])
        self.assertEqual(await self.page.locator("#longListenStatus").count(),1)
        return text

    async def test_explicit_consent_before_gemini_upload_and_preserve_scene(self):
        await self.arm_and_emit()
        await self.page.locator("#longListenProviderWrap summary").click()
        await self.page.locator("#longListenProvider").select_option("gemini")
        await self.page.locator("#longListenAnswer").click()
        await self.page.wait_for_function("longListenController.state()==='submitted'")
        calls=[x for x in self.api_calls if x[0]=="listening-analysis"]
        self.assertEqual([x[1]["stage"] for x in calls],["map","final"])
        self.assertGreater(await self.page.evaluate("window.__testConfirmCount"),0)
        self.assertIn("Gemini Cloud",await self.page.evaluate("window.__testLastConsent"))
        # Reports live inside a collapsed details element; explicitly open it.
        await self.page.locator("#longListenReportWrap summary").click()
        self.assertIn("Özet:",await self.page.locator("#longListenReport").inner_text())
        self.assertEqual(await self.page.evaluate("longListenController.transcript()"),"")
        self.assertEqual(await self.page.locator("#sceneCanvas").count(),1)
        self.assertEqual(await self.page.locator("#sceneForm").count(),1)
        self.assertEqual(self.errors,[])

    async def test_denied_consent_never_uploads_and_keeps_transcript(self):
        text=await self.arm_and_emit()
        await self.page.locator("#longListenProviderWrap summary").click()
        await self.page.locator("#longListenProvider").select_option("gemini")
        await self.page.evaluate("window.__testApproved=false")
        await self.page.locator("#longListenAnswer").click()
        await self.page.wait_for_function("longListenController.state()==='ready'")
        calls=[x for x in self.api_calls if x[0]=="listening-analysis"]
        self.assertEqual(calls,[])
        self.assertEqual(await self.page.evaluate("longListenController.transcript()"),text)
        self.assertEqual(self.errors,[])

    async def test_local_only_never_leaks_to_gemini_when_worker_unavailable(self):
        text=await self.arm_and_emit()
        await self.page.locator("#longListenProviderWrap summary").click()
        await self.page.locator("#longListenProvider").select_option("local")
        await self.page.locator("#longListenAnswer").click()
        await self.page.wait_for_function("longListenController.state()==='ready'")
        self.assertFalse(any(path in ("listening-analysis","local-listening-analysis")
                             for path,_ in self.api_calls))
        self.assertEqual(await self.page.evaluate("window.__testConfirmCount"),0)
        self.assertEqual(await self.page.evaluate("longListenController.transcript()"),text)
        self.assertEqual(self.errors,[])


if __name__=="__main__":
    unittest.main()
