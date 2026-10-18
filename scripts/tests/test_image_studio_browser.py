"""Chromium integration: real UI, synthetic image/provider. NOT a real AI test."""

import asyncio
import base64
import io
import unittest
from PIL import Image
from aiohttp import web
import test_research_source_ui as harness

f = io.BytesIO()
Image.new("RGB", (768, 1376), "#086c87").save(f, format="PNG")
PNG = f.getvalue()


class ImageStudioBrowserTests(harness.ResearchSourceBrowserTests):
    # Inherit infrastructure only; source-link tests are exercised separately.
    test_desktop_actual_invoke_renders_source_and_isolates_widget = None
    test_iphone_actual_pwa_message_renderer_and_reload_metadata = None

    async def api(self, request):
        if request.path.endswith("/status"):
            return web.json_response(
                {
                    "available": True,
                    "detail": "DEMO TEST — sahte sağlayıcı; gerçek ücret yok.",
                }
            )
        if request.path.endswith("/generate"):
            body = await request.json()
            self.invocations.append(body)
            if getattr(self, "delay", False):
                await asyncio.sleep(0.5)
            return web.json_response(
                {
                    "status": "completed",
                    "conversation_id": body["conversation_id"],
                    "request_id": body["request_id"],
                    "assistant_message_id": 900,
                    "user_message_id": 899,
                    "image_url": "/api/image/generated/900",
                    "mime_type": "image/png",
                }
            )
        if "/generated/900" in request.path:
            return web.Response(body=PNG, content_type="image/png")
        return await super().api(request)

    async def test_desktop_generation_and_download(self):
        await self.page.goto(self.url)
        await self.page.get_by_role("textbox", name="Mesaj", exact=True).fill(
            "DEMO TEST — dikey Ferrari fotoğrafı oluştur"
        )
        await self.page.get_by_role("button", name="Gönder", exact=True).click()
        await self.page.get_by_role(
            "button", name="Ücretli üretimi onayla", exact=True
        ).click()
        img = self.page.get_by_alt_text("GÖLGE tarafından üretilen görsel")
        await img.wait_for()
        await self.page.wait_for_function(
            "document.querySelector('figure img')?.naturalWidth===768"
        )
        self.assertEqual(len(self.invocations), 1)
        self.assertTrue(self.invocations[0]["cost_approved"])
        self.assertEqual(self.invocations[0]["aspect_ratio"], "9:16")
        await self.page.wait_for_timeout(300)
        await self.screenshot("image-studio-desktop-fixture.png")
        await self.page.get_by_role("button", name="Görseli büyüt").click()
        self.assertTrue(await self.page.locator("dialog").is_visible())
        await self.page.get_by_role("button", name="Kapat", exact=True).click()
        async with self.page.expect_download():
            await self.page.get_by_role("link", name="Görseli indir / kaydet").click()

    async def phone(self):
        await self.page.set_viewport_size({"width": 390, "height": 844})
        await self.page.goto(self.url + "/phone")
        await self.page.locator("#splash").wait_for(state="detached")
        await self.page.evaluate(
            """() => {document.querySelector('#splash')?.classList.add('hidden');document.querySelector('#login').classList.add('hidden');document.querySelector('#app').classList.remove('hidden');document.querySelector('#chatView').classList.add('active');} """
        )

    async def test_phone_generation_reload_and_download(self):
        await self.phone()
        await self.page.evaluate(
            "void sendImageCreation('DEMO TEST — Mersin fotoğrafı oluştur',addMessage('user','DEMO TEST — Mersin fotoğrafı oluştur'))"
        )
        await self.page.get_by_role(
            "button", name="Ücretli üretimi onayla", exact=True
        ).click()
        await self.page.wait_for_function(
            "document.querySelector('#messages img')?.naturalWidth===768"
        )
        self.assertEqual(len(self.invocations), 1)
        await self.page.reload()
        await self.page.locator("#splash").wait_for(state="detached")
        await self.page.evaluate(
            """()=>{document.querySelector('#splash')?.classList.add('hidden');document.querySelector('#login').classList.add('hidden');document.querySelector('#app').classList.remove('hidden');document.querySelector('#chatView').classList.add('active');addMessage('assistant','DEMO TEST — kalıcı kayıttan görsel',{id:900,has_generated_image:true});}"""
        )
        await self.page.wait_for_function(
            "document.querySelector('#messages img')?.naturalWidth===768"
        )
        self.assertTrue(
            await self.page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        )
        self.assertEqual(
            await self.page.get_by_role(
                "link", name="Görseli indir / kaydet"
            ).get_attribute("href"),
            "/api/image/generated/900",
        )
        await self.screenshot("image-studio-phone-fixture.png")

    async def test_phone_late_cancel_and_conversation_switch(self):
        await self.phone()
        self.delay = True
        await self.page.evaluate(
            "void sendImageCreation('DEMO TEST fotoğraf oluştur',null)"
        )
        await self.page.get_by_role(
            "button", name="Ücretli üretimi onayla", exact=True
        ).click()
        await self.page.wait_for_function("activeImageJob!==null")
        await self.page.evaluate("cancelActiveChat()")
        await self.page.wait_for_timeout(700)
        self.assertEqual(await self.page.locator("#messages img").count(), 0)
        await self.page.evaluate(
            "void sendImageCreation('DEMO TEST fotoğraf oluştur',null)"
        )
        await self.page.get_by_role(
            "button", name="Ücretli üretimi onayla", exact=True
        ).click()
        await self.page.wait_for_function("activeImageJob!==null")
        await self.page.evaluate("conversationId=crypto.randomUUID()")
        await self.page.wait_for_timeout(700)
        self.assertEqual(await self.page.locator("#messages img").count(), 0)

    async def test_desktop_native_history_reload_is_deduplicated_and_never_generates(
        self,
    ):
        await self.context.add_init_script("""
   window.qt={webChannelTransport:{}};
   window.QWebChannel=function(_,callback){callback({objects:{mark:{send(){},action(){},ready(){
    window.nativeReceive(JSON.stringify({kind:'cloud_messages',data:[
     {id:898,role:'user',content:'DEMO TEST Ferrari fotoğrafı oluştur',created_at:new Date().toISOString()},
     {id:900,role:'assistant',content:'DEMO TEST — geçmiş görsel',has_generated_image:true,created_at:new Date().toISOString()}
    ]}));
   },message:{connect(fn){window.nativeReceive=fn},disconnect(){}}}}});};
   const append=HTMLHeadElement.prototype.appendChild;
   HTMLHeadElement.prototype.appendChild=function(node){if(node.src?.startsWith('qrc:')){setTimeout(()=>node.onload?.(),0);return node;}return append.call(this,node);};
  """)
        await self.page.goto(self.url)
        await self.page.get_by_alt_text("GÖLGE tarafından üretilen görsel").wait_for()
        await self.page.evaluate(
            "nativeReceive(JSON.stringify({kind:'cloud_messages',data:[{id:900,role:'assistant',content:'DEMO TEST — geçmiş görsel',has_generated_image:true}]}))"
        )
        self.assertEqual(
            await self.page.get_by_alt_text("GÖLGE tarafından üretilen görsel").count(),
            1,
        )
        await self.page.reload()
        await self.page.get_by_alt_text("GÖLGE tarafından üretilen görsel").wait_for()
        self.assertEqual(self.invocations, [])

    async def test_refusing_cost_never_calls_generation(self):
        await self.page.goto(self.url)
        await self.page.get_by_role("textbox", name="Mesaj", exact=True).fill(
            "Ferrari fotoğrafı oluştur"
        )
        await self.page.get_by_role("button", name="Gönder", exact=True).click()
        await self.page.get_by_role("button", name="Vazgeç", exact=True).click()
        await self.page.wait_for_timeout(400)
        self.assertEqual(self.invocations, [])

    async def test_pending_consent_keeps_event_loop_live_and_escape_aborts(self):
        for phone in (False, True):
            if phone:
                await self.phone()
                await self.page.evaluate(
                    "void sendImageCreation('DEMO TEST fotoğraf oluştur',null)"
                )
            else:
                await self.page.goto(self.url)
                await self.page.get_by_role("textbox", name="Mesaj", exact=True).fill(
                    "DEMO TEST fotoğraf oluştur"
                )
                await self.page.get_by_role("button", name="Gönder", exact=True).click()
            consent = self.page.get_by_role("dialog", name="Görsel üretimi maliyet onayı")
            await consent.wait_for()
            # A live JS timer is necessary for audio callbacks; this is not a mic test.
            self.assertTrue(await self.page.evaluate(
                "new Promise(resolve=>setTimeout(()=>resolve(true),30))"
            ))
            await self.page.keyboard.press("Escape")
            await consent.wait_for(state="detached")
            self.assertEqual(self.invocations, [])
            self.assertEqual(await self.page.locator("figure img, #messages img").count(), 0)

    async def test_phone_conversation_changed_while_consent_pending_never_dispatches(self):
        await self.phone()
        await self.page.evaluate("void sendImageCreation('DEMO TEST fotoğraf oluştur',null)")
        await self.page.get_by_role("dialog", name="Görsel üretimi maliyet onayı").wait_for()
        await self.page.evaluate("conversationId=crypto.randomUUID()")
        await self.page.get_by_role("button", name="Ücretli üretimi onayla", exact=True).click()
        await self.page.wait_for_function("activeImageJob===null")
        self.assertEqual(self.invocations, [])



class FreeLocalImageBrowserTests(harness.ResearchSourceBrowserTests):
    """Actual built UI with a controlled local-image device queue; no GPU/model."""
    test_desktop_actual_invoke_renders_source_and_isolates_widget = None
    test_iphone_actual_pwa_message_renderer_and_reload_metadata = None

    async def api(self, request):
        if request.path.endswith('/status'):
            return web.json_response({'available':True,'provider':'comfyui_local','requires_cost_approval':False,'detail':'DEMO TEST — ücretsiz yerel SD 1.5'})
        if request.path.endswith('/generate'):
            self.invocations.append(await request.json());self.polls=0
            return web.json_response({'status':'queued','request_id':self.invocations[-1]['request_id']},status=202)
        if '/requests/' in request.path:
            self.polls+=1
            body=self.invocations[-1]
            if self.polls==1 or getattr(self,'hold',False):
                return web.json_response({'status':'running'},status=202)
            return web.json_response({'status':'completed','request_id':body['request_id'],
                'conversation_id':body['conversation_id'],'assistant_message_id':900,
                'user_message_id':899,'image_url':'/api/image/generated/900','mime_type':'image/png'})
        if '/generated/900' in request.path:
            f=io.BytesIO();Image.new('RGB',(384,640),'cyan').save(f,format='PNG')
            return web.Response(body=f.getvalue(),content_type='image/png')
        return await super().api(request)

    async def test_desktop_free_queue_never_requests_paid_consent(self):
        await self.page.goto(self.url)
        await self.page.get_by_role('textbox',name='Mesaj',exact=True).fill('DEMO TEST — dikey Ferrari fotoğrafı oluştur')
        await self.page.get_by_role('button',name='Gönder',exact=True).click()
        await self.page.get_by_alt_text('GÖLGE tarafından üretilen görsel').wait_for()
        self.assertEqual(len(self.invocations),1)
        self.assertFalse(self.invocations[0]['cost_approved'])
        self.assertGreaterEqual(self.polls,2)
        self.assertEqual(await self.page.get_by_role('dialog',name='Görsel üretimi maliyet onayı').count(),0)
        await self.screenshot('free-image-desktop-fixture.png')

    async def test_phone_free_queue_persists_image_reference(self):
        await ImageStudioBrowserTests.phone(self)
        await self.page.evaluate("void sendImageCreation('DEMO TEST — ücretsiz dikey görsel oluştur',addMessage('user','DEMO TEST — sentetik ComfyUI görsel testi'))")
        await self.page.wait_for_function("document.querySelector('#messages img')?.naturalWidth===384")
        self.assertFalse(self.invocations[0]['cost_approved'])
        self.assertEqual(await self.page.get_by_role('dialog',name='Görsel üretimi maliyet onayı').count(),0)
        self.assertTrue(await self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        self.assertEqual(await self.page.get_by_role('link',name='Görseli indir / kaydet').get_attribute('href'),'/api/image/generated/900')
        await self.screenshot('free-image-phone-fixture.png')

    async def test_phone_free_pending_cancel_stops_polling(self):
        await ImageStudioBrowserTests.phone(self);self.hold=True
        await self.page.evaluate("void sendImageCreation('DEMO TEST fotoğraf oluştur',null)")
        await self.page.wait_for_function("activeImageJob!==null")
        await self.page.keyboard.press('Escape')
        await self.page.wait_for_timeout(1000)
        self.assertEqual(await self.page.locator('#messages img').count(),0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
