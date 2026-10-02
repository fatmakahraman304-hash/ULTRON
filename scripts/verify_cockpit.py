import json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(root/'cache/playwright')
from integration.launcher import Services
from playwright.sync_api import sync_playwright
out=root/'logs/design';out.mkdir(parents=True,exist_ok=True)
with Services() as service:
    service.start()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(service.bridge.url+'/merged/dashboard#'+service.bridge.token)
        page.wait_for_url('**/frontend/index.html')
        page.get_by_text('Yerel bağlantı',exact=True).wait_for(timeout=15000)
        page.get_by_role('button',name='Sistemi kontrol et',exact=True).click()
        page.get_by_text('Sistem raporu',exact=False).first.wait_for()
        page.locator('input[type=file]').set_input_files({'name':'proje-notlari.txt','mimeType':'text/plain','buffer':'ULTRON arayüzü: sistem paneli, enerji çekirdeği ve konuşma alanı.'.encode()})
        page.get_by_title('proje-notlari.txt',exact=True).wait_for(timeout=10000)
        page.wait_for_timeout(500)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(out/'desktop.png'))
        page.get_by_role('button',name='Ayarlar',exact=True).click()
        page.get_by_role('dialog',name='Ayarlar').wait_for()
        page.screenshot(path=str(out/'settings.png'))
        page.get_by_role('switch',name='Robot avatar').click()
        page.get_by_role('button',name='Paneli kapat').click()
        page.screenshot(path=str(out/'avatar.png'))
        page.get_by_role('button',name='Kişiselleştir',exact=True).click()
        page.get_by_label('Asistan adı',exact=True).fill('ULTRON')
        page.get_by_role('button',name='#00d7e8 vurgu rengi').click()
        assert page.locator('.cockpit').evaluate("e=>getComputedStyle(e).getPropertyValue('--accent').trim()")=='#00d7e8'
        page.get_by_role('button',name='#ff183c vurgu rengi').click()
        page.screenshot(path=str(out/'customize.png'))
        page.get_by_role('button',name='Paneli kapat').click()
        page.reload();page.get_by_text('Yerel bağlantı',exact=True).wait_for()
        assert page.locator('.core-avatar').count()==1
        page.get_by_role('button',name='Ayarlar',exact=True).click()
        page.get_by_role('switch',name='Robot avatar').click()
        page.get_by_role('button',name='Paneli kapat').click()
        page.get_by_role('button',name='Not oluştur',exact=True).click()
        page.get_by_label('Notunuz').fill('cockpit-ui-test-temporary')
        page.get_by_role('button',name='Notu kaydet',exact=True).click()
        page.get_by_text('Not kalıcı belleğe kaydedildi.',exact=True).wait_for()
        rows=service.bridge.request('/api/memory/v16')['rows']
        note=next(row for row in rows if row['content']=='cockpit-ui-test-temporary')
        service.bridge.request('/api/memory/v16/delete',{'id':note['id']})
        page.set_viewport_size({'width':430,'height':932})
        page.goto(service.bridge.url+'/frontend-mobile/index.html')
        page.get_by_text('Yerel bağlantı',exact=True).wait_for()
        page.get_by_role('button',name='Sistem durumunu göster',exact=False).click()
        page.screenshot(path=str(out/'mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.get_by_role('button',name='Ayarlar',exact=True).click()
        page.get_by_role('switch',name='Robot avatar').click()
        page.get_by_role('button',name='Paneli kapat').click()
        page.screenshot(path=str(out/'mobile-avatar.png'),full_page=True)
        for width in (375,820,1280):
            page.set_viewport_size({'width':width,'height':900})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
        assert not errors,errors
        (out/'checks.json').write_text(json.dumps({'status':'PASS','javascript_errors':errors,'checks':['desktop','mobile','settings','customization','avatar','preference persistence','file extraction','memory roundtrip','responsive widths']},indent=2),encoding='utf-8')
        browser.close()
        print('VISUAL_AND_INTERACTION_PASS',flush=True)
