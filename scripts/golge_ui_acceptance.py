"""Capture/verify a running, isolated GÖLGE backend with real authentication.

Never starts a provider, changes a production DB, or claims hardware/model quality.
Only loopback backends are accepted. GOLGE_UI_QA_TOKEN must be a test session token.
--demo intercepts the model endpoint in the browser only, and labels every demo.
"""
import argparse
import asyncio
import json
import io
import os
import shutil
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
from PIL import Image

async def run(args):
    origin=args.url.rstrip('/')
    if urlsplit(origin).hostname not in {'localhost','127.0.0.1','::1'}:
        raise ValueError('Use an isolated loopback backend, never a production user session.')
    token=os.environ.get('GOLGE_UI_QA_TOKEN')
    if not token:raise ValueError('GOLGE_UI_QA_TOKEN is required; no unauthenticated fallback.')
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    report={'environment':'Chromium WebGL/SwiftShader with CPU compositor (headless resize capture workaround); isolated real backend, not physical Windows/iPhone','checks':{},'errors':[],'real_model':'NOT RUN','microphone':'NOT RUN','tts_sync':'NOT RUN','visual_acceptance':'REVIEW_REQUIRED; human comparison with supplied reference'}
    async with async_playwright() as p:
        browser=await p.chromium.launch(args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage','--disable-gpu-compositing'])
        context=await browser.new_context(viewport={'width':1920,'height':1080},service_workers='block')
        unauth=await context.request.get(origin+'/api/system')
        assert unauth.status==401,'QA backend must enforce the existing session boundary'
        auth=await context.request.post(origin+'/api/merged/session',headers={'X-MARK-Token':token})
        assert auth.ok,'test session authentication failed'
        denied=await context.request.post(origin+'/api/merged/invoke',headers={'Origin':'https://invalid.example'},data={'text':'test','mode':'general'})
        assert denied.status==401,'cross-origin cookie writes must be denied'
        report['checks']['real_auth_and_origin_boundary']='PASS'
        system=await (await context.request.get(origin+'/api/system')).json()
        health=await (await context.request.get(origin+'/api/merged/health')).json()
        assert isinstance(system.get('cpu',{}).get('percent'),(int,float))
        assert isinstance(system.get('ram',{}).get('total_gb'),(int,float))
        report['telemetry']={k:system.get(k) for k in ('platform','cpu','ram','gpu')}
        report['cloud_configured']=bool(health.get('cloud',{}).get('enabled'))
        report['checks']['real_backend_telemetry']='PASS'
        page=await context.new_page();websockets=[]
        page.on('websocket',lambda ws:websockets.append(ws.url))
        page.on('pageerror',lambda error:report['errors'].append(str(error)))
        page.on('console',lambda message:report['errors'].append(message.text) if 'Shader Error' in message.text else None)
        async def capture(filename):
            await page.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            data=await page.screenshot(path=str(out/filename))
            width=(page.viewport_size or {}).get('width',0)
            if width>840:
                image=Image.open(io.BytesIO(data)).convert('RGB')
                region=image.crop((25,25,width-25,75))
                pixels=list(region.get_flattened_data()) if hasattr(region,'get_flattened_data') else list(region.getdata())
                black=sum(max(pixel)<2 for pixel in pixels)/len(pixels)
                assert black<.7 and sum(max(pixel)>110 for pixel in pixels)>100,f'Corrupt/incomplete desktop compositor capture: {filename}'

        await page.goto(origin+'/frontend/index.html',wait_until='domcontentloaded')
        await page.locator('.golge-connection.connected').wait_for(timeout=15000)
        await page.locator('.core-canvas canvas').wait_for(timeout=15000)
        await page.wait_for_timeout(600)
        await capture('live-empty-desktop1920.png')
        for width,height in [(1920,1080),(1366,768)]:
            await page.set_viewport_size({'width':width,'height':height});await page.wait_for_timeout(1000)
            assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            await capture(f'live-empty-desktop{width}.png')
        report['checks']['desktop_empty_layouts']='PASS'
        await page.set_viewport_size({'width':1920,'height':1080})
        field=page.get_by_role('textbox',name='Mesaj',exact=True)
        await field.fill('Merhaba GÖLGE, kısa bir Türkçe cevap verir misin?')
        async with page.expect_response(lambda r:r.url.endswith('/api/merged/invoke')) as pending:
            await field.press('Enter')
        response=await pending.value;reply=await response.json()
        await page.locator('.message.assistant').wait_for(timeout=15000)
        report['real_model']='PASS' if reply.get('ok') and str(reply.get('text','')).strip() else 'BLOCKED' if reply.get('status')=='UNAVAILABLE' else 'FAIL'
        report['real_chat_response']={k:reply.get(k) for k in ('ok','status','error','source','model') if k in reply}
        await capture('live-chat-provider-result.png')
        if args.demo:
            replies=iter([
                'Merhaba! Bir fikir üzerinde çalışabilir, bir konuyu inceleyebilir ya da gününü birlikte planlayabiliriz.',
                'Önce en önemli işi seçelim. Onu bitirebileceğin bir zaman aralığı ayıralım; kalan işleri sonra sıralarız.',
                'Anladım. Projenin mavi ve koyu lacivert renklerini temel alalım. Kontrol merkezini açarak çalışma alanına da geçebilirsin.',
            ])
            async def fake_model(route):
                await route.fulfill(json={'ok':True,'text':next(replies,'Bu, uzun mesaj ve kaydırma yerleşimini sınayan sentetik bir yanıttır.\n\n'+'GÖLGE görsel kabul senaryosu. '*150),'source':'explicit_visual_demo'})
            await page.route('**/api/merged/invoke',fake_model)
            await page.get_by_role('button',name='Temizle',exact=True).click()
            await page.evaluate("""() => {const b=document.createElement('div');b.id='qa-demo-label';b.textContent='GÖRSEL DEMO · SENTETİK SOHBET';Object.assign(b.style,{position:'fixed',top:'0',left:'50%',transform:'translateX(-50%)',zIndex:'1000',background:'#171308ee',border:'1px solid #796d37',borderRadius:'0 0 6px 6px',padding:'3px 10px',font:'600 9px Arial,sans-serif',letterSpacing:'.08em',color:'#e6dca7',whiteSpace:'nowrap'});document.body.appendChild(b)}""")
            for i,text in enumerate(['Merhaba GÖLGE, bugün neler yapabiliriz?','Önce günümü planlamak istiyorum.','Tamam, sonra üzerinde çalıştığımız projeye dönelim.']):
                await field.fill(text);await field.press('Enter');await page.wait_for_function('(n)=>document.querySelectorAll(".message.assistant").length>=n',arg=i+1)
            for width,height in [(1920,1080),(1366,768)]:
                await page.set_viewport_size({'width':width,'height':height});await page.wait_for_timeout(1000)
                await capture(f'demo-chat-desktop{width}.png')
            report['checks']['filled_chat_demo']='PASS (synthetic model responses, labeled)'
        await page.get_by_role('button',name='Kontrol merkezini aç',exact=True).click()
        await page.locator('.cc-map-card canvas').wait_for(timeout=15000)
        await page.wait_for_function('!document.querySelector(".earth-render-status")',timeout=15000)
        for width,height in [(1920,1080),(1366,768)]:
            await page.set_viewport_size({'width':width,'height':height});await page.wait_for_timeout(1000)
            await capture(f'live-control-desktop{width}.png')
            assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            last=await page.locator('.cc-action-grid button').last.bounding_box();column=await page.locator('.cc-right').bounding_box()
            assert last and column and last['y']+last['height']<=column['y']+column['height']+1,'quick actions clipped by the column'
        focus=page.get_by_role('textbox',name='Kontrol merkezi komutu',exact=True)
        await focus.fill("Kıbrıs'a odaklan");await focus.press('Enter')
        await page.wait_for_function('document.querySelector(".earth-watch-brand").textContent.includes("KIBRIS")')
        await page.wait_for_timeout(1000)
        await capture('live-control-cyprus.png')
        await page.locator('.cc-map-card canvas').hover();await page.mouse.wheel(0,-160);await page.wait_for_timeout(250)
        report['checks']['globe_focus_and_wheel']='PASS'
        await focus.fill('GÖLGE, normal moda dön.');await focus.press('Enter')
        await page.locator('.core-canvas canvas').wait_for(timeout=10000)
        assert await page.locator('.message.assistant').count()>0,'chat was lost during workspace transition'
        assert len(websockets)==1,'view transitions reopened/duplicated the real WebSocket'
        report['checks']['workspace_state_and_single_websocket']='PASS'
        for i in range(2):
            await page.get_by_role('button',name='Kontrol merkezini aç',exact=True).click();await page.locator('.cc-map-card canvas').wait_for()
            await page.get_by_role('button',name='Normal sohbete dön',exact=True).first.click();await page.locator('.core-canvas canvas').wait_for()
            assert await page.locator('canvas').count()==1
        report['checks']['canvas_mount_cleanup_cycles']='PASS (DOM and reviewed GPU disposal, not physical GPU memory measurement)'
        await page.set_viewport_size({'width':390,'height':844});await page.wait_for_timeout(1000)
        assert await page.locator('.reactor-panel').count()==0 and await page.locator('.control-center-view').count()==0
        bg=await page.evaluate('getComputedStyle(document.querySelector(".viewport"),"::before").backgroundImage')
        assert 'golge-night-lake.webp' in bg
        await capture('demo-mobile390.png' if args.demo else 'live-mobile390.png')
        if args.demo:
            await page.get_by_role('textbox',name='Mesaj',exact=True).fill('Uzun konuşma yerleşim testi')
            await page.get_by_role('textbox',name='Mesaj',exact=True).press('Enter');await page.wait_for_timeout(300)
            scroller=await page.locator('.messages').evaluate('(el)=>({range:el.scrollHeight-el.clientHeight,top:el.scrollTop})')
            assert scroller['range']>0
        else:
            report['long_chat_fixture']='NOT RUN; use --demo for a labeled, synthetic long reply'
        wallpaper=await page.evaluate('({position:getComputedStyle(document.querySelector(".viewport"),"::before").position,y:scrollY})')
        assert wallpaper['position']=='fixed' and wallpaper['y']==0
        await page.set_viewport_size({'width':390,'height':560});await page.wait_for_timeout(200)
        composer=await page.locator('.composer').bounding_box();assert composer and composer['y']+composer['height']<=560
        report['checks']['mobile_photo_fixed_scroll_and_reduced_viewport']='PASS (keyboard-height simulation, not iPhone keyboard)'
        assert not report['errors'],report['errors']
        report['checks']['shader_and_react_errors']='PASS'
        await context.close()
        if args.record:
            clip=await browser.new_context(viewport={'width':1366,'height':768},record_video_dir=str(out/'raw-video'),record_video_size={'width':1280,'height':720})
            await clip.request.post(origin+'/api/merged/session',headers={'X-MARK-Token':token})
            live=await clip.new_page();await live.goto(origin+'/frontend/index.html')
            await live.locator('.core-canvas canvas').wait_for(timeout=15000)
            await live.wait_for_timeout(6000)
            video=live.video;await clip.close()
            shutil.copyfile(await video.path(),out/'core-idle-live.webm')
            report['recording']='Actual idle WebGL with real backend; no microphone or TTS synchronization claim'
        await browser.close()
    (out/'acceptance-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    parser.add_argument('--output',default='/tmp/golge-ui-acceptance')
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--record',action='store_true')
    asyncio.run(run(parser.parse_args()))
