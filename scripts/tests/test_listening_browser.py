"""Chromium mobile-viewport smoke: synthetic microphone, real UI event flow.

This is NOT a physical iPhone, real microphone, Ollama or Gemini test.
All speech segments, API results and approvals are intentionally synthetic.
"""
import asyncio
import json
import os
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
        self.browser=await self.playwright.chromium.launch(
            args=["--no-sandbox"],
            executable_path=os.getenv("ULTRON_TEST_BROWSER_EXECUTABLE") or None)
        self.context=await self.browser.new_context(
            viewport={"width":390,"height":844},service_workers="block")
        await self.context.add_init_script(script=MIC_STUB)
        self.api_calls=[]
        self.worker_ready=False
        self.local_jobs={}
        self.local_read_failures={}
        self.final_text="Özet: kararlar. Hiçbir işlem uygulanmadı."
        async def api(route):
            request=route.request
            path=request.url.split("/api/",1)[-1].split("?",1)[0]
            body=request.post_data_json if request.method=="POST" else None
            self.api_calls.append((path,body))
            if path=="device-presence":
                value={"devices":[{"device":"desktop","online":True,
                    "state":{"local_listening_analysis_ready":True}}]
                    if self.worker_ready else []}
            elif path=="local-listening-analysis" and request.method=="POST":
                ident=501+len(self.local_jobs)
                self.local_jobs[ident]=body
                value={"id":ident,"status":"queued","provider":"local-ollama"}
            elif path.startswith("local-listening-analysis/"):
                job=self.local_jobs[int(path.rsplit("/",1)[-1])]
                stage=job["stage"]
                if self.local_read_failures.get(stage,0):
                    self.local_read_failures[stage]-=1
                    await route.fulfill(status=503,content_type="application/json",
                                        body=json.dumps({"detail":"SECRET provider and transcript detail"}))
                    return
                value={"status":"completed","stage":stage,
                       "analysis":self.final_text if stage=="final" else "Bu test gerçek kullanıcı konuşması içermiyor.",
                       "model":"qwen3:4b","provider":"local-ollama"}
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

    async def show_probe(self):
        # Direct owner command opens diagnostics WITHOUT opening the microphone.
        await self.page.locator("#message").fill("Qwen bağlantısını test et")
        await self.page.locator("#sendBtn").click()
        await self.page.wait_for_function(
            "!document.querySelector('#longListenPanel').classList.contains('hidden')")
        self.assertEqual(await self.page.evaluate("longListenController.state()"),"idle")
        self.assertIsNone(await self.page.evaluate("window.__testSpeech.instance"))

    async def test_live_qwen_probe_checks_actual_completion_with_only_example_text(self):
        self.worker_ready=True
        await self.show_probe()
        await self.page.wait_for_function(
            "document.querySelector('#longListenQwenProbeStatus').textContent.includes('Gerçek Qwen yanıtı alındı')")
        post=[body for path,body in self.api_calls
              if path=="local-listening-analysis" and body is not None]
        self.assertEqual(len(post),1)
        self.assertEqual(post[0]["stage"],"map")
        self.assertEqual(post[0]["part"],1)
        self.assertIn("sentetik bir not",post[0]["text"])
        self.assertNotIn("mimarlık projesi",post[0]["text"])
        self.assertEqual([x for x in self.api_calls if x[0]=="listening-analysis"],[])
        self.assertIn("qwen3:4b",await self.page.locator("#longListenQwenProbeStatus").inner_text())
        self.assertEqual(self.errors,[])

    async def test_live_qwen_probe_refuses_offline_worker_without_any_analysis_upload(self):
        await self.show_probe()
        await self.page.wait_for_function(
            "document.querySelector('#longListenQwenProbeStatus').textContent.includes('Laptop GÖLGE çevrimiçi değil')")
        self.assertFalse(any(path.startswith("local-listening-analysis")
                             or path=="listening-analysis" for path,_ in self.api_calls))
        self.assertEqual(self.errors,[])

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

    async def test_local_map_reduce_final_recovers_lost_reads_and_accepts_unicode_final(self):
        self.worker_ready=True
        self.local_read_failures={'reduce':1,'final':1}
        self.final_text='Özet: '+ '😀'*5000
        await self.arm_and_emit()
        # Long synthetic transcription drives every stage through the real UI.
        await self.page.evaluate("for(let i=0;i<25;i++)window.__testSpeech.emit('Karar '+i+': '+ 'örnek '.repeat(180))")
        await self.page.locator("#longListenProviderWrap summary").click()
        await self.page.locator("#longListenProvider").select_option("local")
        await self.page.locator("#longListenAnswer").click()
        await self.page.wait_for_function("longListenController.state()==='submitted'")
        self.assertEqual(await self.page.locator("#longListenReport").text_content(),self.final_text)
        jobs=list(self.local_jobs.values())
        maps=[job for job in jobs if job['stage']=='map']
        self.assertGreater(len(maps),1)
        self.assertEqual([job['part'] for job in maps],list(range(1,len(maps)+1)))
        self.assertTrue(any(job['stage']=='reduce' for job in jobs))
        self.assertEqual(len([job for job in jobs if job['stage']=='final']),1)
        self.assertEqual(len({job['request_id'] for job in jobs}),len(jobs))
        self.assertEqual(await self.page.evaluate("longListenController.transcript()"),'')
        self.assertFalse(any(name=='listening-analysis' for name,_ in self.api_calls))
        self.assertNotIn('SECRET',await self.page.locator('#toast').text_content())
        self.assertEqual(self.errors,[])

    async def test_chat_render_failure_preserves_confirmed_panel_report(self):
        await self.arm_and_emit()
        await self.page.locator("#longListenProviderWrap summary").click()
        await self.page.locator("#longListenProvider").select_option("gemini")
        await self.page.evaluate("()=>{addMessage=()=>{throw Error('SECRET presentation detail')};}")
        await self.page.locator("#longListenAnswer").click()
        await self.page.wait_for_function("longListenController.state()==='submitted'")
        self.assertIn('Özet:',await self.page.locator('#longListenReport').text_content())
        self.assertNotIn('SECRET',await self.page.locator('#toast').text_content())
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
