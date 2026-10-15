"""Explicitly synthetic native bridge/audio-level UI contract, NOT mic/TTS proof."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

FIXTURE=r"""(() => {
 const listeners=new Set();window.qt={webChannelTransport:{}};
 window.__syntheticBridgeEmit=e=>listeners.forEach(fn=>fn(JSON.stringify(e)));
 window.QWebChannel=function(transport,callback){callback({objects:{mark:{
  send(){},action(){},ready(){},message:{connect:fn=>listeners.add(fn),disconnect:fn=>listeners.delete(fn)}
 }}})};
 const descriptor=Object.getOwnPropertyDescriptor(HTMLScriptElement.prototype,'src');
 Object.defineProperty(HTMLScriptElement.prototype,'src',{...descriptor,set(value){descriptor.set.call(this,String(value).startsWith('qrc:')?'data:text/javascript,/* explicitly synthetic QWebChannel fixture */':value)}});
 document.addEventListener('DOMContentLoaded',()=>{const label=document.createElement('div');label.textContent='SİMÜLASYON · YAPAY SES SEVİYESİ · GERÇEK MİKROFON / TTS DEĞİL';label.style.cssText='position:fixed;top:0;left:0;right:0;z-index:9999;text-align:center;background:#42320bee;color:#fff1b8;padding:5px;font:11px Arial';document.body.append(label)});
})()"""
async def run(args):
 if urlsplit(args.url).hostname not in {'127.0.0.1','localhost','::1'}:raise ValueError('isolated loopback only')
 out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
 async with async_playwright() as p:
  b=await p.chromium.launch(args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-gpu-compositing'])
  c=await b.new_context(viewport={'width':1366,'height':768},record_video_dir=str(out/'raw'),record_video_size={'width':1366,'height':768},service_workers='block')
  await c.request.post(args.url+'/api/merged/session',headers={'X-MARK-Token':os.environ['GOLGE_UI_QA_TOKEN']})
  r=await c.request.post(args.url+'/api/stage/command',headers={'Origin':args.url},data={'operation':'reset'});assert r.ok
  await c.add_init_script(FIXTURE);page=await c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(args.url+'/frontend/index.html');await page.locator('.core-canvas canvas').wait_for(timeout=15000)
  await page.wait_for_function('!document.querySelector(".power").disabled')
  for state,level in [('LISTENING',0),('LISTENING',.75),('SPEAKING',.35),('SPEAKING',0),('IDLE',0)]:
   await page.evaluate('(e)=>window.__syntheticBridgeEmit(e)',{'kind':'state','state':state,'muted':state=='IDLE','amplitude':level})
   await page.wait_for_function('([s,a])=>{const e=document.querySelector(".core-canvas");return e?.dataset.state===s&&Math.abs(Number(e.dataset.audioLevel)-a)<.001}',arg=[state,level])
   await page.wait_for_timeout(1000)
   if level:await page.screenshot(path=str(out/f'synthetic-{state.lower()}.png'))
  await page.evaluate("window.__syntheticBridgeEmit({kind:'log',role:'user',text:'GÖLGE, Dünya’yı göster.'})")
  await page.locator('.earth-watch-webgl canvas').wait_for(timeout=15000);await page.wait_for_timeout(1600)
  await page.evaluate("window.__syntheticBridgeEmit({kind:'log',role:'user',text:'GÖLGE, CORE’a dön.'})")
  await page.locator('.core-canvas canvas').wait_for(timeout=15000);await page.wait_for_timeout(1700)
  assert not await page.locator('.earth-watch-webgl canvas').count()
  assert not errors,errors
  video=page.video;await page.close();await c.close();await video.save_as(str(out/'synthetic-audio-and-voice-contract.webm'));await b.close()
 result={'status':'PASS','source':'FAKE QWebChannel / injected audio levels; real production UI and real isolated stage API','checks':['listening amplitude including zero','speaking amplitude including zero','return to idle','synthetic transcript Earth and CORE routing'],'physical_microphone':'NOT RUN','real_tts':'NOT RUN','errors':errors}
 (out/'synthetic-audio-contract.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8017');p.add_argument('--output',required=True);asyncio.run(run(p.parse_args()))
