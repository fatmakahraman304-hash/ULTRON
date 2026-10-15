"""Real, isolated loopback backend/WebGL acceptance; never touches production.

Model inference and provider availability are reported independently. Optional
synthetic native audio contract is conspicuously labelled, never hardware proof.
"""
import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

async def run(args):
    origin=args.url.rstrip('/')
    if urlsplit(origin).hostname not in {'localhost','127.0.0.1','::1'}:
        raise ValueError('Only an isolated loopback QA backend is allowed')
    token=os.environ['GOLGE_UI_QA_TOKEN']
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    report={'environment':'Real isolated backend; Chromium SwiftShader WebGL / CPU compositor; no physical iPhone or Windows GPU','checks':{},'providers':{},'errors':[],'microphone':'NOT RUN','tts':'NOT RUN','visual_acceptance':'REVIEW_REQUIRED','video_segments':[]}
    async with async_playwright() as p:
        browser=await p.chromium.launch(args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-gpu-compositing','--disable-dev-shm-usage'])
        context=await browser.new_context(viewport={'width':1366,'height':768},service_workers='block',record_video_dir=str(out/'raw'),record_video_size={'width':1366,'height':768})
        assert (await context.request.get(origin+'/api/system')).status==401
        assert (await context.request.post(origin+'/api/merged/session',headers={'X-MARK-Token':token})).ok
        denied=await context.request.post(origin+'/api/stage/command',headers={'Origin':'https://invalid.example'},data={'operation':'reset'})
        assert denied.status==401
        for path in ['/api/world/layers','/api/world/search?q=Lefko%C5%9Fa']:
            other=await browser.new_context()
            assert (await other.request.get(origin+path)).status==401
            await other.close()
        report['checks']['auth_origin_world_route_boundary']='PASS'
        system=await (await context.request.get(origin+'/api/system')).json()
        health=await (await context.request.get(origin+'/api/merged/health')).json()
        report['backend']={'platform':system.get('platform'),'cpu_percent':system.get('cpu',{}).get('percent'),'ram_total_gb':system.get('ram',{}).get('total_gb'),'cloud_configured':bool(health.get('cloud',{}).get('enabled'))}
        baseline=await context.request.post(origin+'/api/stage/command',headers={'Origin':origin},data={'operation':'earth_focus','place':'GLOBAL','lat':20,'lon':0,'camera_distance':7.4})
        assert baseline.ok,'Isolated QA baseline failed'
        reset=await context.request.post(origin+'/api/stage/command',headers={'Origin':origin},data={'operation':'reset'})
        assert reset.ok,'Authorized QA reset failed'
        page=await context.new_page();websockets=[];tiles=[]
        page.on('pageerror',lambda e:report['errors'].append(str(e)))
        page.on('console',lambda m:report['errors'].append(m.text) if 'Shader Error' in m.text else None)
        page.on('websocket',lambda ws:websockets.append(ws.url))
        page.on('response',lambda r:tiles.append(r.status) if 'tile.openstreetmap.org' in r.url else None)
        await page.goto(origin+'/frontend/index.html',wait_until='domcontentloaded')
        await page.locator('.core-canvas canvas').wait_for(timeout=15000)
        await page.locator('.golge-connection.connected').wait_for(timeout=15000)
        begin=time.monotonic()
        async def segment(name):report['video_segments'].append({'name':name,'seconds_after_page_ready':round(time.monotonic()-begin,2)})
        async def command(text,wait=400):
            field=page.get_by_role('textbox',name='Kontrol merkezi komutu' if await page.locator('.control-center-view').count() else 'Mesaj',exact=True)
            await field.fill(text);await field.press('Enter');await page.wait_for_timeout(wait)
        async def screenshot(name):
            assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            await page.screenshot(path=str(out/name))
        await segment('CORE idle');await page.wait_for_timeout(1500)
        await screenshot('core-desktop1366.png')
        await page.set_viewport_size({'width':1920,'height':1080});await page.wait_for_timeout(800);await screenshot('core-desktop1920.png')
        await page.set_viewport_size({'width':1366,'height':768});await page.wait_for_timeout(500)
        await page.evaluate('''() => {window.__earthTransitions=[];const observer=new MutationObserver(()=>{const e=document.querySelector('.core-earth-workspace');if(e)window.__earthTransitions.push({phase:e.dataset.transition,canvases:e.querySelectorAll('canvas').length})});observer.observe(document.querySelector('.reactor-panel'),{subtree:true,childList:true,attributes:true,attributeFilter:['data-transition']})}''')
        await segment('CORE to Earth')
        await command('GÖLGE, Dünya’yı göster.',120)
        await page.locator('.earth-watch-webgl canvas').wait_for(timeout=15000)
        await page.locator('.core-earth-workspace[data-transition="stable"]').wait_for(timeout=10000)
        transitions=await page.evaluate('window.__earthTransitions')
        assert any(e['phase']=='enter' and e['canvases']==2 for e in transitions),transitions
        assert await page.locator('canvas').count()==1
        assert await page.locator('.earth-watch-webgl').get_attribute('data-quality')
        report['checks']['real_gpu_transition_and_outgoing_disposal']='PASS'
        profile=await page.locator('.earth-watch-webgl').evaluate("e=>({renderer:e.dataset.renderer,quality:e.dataset.quality,geometries:e.dataset.geometries,textures:e.dataset.textures})")
        intervals=await page.evaluate("""async()=>{const times=[];let last=performance.now();for(let i=0;i<24;i++){await new Promise(requestAnimationFrame);const now=performance.now();times.push(now-last);last=now}return times.sort((a,b)=>a-b)}""")
        report['headless_render_measurement']={**profile,'raf_p50_ms':round(intervals[12],1),'raf_p95_ms':round(intervals[22],1),'target_windows_fps':'NOT RUN'}
        await screenshot('earth-desktop1366.png')
        await page.set_viewport_size({'width':1920,'height':1080});await page.wait_for_timeout(800);await screenshot('earth-desktop1920.png')
        await page.set_viewport_size({'width':1366,'height':768})
        canvas=page.locator('.earth-watch-webgl canvas');box=await canvas.bounding_box();assert box
        await segment('Mouse rotate and wheel zoom')
        await page.mouse.move(box['x']+box['width']*.55,box['y']+box['height']*.5);await page.mouse.down();await page.mouse.move(box['x']+box['width']*.7,box['y']+box['height']*.56,steps=12);await page.mouse.up()
        before=float(await page.locator('.earth-watch-webgl').get_attribute('data-camera-distance'))
        await page.mouse.wheel(0,-100);await page.wait_for_timeout(750)
        after=float(await page.locator('.earth-watch-webgl').get_attribute('data-camera-distance'));assert after<before
        report['checks']['orbit_and_wheel_zoom']='PASS'
        for query in ['Kıbrıs','Lefkoşa']:
            await segment('Geocode and focus '+query)
            response=await context.request.get(origin+'/api/world/search',params={'q':query},timeout=20000)
            payload=await response.json()
            hits=payload.get('results',[])
            report['providers'][query]={'http':response.status,'source':payload.get('source'),'results':hits,'status':'PASS' if response.ok and hits else 'BLOCKED'}
            if not response.ok or not hits:continue
            await command(f'GÖLGE, {query} konumunu göster.',800)
            if len(hits)>1:
                await page.locator('.earth-search-results button').first.wait_for(timeout=14000)
                await page.locator('.earth-search-results button').first.click()
            if query=='Kıbrıs':
                await page.wait_for_function('(lat)=>Math.abs(Number(document.querySelector(".earth-watch-webgl")?.dataset.focusLat)-lat)<.0001',arg=hits[0]['lat'],timeout=10000)
                await page.wait_for_function('Number(document.querySelector(".earth-watch-webgl")?.dataset.focusFacing)>.98',timeout=5000)
                facing=float(await page.locator('.earth-watch-webgl').get_attribute('data-focus-facing'))
                assert facing>.98,f'Camera points at wrong region: {facing}'
                await screenshot('cyprus-focus.png')
                report['checks']['cyprus_true_coordinates_camera_direction']='PASS'
            else:
                await page.locator('.earth-raster-map').wait_for(timeout=15000)
                await page.wait_for_timeout(2500)
                await screenshot('nicosia-street-map.png')
                report['checks']['city_map_is_real_tiles_not_globe_upscale']='PASS' if any(s==200 for s in tiles) else 'BLOCKED: tile provider unavailable'
        await segment('Satellite unavailable boundary')
        layer_before=(await (await context.request.get(origin+'/api/stage')).json())['earth'].get('layer')
        await command('GÖLGE, uydu moduna geç.',500)
        layers=await (await context.request.get(origin+'/api/world/layers')).json()
        if not layers['SATELLITE']['available']:
            layer_after=(await (await context.request.get(origin+'/api/stage')).json())['earth'].get('layer')
            assert layer_before==layer_after
            report['checks']['unlicensed_satellite_preserves_current_view']='PASS'
            report['providers']['SATELLITE']='BLOCKED: no licensed imagery configuration'
        await command('GÖLGE, 3D görünümü aç.',700)
        await page.locator('.earth-watch-webgl canvas').wait_for(timeout=15000)
        await segment('Day night terminator');await command('GÖLGE, Dünya’nın gece tarafını göster.',1600);await screenshot('earth-night.png')
        await segment('Normal chat to control center')
        count=await page.locator('.message').count()
        await command('GÖLGE, kontrol merkezini aç.',800)
        await page.locator('.cc-map-card canvas').wait_for(timeout=15000)
        await page.wait_for_timeout(700);await screenshot('control-desktop1366.png')
        await page.set_viewport_size({'width':1920,'height':1080});await page.wait_for_timeout(700);await screenshot('control-desktop1920.png')
        await page.set_viewport_size({'width':1366,'height':768})
        await command('GÖLGE, normal moda dön.',600)
        assert await page.locator('.message').count()>=count
        assert len(websockets)==1,websockets
        report['checks']['shared_earth_chat_and_single_websocket']='PASS'
        await segment('Earth to CORE')
        await command('GÖLGE, CORE’a dön.',1700)
        await page.locator('.core-canvas canvas').wait_for(timeout=15000)
        assert await page.locator('.earth-watch-webgl canvas').count()==0
        for _ in range(3):
            await command('Dünyayı aç',100)
            await page.wait_for_function('document.querySelector(".show-earth[data-transition=stable]")&&document.querySelectorAll(".earth-watch-webgl canvas").length===1&&document.querySelectorAll("canvas").length===1',timeout=12000)
            await command('CORE’a dön',100)
            await page.wait_for_function('document.querySelector(".show-core[data-transition=stable]")&&document.querySelectorAll(".core-canvas canvas").length===1&&document.querySelectorAll("canvas").length===1',timeout=12000)
            assert await page.locator('canvas').count()==1,'Outgoing scene was not removed'
        report['checks']['repeat_scene_transition_cleanup']='PASS'
        # Endpoint is genuine; only one request is made, through the actual UI.
        async with page.expect_response(lambda r:r.url.endswith('/api/merged/invoke'),timeout=20000) as pending:
            await command('Merhaba GÖLGE, kısa bir Türkçe yanıt verir misin?',100)
        response=await pending.value;reply=await response.json()
        report['real_model']={'status':'PASS' if reply.get('ok') and reply.get('text') else 'BLOCKED' if reply.get('status')=='UNAVAILABLE' else 'FAIL','response':{k:reply.get(k) for k in ('ok','status','source','model','error') if k in reply}}
        await screenshot('actual-provider-result.png')
        await page.set_viewport_size({'width':390,'height':844});await page.wait_for_timeout(900)
        assert await page.locator('canvas').count()==0
        assert not await page.locator('.control-center-view').count()
        before=await page.locator('.viewport').evaluate("e=>getComputedStyle(e,'::before').backgroundImage")
        assert 'golge-night-lake' in before
        await page.locator('.messages').evaluate('e=>e.scrollTop=0');await page.wait_for_timeout(100)
        await screenshot('mobile390.png')
        await page.locator('.messages').evaluate('e=>e.scrollTop=e.scrollHeight')
        assert await page.evaluate('window.scrollY')==0
        await page.set_viewport_size({'width':390,'height':550});await page.wait_for_timeout(300)
        composer=await page.locator('.composer').bounding_box();assert composer and composer['y']+composer['height']<=550
        report['checks']['mobile_fixed_photo_scroll_and_keyboard_height_simulation']='PASS'
        report['checks']['shader_react_errors']='PASS' if not report['errors'] else 'FAIL'
        assert not report['errors'],report['errors']
        report['tile_responses']=tiles
        video=page.video;await page.close();await context.close()
        if video:await video.save_as(str(out/'earth-workspace-live.webm'))
        await browser.close()
    (out/'earth-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'checks':report['checks'],'providers':{k:v.get('status') if isinstance(v,dict) else v for k,v in report['providers'].items()},'real_model':report['real_model']['status'],'errors':report['errors']},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8017');parser.add_argument('--output',required=True)
    asyncio.run(run(parser.parse_args()))
