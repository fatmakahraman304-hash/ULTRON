"""Verify native hologram rendering and its authenticated browser handoff."""
import os,sys,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
if '--child' in sys.argv:
 os.environ['MARK_SMOKE_SECONDS']='40'
 from PyQt6.QtCore import QTimer
 import integration.panel,webbrowser
 from urllib.parse import urlparse,parse_qs
 def capture_browser(url):
  parsed=urlparse(url)
  (root/'logs/hologram/browser-handoff.json').write_text(json.dumps({'path':parsed.path,'hologram':parse_qs(parsed.query).get('hologram')==['1'],'authenticated':bool(parsed.fragment)}),encoding='utf-8')
  return True
 webbrowser.open=capture_browser
 original=integration.panel.attach
 def attach(ui):
  original(ui);page=ui._web_cockpit[1]
  QTimer.singleShot(4500,lambda:page.runJavaScript("document.querySelector('.open-hologram')?.click()"))
  QTimer.singleShot(9000,lambda:page.runJavaScript("document.querySelector('.holo-camera-button')?.click()"))
  def result(data):
   (root/'logs/hologram/native-check.json').write_text(data or '{}',encoding='utf-8')
   ui._win.grab().save(str(root/'logs/hologram/native.png'))
   QTimer.singleShot(200,ui._app.quit)
  QTimer.singleShot(13000,lambda:page.runJavaScript("JSON.stringify({hologram:!!document.querySelector('.holo-lab'),parts:document.querySelectorAll('.holo-parts button').length,canvas:!!document.querySelector('.holo-canvas canvas'),error:document.querySelector('.holo-error')?.textContent||null})",result))
 integration.panel.attach=attach
 import runpy
 runpy.run_path(str(root/'mark_app.py'),run_name='__main__')
else:
 from integration.launcher import Services
 with Services() as service:
  service.start()
  result=subprocess.run([sys.executable,'-u',__file__,'--child'],cwd=root,env=service.env,timeout=65)
  assert result.returncode==0,result.returncode
  data=json.loads((root/'logs/hologram/native-check.json').read_text(encoding='utf-8'))
  assert data.get('hologram') and data.get('canvas') and data.get('parts') in (11,14) and not data.get('error'),data
  handoff=json.loads((root/'logs/hologram/browser-handoff.json').read_text(encoding='utf-8'))
  assert handoff=={'path':'/merged/dashboard','hologram':True,'authenticated':True},handoff
  print('NATIVE_HOLOGRAM_AND_BROWSER_HANDOFF_PASS',flush=True)
