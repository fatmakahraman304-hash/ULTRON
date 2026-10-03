"""Project roundtrip, undo/redo, clipping, notes and input validation in the real UI."""
import json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(root/'cache/playwright')
from integration.launcher import Services
from playwright.sync_api import sync_playwright
out=root/'logs/hologram-project';out.mkdir(parents=True,exist_ok=True)
with Services() as service:
 service.start()
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  page=browser.new_page(viewport={'width':1440,'height':1000})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(service.bridge.url+'/merged/dashboard?hologram=1#'+service.bridge.token)
  page.get_by_role('button',name='Parçalara ayır',exact=True).wait_for()
  assert page.get_by_role('button',name='Geri al',exact=True).is_disabled()
  page.get_by_role('button',name='Parçalara ayır',exact=True).click()
  assert page.get_by_label('Parça ayrımı',exact=True).input_value()=='1'
  page.get_by_role('button',name='Geri al',exact=True).click()
  assert page.get_by_label('Parça ayrımı',exact=True).input_value()=='0'
  page.get_by_role('button',name='İleri al',exact=True).click()
  assert page.get_by_label('Parça ayrımı',exact=True).input_value()=='1'
  page.locator('.holo-parts button').filter(has_text='Enerji çekirdeği').click()
  page.get_by_label('Parça notu',exact=True).fill('Merkez parçayı incele — Türkçe not.')
  page.get_by_label('Kesit görünümü',exact=True).check()
  page.get_by_label('Tel kafes görünümü',exact=True).check()
  page.wait_for_timeout(400)
  page.screenshot(path=str(out/'section-notes.png'))
  with page.expect_download() as result:
   page.get_by_role('button',name='Projeyi kaydet',exact=True).click()
  project=out/'ornek.ultron.json';result.value.save_as(str(project));data=json.loads(project.read_text(encoding='utf-8'))
  assert data['schema']=='ultron-project-v1' and len(data['parts'])==14
  assert data['view']['notes'][0]=='Merkez parçayı incele — Türkçe not.'
  assert data['view']['cut']==0 and data['view']['wire'] is True
  page.get_by_role('button',name='Robot kolu',exact=False).click();assert page.locator('.holo-parts button').count()==11
  page.locator('input[aria-label="Proje dosyası"]').set_input_files(str(project))
  page.wait_for_function("document.querySelectorAll('.holo-parts button').length===14")
  assert page.get_by_label('Parça notu',exact=True).input_value()=='Merkez parçayı incele — Türkçe not.'
  assert page.get_by_label('Kesit görünümü',exact=True).is_checked()
  assert page.get_by_label('Tel kafes görünümü',exact=True).is_checked()
  assert page.get_by_label('Parça ayrımı',exact=True).input_value()=='1'
  assert page.get_by_role('button',name='Geri al',exact=True).is_disabled()
  invalid=json.loads(project.read_text(encoding='utf-8'));invalid['view']['offsets']=[]
  page.locator('input[aria-label="Proje dosyası"]').set_input_files({'name':'bad.ultron.json','mimeType':'application/json','buffer':json.dumps(invalid).encode()})
  page.get_by_role('alert').wait_for();assert page.locator('.holo-parts button').count()==14
  assert page.get_by_label('Parça notu',exact=True).input_value()=='Merkez parçayı incele — Türkçe not.'
  page.get_by_label('Hologram uyarısını kapat').click()
  page.evaluate("window.dispatchEvent(new CustomEvent('ultron-hologram-command',{detail:'Hologramı kesit kapat.'}))")
  assert not page.get_by_label('Kesit görünümü',exact=True).is_checked()
  page.evaluate("window.dispatchEvent(new CustomEvent('ultron-hologram-command',{detail:'Geri al'}))")
  assert page.get_by_label('Kesit görünümü',exact=True).is_checked()
  for width in (375,820,1440):
   page.set_viewport_size({'width':width,'height':932});page.wait_for_timeout(100)
   assert page.locator('.holo-lab').evaluate('e=>e.scrollWidth<=e.clientWidth'),width
  assert not errors,errors
  (out/'checks.json').write_text(json.dumps({'status':'PASS','checks':['undo/redo','notes','section','self-contained project roundtrip','malformed input preserves work','spoken-command event adapter','responsive widths'],'javascript_errors':errors},indent=2),encoding='utf-8')
  browser.close()
 print('PROJECT_WORKSPACE_PASS')
