"""Exercise real WebGL, local hand model, imported geometry and responsive controls."""
import json,os,sys,struct
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(root/'cache/playwright')
from integration.launcher import Services
from playwright.sync_api import sync_playwright
out=root/'logs/hologram';out.mkdir(parents=True,exist_ok=True)
# A self-contained GLB with two independent triangle meshes, no remote dependencies.
vertices=struct.pack('<9f',-1,0,0,1,0,0,0,1,0)
model={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0,1]}],'nodes':[{'mesh':0,'name':'Sol panel','translation':[-1,0,0]},{'mesh':0,'name':'Sağ panel','translation':[1,0,0]}],'meshes':[{'primitives':[{'attributes':{'POSITION':0}}]}],'buffers':[{'byteLength':len(vertices)}],'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(vertices)}],'accessors':[{'bufferView':0,'componentType':5126,'count':3,'type':'VEC3','min':[-1,0,0],'max':[1,1,0]}]}
chunk=json.dumps(model).encode();chunk+=b' '*((-len(chunk))%4)
glb=struct.pack('<III',0x46546c67,2,12+8+len(chunk)+8+len(vertices))+struct.pack('<II',len(chunk),0x4e4f534a)+chunk+struct.pack('<II',len(vertices),0x004e4942)+vertices
with Services() as service:
 service.start()
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream'])
  page=browser.new_page(viewport={'width':1440,'height':1000},permissions=['camera'])
  errors=[];console=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda msg:console.append(msg.text) if msg.type=='error' else None)
  page.goto(service.bridge.url+'/merged/hologram#'+service.bridge.token)
  page.get_by_role('dialog',name='Hologram çalışma alanı').wait_for()
  page.wait_for_function("document.querySelectorAll('.holo-parts button').length===14")
  assert page.locator('.holo-canvas canvas').count()==1
  page.wait_for_timeout(700)
  page.screenshot(path=str(out/'assembled.png'))
  page.get_by_role('button',name='Parçalara ayır',exact=True).click()
  assert page.get_by_label('Parça ayrımı',exact=True).input_value()=='1'
  page.locator('.holo-parts button').filter(has_text='Enerji çekirdeği').click()
  page.get_by_role('button',name='Sadece bu parça').click()
  page.get_by_role('button',name='Tüm parçaları göster').click()
  page.get_by_label('Tel kafes görünümü').check()
  page.get_by_label('Tel kafes görünümü').uncheck()
  page.wait_for_timeout(650)
  page.screenshot(path=str(out/'exploded.png'))
  before=page.locator('.holo-canvas canvas').evaluate('c=>c.toDataURL()')
  box=page.locator('.holo-canvas').bounding_box()
  page.mouse.move(box['x']+box['width']*.5,box['y']+box['height']*.5);page.mouse.down();page.mouse.move(box['x']+box['width']*.65,box['y']+box['height']*.55,steps=8);page.mouse.up();page.wait_for_timeout(400)
  after=page.locator('.holo-canvas canvas').evaluate('c=>c.toDataURL()');assert before!=after,'Orbit must change rendering'
  page.screenshot(path=str(out/'before-command.png'))
  page.get_by_label('Hologram komutu').fill('birleştir');page.get_by_role('button',name='Uygula',exact=True).click()
  assert page.get_by_label('Parça ayrımı',exact=True).input_value()=='0'
  with page.expect_download() as saved:
   page.get_by_role('button',name='Görüntüyü kaydet',exact=True).click()
  saved.value.save_as(str(out/'export.png'))
  assert (out/'export.png').read_bytes().startswith(b'\x89PNG')
  page.get_by_role('button',name='Robot kolu',exact=False).click();assert page.locator('.holo-parts button').count()==11
  page.get_by_role('button',name='Parçalara ayır',exact=True).click();page.wait_for_timeout(500);page.screenshot(path=str(out/'robot-arm.png'))
  page.locator(".holo-lab input[accept='.glb']").set_input_files({'name':'test.glb','mimeType':'model/gltf-binary','buffer':glb})
  page.wait_for_function("document.querySelectorAll('.holo-parts button').length===2")
  page.locator(".holo-lab input[accept='.glb']").set_input_files({'name':'bad.glb','mimeType':'model/gltf-binary','buffer':b'broken'})
  page.get_by_role('alert').wait_for();assert page.locator('.holo-parts button').count()==2
  page.get_by_label('Hologram uyarısını kapat').click()
  page.get_by_role('button',name='Enerji çekirdeği',exact=False).first.click()
  page.get_by_role('button',name='Kamerayla el kontrolünü aç',exact=False).click()
  page.get_by_role('button',name='El kontrolünü kapat',exact=False).wait_for(timeout=45000)
  page.get_by_text('El görünmüyor · hareket durdu',exact=True).wait_for(timeout=30000)
  page.screenshot(path=str(out/'hand-tracking-ready.png'))
  assert page.locator('video').evaluate('v=>v.srcObject.getVideoTracks()[0].readyState')=='live'
  page.get_by_role('button',name='El kontrolünü kapat',exact=False).click()
  assert page.locator('video').evaluate('v=>v.srcObject===null')
  for width in (375,820,1440):
   page.set_viewport_size({'width':width,'height':932});page.wait_for_timeout(150)
   assert page.locator('.holo-lab').evaluate('e=>e.scrollWidth<=e.clientWidth'),width
  page.set_viewport_size({'width':430,'height':932});page.screenshot(path=str(out/'mobile.png'),full_page=True)
  page.get_by_role('button',name='Hologramı kapat').click();assert page.get_by_role('dialog',name='Hologram çalışma alanı').count()==0
  page.get_by_role('button',name='Yeniden aç').click();page.get_by_role('dialog',name='Hologram çalışma alanı').wait_for();page.keyboard.press('Escape');assert page.get_by_role('dialog',name='Hologram çalışma alanı').count()==0
  assert not errors,errors
  (out/'checks.json').write_text(json.dumps({'status':'PASS','checks':['authenticated browser handoff','PNG export','WebGL render','orbit','explode and assemble','select and isolate','wireframe','commands','GLB import','invalid GLB preserves scene','real MediaPipe inference on synthetic camera','camera stop releases stream','responsive layouts','close and reopen'],'javascript_errors':errors,'console_errors':console},ensure_ascii=False,indent=2),encoding='utf-8')
  browser.close()
 print('HOLOGRAM_INTERACTION_PASS')
