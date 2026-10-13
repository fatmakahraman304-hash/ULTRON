"""Actual WebGL UI; synthetic chat API, no cloud model or hardware claims."""
import asyncio
import json
import struct
import unittest
from pathlib import Path
from aiohttp import web
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[2]
STATIC=ROOT/'ultron/cloud_service/static'

def glb(external=False):
    binary=struct.pack('<9f',0,0,0,1,0,0,0,1,0)
    payload={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],
        'nodes':[{'mesh':0,'name':'Test parçası'}],'meshes':[{'primitives':[{'attributes':{'POSITION':0}}]}],
        'accessors':[{'bufferView':0,'componentType':5126,'count':3,'type':'VEC3','min':[0,0,0],'max':[1,1,0]}],
        'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(binary)}],'buffers':[{'byteLength':len(binary)}]}
    if external:payload['buffers'][0]['uri']='https://example.invalid/private.bin'
    text=json.dumps(payload).encode();text+=b' '*((-len(text))%4)
    return struct.pack('<III',0x46546c67,2,28+len(text)+len(binary))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(binary),0x004e4942)+binary

class SceneBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async def index(_):return web.FileResponse(STATIC/'index.html')
        app=web.Application();app.router.add_get('/',index);app.router.add_static('/static/',STATIC)
        app.router.add_static('/desktop/',ROOT/'ultron/frontend/dist')
        self.runner=web.AppRunner(app,access_log=None);await self.runner.setup()
        site=web.TCPSite(self.runner,'127.0.0.1',0);await site.start()
        self.url='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
        self.pw=await async_playwright().start()
        self.browser=await self.pw.chromium.launch(args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        self.context=await self.browser.new_context(viewport={'width':430,'height':900},service_workers='block')
        self.calls=[]
        async def api(route):
            self.calls.append(route.request.url)
            await route.fulfill(json={'messages':[],'devices':[],'requests':[],'memories':[],'plans':[],'commands':[],'ok':True})
        await self.context.route('**/api/**',api)
        self.page=await self.context.new_page();self.errors=[]
        self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        await self.page.goto(self.url)
        await self.page.wait_for_function("!document.querySelector('#app').classList.contains('hidden')")
        await self.page.evaluate('voiceEnabled=false')

    async def asyncTearDown(self):
        await self.browser.close();await self.pw.stop();await self.runner.cleanup()

    async def state(self):return await self.page.locator('#sceneCanvas').evaluate('(el)=>JSON.parse(el.dataset.scene)')

    async def engine(self):
        self.assertFalse(await self.page.evaluate('!!window.ULTRONScene'))
        await self.page.locator('#message').fill('Bir motorun 3D modelini göster')
        await self.page.evaluate('send(false)')
        await self.page.wait_for_function("document.querySelector('#sceneCanvas').dataset.scene")
        self.assertEqual(len((await self.state())['parts']),21)

    async def command(self,text):
        await self.page.locator('#sceneCommand').fill(text)
        await self.page.locator('#sceneForm button[type=submit]').click()
        await self.page.wait_for_function('!sceneCommandBusy')

    async def test_mobile_transform_selection_remove_undo_without_model_calls(self):
        await self.engine();initial=await self.state()
        await self.command('onu sağa taşı');self.assertEqual((await self.state())['offsets'][0],[1,0,0])
        await self.command('yukarı kaldır');self.assertEqual((await self.state())['offsets'][0],[1,1,0])
        await self.command('onu sola 90 derece döndür')
        rotated=await self.state();self.assertNotEqual(rotated['rotations'],initial['rotations'])
        await self.command('onu kaldır');self.assertEqual(await self.state(),rotated)
        self.assertIn('Yukarı mı',await self.page.locator('#sceneNotice').inner_text())
        await self.command('onu kenara al');await self.command('onu büyüt')
        self.assertEqual((await self.state())['scales'][0],[1.25]*3)
        await self.command('onu yok et');self.assertEqual((await self.state())['parts'],[])
        await self.command('geri al');self.assertEqual(len((await self.state())['parts']),21)
        await self.command('Piston 1 seç');self.assertEqual((await self.state())['selected'],5)
        await self.command('onu yok et');self.assertEqual(len((await self.state())['parts']),20)
        await self.command('geri al');self.assertEqual(len((await self.state())['parts']),21)
        await self.command('sahneyi sıfırla')
        reset=await self.state()
        for key in ['offsets','rotations','scales','removed']:
            self.assertEqual(reset[key],initial[key],key)
        self.assertFalse(any(u.endswith(('/api/chat','/api/local-chat')) for u in self.calls))
        self.assertEqual(self.errors,[])
        await self.page.screenshot(path='/tmp/ultron-scene-mobile.png')

    async def test_shapes_and_freeform_design_preserve_scene_on_bad_output(self):
        await self.engine()
        for text,name in [('daire','Daire'),('kare çiz','Kare'),('üçgen oluştur','Üçgen')]:
            await self.command(text)
            self.assertEqual((await self.state())['parts'][0]['name'],name)
            self.assertEqual(len((await self.state())['parts']),1)
        design={'name':'Masa','parts':[
            {'name':'Tabla','shape':'box','size':[3,.2,2],'position':[0,1,0],'rotation':[0,0,0]},
            {'name':'Ayak','shape':'cylinder','size':[.3,2,.3],'position':[0,0,0],'rotation':[0,0,0]}]}
        async def good(route):
            self.assertIn('masa',route.request.post_data_json['description'])
            await route.fulfill(json={'design':design})
        await self.page.route('**/api/scene-design',good)
        await self.command('bir masa modeli oluştur')
        state=await self.state();self.assertEqual(len(state['parts']),2)
        self.assertEqual(state['parts'][0]['name'],'Tabla')
        self.assertIn('kavramsal',await self.page.locator('#sceneNotice').inner_text())
        await self.command('onu sağa taşı')
        state=await self.state()
        await self.page.unroute('**/api/scene-design')
        await self.page.route('**/api/scene-design',lambda route:route.fulfill(json={'design':{'code':'alert(1)'}}))
        await self.command('bir ejderha modeli oluştur')
        self.assertEqual(await self.state(),state)
        self.assertIn('üretilemedi',await self.page.locator('#sceneNotice').inner_text())
        self.assertEqual(self.errors,[])

    async def test_mobile_design_uses_local_queue_without_chat_history(self):
        await self.engine()
        await self.page.evaluate("refreshAutoBrain=async()=> 'local'")
        requests=[]
        design={'name':'Sandalye','parts':[{'name':'Oturak','shape':'box','size':[2,.2,2],'position':[0,0,0],'rotation':[0,0,0]}]}
        async def local(route):
            requests.append(route.request)
            if route.request.method=='POST':await route.fulfill(json={'command_id':91},status=202)
            else:await route.fulfill(json={'status':'completed','reply':json.dumps(design)})
        await self.page.route('**/api/local-scene-design**',local)
        previous=await self.page.evaluate('conversationId')
        await self.command('sandalye modeli oluştur')
        self.assertEqual((await self.state())['parts'][0]['name'],'Oturak')
        self.assertEqual(await self.page.evaluate('conversationId'),previous)
        self.assertEqual(requests[0].post_data_json['description'],'sandalye')
        self.assertNotIn('message',requests[0].post_data_json)
        self.assertFalse(any('/api/scene-design' in u or u.endswith('/api/local-chat') for u in self.calls))
        self.assertEqual(self.errors,[])

    async def test_generated_design_does_not_replace_closed_scene(self):
        await self.engine();initial=await self.state()
        entered=asyncio.Event();release=asyncio.Event()
        async def delay(route):
            entered.set();await release.wait()
            await route.fulfill(json={'design':{'name':'Test','parts':[{'name':'Test','shape':'box','size':[1,1,1],'position':[0,0,0],'rotation':[0,0,0]}]}})
        await self.page.route('**/api/scene-design',delay)
        await self.page.locator('#sceneCommand').fill('bir masa modeli oluştur')
        await self.page.locator('#sceneForm button[type=submit]').click()
        await asyncio.wait_for(entered.wait(),5)
        await self.page.locator('#closeMobileHologram').click();release.set()
        await self.page.wait_for_function('!sceneCommandBusy')
        self.assertEqual(await self.state(),initial)
        self.assertEqual(await self.page.evaluate('currentView'),'chat')
        self.assertEqual(self.errors,[])

    async def test_closing_workspace_during_lazy_load_does_not_reopen_it(self):
        entered=asyncio.Event();release=asyncio.Event()
        async def delay(route):
            entered.set();await release.wait();await route.continue_()
        await self.page.route('**/static/scene-control.js',delay)
        await self.page.locator('#message').fill('Bir motorun 3D modelini göster')
        await self.page.evaluate('void send(false)')
        await asyncio.wait_for(entered.wait(),5)
        await self.page.locator('#closeMobileHologram').click()
        release.set()
        await self.page.wait_for_function('!chatSending')
        self.assertEqual(await self.page.evaluate('currentView'),'chat')
        self.assertEqual(await self.page.locator('#sceneCanvas canvas').count(),0)
        self.assertEqual(self.errors,[])

    async def test_glb_load_and_external_reference_rejection(self):
        await self.engine();picker=self.page.locator('#sceneCanvas input[type=file]')
        await picker.set_input_files({'name':'part.glb','mimeType':'model/gltf-binary','buffer':glb()})
        await self.page.wait_for_function("document.querySelector('#sceneNotice').textContent==='Modeli sahneye yükledim.'")
        loaded=await self.state();self.assertEqual(len(loaded['parts']),1)
        await picker.set_input_files({'name':'external.glb','mimeType':'model/gltf-binary','buffer':glb(True)})
        await self.page.wait_for_function("document.querySelector('#sceneNotice').textContent.startsWith('Model yüklenemedi')")
        self.assertEqual(await self.state(),loaded);self.assertEqual(self.errors,[])

    async def test_reset_restores_geometry_and_is_undoable_after_project_reload(self):
        await self.page.goto(self.url+'/desktop/hologram.html')
        await self.page.locator('.holo-canvas canvas').wait_for()
        async def save():
            async with self.page.expect_download() as pending:
                await self.page.get_by_role('button',name='Projeyi kaydet',exact=True).click()
            return json.loads(Path(await (await pending.value).path()).read_text())
        async def command(text):
            field=self.page.locator('.holo-bottom input')
            await field.fill(text);await field.press('Enter')
        initial=await save()
        for text in ['onu döndür','onu büyüt','onu sağa taşı','onu yok et']:
            await command(text)
        changed=await save()
        await self.page.get_by_label('Proje dosyası').set_input_files({'name':'changed.json','mimeType':'application/json','buffer':json.dumps(changed).encode()})
        await self.page.get_by_role('button',name='Sıfırla',exact=True).click()
        reset=await save()
        for key in ['offsets','rotations','scales','removed']:
            self.assertEqual(reset['view'][key],initial['view'][key],key)
        await command('geri al')
        undone=await save()
        for key in ['offsets','rotations','scales','removed']:
            self.assertEqual(undone['view'][key],changed['view'][key],key)
        await command('ileri al')
        redone=await save()
        self.assertEqual(redone['view'],reset['view'])
        self.assertEqual(self.errors,[])

    async def test_desktop_command_event_drives_real_hologram(self):
        await self.page.set_viewport_size({'width':1280,'height':900})
        await self.page.goto(self.url+'/desktop/hologram.html');await self.page.locator('.holo-canvas canvas').wait_for()
        await self.page.evaluate("window.dispatchEvent(new CustomEvent('ultron-hologram-command',{detail:'Bir motorun 3D modelini göster'}))")
        await self.page.get_by_text('KAVRAMSAL MOTOR',exact=True).wait_for()
        self.assertEqual(await self.page.locator('.holo-parts button').count(),21)
        field=self.page.locator('.holo-bottom input')
        for t in ['onu döndür','onu yukarı kaldır','onu yok et']:
            await field.fill(t);await field.press('Enter')
        self.assertEqual(await self.page.locator('.holo-parts button').count(),0)
        await field.fill('geri al');await field.press('Enter')
        self.assertEqual(await self.page.locator('.holo-parts button').count(),21)
        async with self.page.expect_download() as pending:
            await self.page.get_by_role('button',name='Projeyi kaydet',exact=True).click()
        download=await pending.value
        saved=json.loads(Path(await download.path()).read_text())
        self.assertEqual(saved['view']['offsets'][0][1],1)
        self.assertNotEqual(saved['view']['rotations'][0],[0,0,0])
        await self.page.get_by_label('Proje dosyası').set_input_files({'name':'roundtrip.json','mimeType':'application/json','buffer':json.dumps(saved).encode()})
        await self.page.get_by_text('KAVRAMSAL MOTOR',exact=True).wait_for()
        self.assertEqual(await self.page.locator('.holo-parts button').count(),21)
        self.assertEqual(self.errors,[])
        await self.page.screenshot(path='/tmp/ultron-scene-desktop.png')

if __name__=='__main__':unittest.main(verbosity=2)
