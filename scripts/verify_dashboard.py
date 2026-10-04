"""Real backend + WebGL, responsive, socket, memory and approval-boundary checks."""
import json,os,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(root/'cache/playwright')
from integration.launcher import Services
from playwright.sync_api import sync_playwright
out=root/'logs/dashboard';out.mkdir(parents=True,exist_ok=True)
with Services() as service:
 service.start()
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  page=browser.new_page(viewport={'width':1920,'height':1080})
  errors=[];console=[];sockets=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:console.append(m.text) if m.type=='error' else None)
  page.on('websocket',lambda ws:sockets.append(ws))
  page.goto(service.bridge.url+'/merged/dashboard#'+service.bridge.token)
  page.locator('.ultron-app').wait_for()
  page.wait_for_function("document.querySelector('.subsystems.left').textContent.includes('ONLINE')")
  page.wait_for_function("Number(document.querySelector('.core-canvas').dataset.frames)>30")
  assert len(sockets)==1,'Exactly one websocket'
  page.screenshot(path=str(root/'logs/final-ultron-1920x1080.png'))
  for w,h in [(1366,768),(1920,1080),(768,1024)]:
   page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(300)
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'overflow {w}'
  page.set_viewport_size({'width':1366,'height':768});page.screenshot(path=str(root/'logs/final-ultron-1366x768.png'))
  page.get_by_role('button',name='Panel yoğunluğunu değiştir').click();assert 'compact' in page.locator('.ultron-app').get_attribute('class')
  page.get_by_role('button',name='Terminal',exact=True).click()
  page.get_by_label('Terminal girdisi').fill('echo ULTRON_UI_CHECK')
  page.get_by_role('button',name='Çalıştır',exact=True).click()
  # Read-only command either executes or is shown for explicit approval; neither path bypasses policy.
  page.wait_for_timeout(2200)
  assert page.locator('.messages').inner_text() or page.get_by_role('dialog',name='İşlem onayı').count()
  if page.get_by_role('dialog',name='İşlem onayı').count():page.get_by_role('button',name='Reddet',exact=True).click()
  page.get_by_role('button',name='Paneli kapat').click()
  page.locator('nav button').filter(has_text='Araçlar').click()
  page.get_by_role('button',name='Hafıza',exact=True).click()
  page.get_by_label('Hafıza girdisi').fill('ultron-dashboard-verification-note')
  page.get_by_role('button',name='Not kaydet').click()
  page.wait_for_timeout(800)
  rows=service.bridge.request('/api/memory/v16')['rows']
  notes=[r for r in rows if r['content']=='ultron-dashboard-verification-note'];assert notes
  for row in notes:service.bridge.request('/api/memory/v16/delete',{'id':row['id']})
  page.get_by_role('button',name='Paneli kapat').click()
  page.get_by_role('button',name='Hologram Çalışma Alanı',exact=True).click()
  page.get_by_role('dialog',name='Hologram çalışma alanı').wait_for()
  assert page.locator('.holo-canvas canvas').count()==1
  page.locator('.holo-close').click()
  page.locator('nav button').filter(has_text='Ana Ekran').click()
  page.locator('nav button').filter(has_text='Ayarlar').click()
  page.get_by_label('Yanıt modu').select_option('fast')
  page.get_by_role('button',name='Paneli kapat').click()
  page.get_by_role('button',name='Temizle',exact=True).click()
  page.get_by_label('Mesaj',exact=True).fill('Sadece TAMAM yaz.')
  page.get_by_role('button',name='Gönder',exact=True).click()
  page.wait_for_function("document.querySelectorAll('.message.assistant').length>0",timeout=190000)
  assert page.locator('.message.assistant').inner_text().strip()
  # The same HTTP caller cannot grant itself permission, including from this UI.
  forbidden=root/'logs'/'ui-approval-must-not-exist.txt'
  denied=page.evaluate("""async path=>{const r=await fetch('/api/merged/tool',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:'write_text',arguments:{path,content:'forbidden'},approved:true})});return r.json()}""",str(forbidden))
  assert not denied.get('ok') and not forbidden.exists(),'Self approval bypass'
  # Feed an existing WS event from the authenticated socket (mic), verify renderer state propagation.
  page.evaluate("""async()=>{const w=new WebSocket(location.origin.replace('http','ws')+'/ws');await new Promise(r=>w.onopen=r);w.send(JSON.stringify({type:'mic',active:true}));setTimeout(()=>{w.send(JSON.stringify({type:'mic',active:false}));w.close();},1600)}""")
  page.wait_for_function("document.querySelector('.core-canvas').dataset.state==='LISTENING'")
  page.wait_for_timeout(2000)
  assert not errors,errors
  assert not console,console
  report={'status':'PASS','page_errors':errors,'console_errors':console,'viewports':[1920,1366,768],'checks':['WebGL 30 frames','one UI websocket','actual backend telemetry','panel density','terminal approval boundary','self approval denied','real Ollama chat','memory roundtrip','hologram lab','WebSocket core state']}
  (out/'checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
  browser.close()
print('DASHBOARD_BROWSER_PASS')
