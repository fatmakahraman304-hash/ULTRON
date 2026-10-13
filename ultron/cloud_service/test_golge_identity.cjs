const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=__dirname;
function read(name){return fs.readFileSync(path.join(root,name),'utf8');}
test('GÖLGE mobile app and assistant chat identity, not legacy screen brand',()=>{
 const html=read('static/index.html');
 for(const text of [
   '<title>GÖLGE Mobile</title>',
   'name="apple-mobile-web-app-title" content="GÖLGE"',
   'class="splash-logo">GÖLGE</div>',
   '<b>GÖLGE</b>',
   'content:"GÖLGE"',
   'GÖLGE • KENDİNİ GELİŞTİR',
   '10 GÖLGE YETENEĞİ',
   '/static/golge-icon.svg',
 ])assert.ok(html.includes(text),'Missing live branding: '+text);
 for(const text of ['<title>ULTRON','class="splash-logo">ULTRON','content:"ULTRON"'])
   assert.ok(!html.includes(text),'Old visible name: '+text);
 const script=html.match(/<script>([\s\S]*?)<\/script>/);
 assert.ok(script,'missing inline script');
 new vm.Script(script[1]);
});
test('manifest, foreground icon and cache use new GÖLGE app name',()=>{
 const m=JSON.parse(read('static/manifest.webmanifest'));
 assert.equal(m.name,'GÖLGE Mobile');
 assert.equal(m.short_name,'GÖLGE');
 assert.ok(m.icons?.some(i=>i.src==='/static/golge-icon.svg'));
 const icon=read('static/golge-icon.svg');
 assert.match(icon,/>GÖLGE<\/text>/);
 const sw=read('static/sw.js');
 assert.match(sw,/ultron-shell-v65/);
 assert.match(sw,/\/static\/golge-icon.svg/);
 assert.doesNotMatch(sw,/\/static\/ultron-icon.svg/);
});
test('GÖLGE voice commands are accepted; technical legacy aliases remain functional',()=>{
 const listen=require('./static/long-listen.js');
 assert.equal(listen.isStart('GÖLGE, bir saat dinle beni'),true);
 assert.equal(listen.isStart('Gölge bir saat dinle'),true);
 assert.equal(listen.isStart('Golge 1 saat dinle'),true);
 assert.equal(listen.isAnswer('GÖLGE cevap ver'),true);
 assert.equal(listen.isStart('ULTRON bir saat dinle'),true);
 assert.equal(listen.isAnswer('ULTRON cevap ver'),true);
 assert.equal(listen.isStart('GÖLGE bütün dosyaları sil'),false);
 const probe=require('./static/local-listening-probe.js');
 assert.equal(probe.isRequest('GÖLGE, Qwen bağlantısını test et'),true);
 assert.equal(probe.isRequest('Gölge, Qwen bağlantısını test eder misin?'),true);
});
test('GÖLGE safe phone shortcut display keeps unchanged underlying transport keys',()=>{
 const policy=require('./static/mobile-action-guard.js');
 // The old bridge 'source' field must remain a stable protocol identifier.
 const source=read('static/mobile-action-guard.js');
 assert.match(source,/BRIDGE_NAME = 'GÖLGE Bridge'/);
 assert.match(source,/raw\.source !== 'ultron'/);
 const html=read('static/index.html');
 assert.match(html,/GÖLGE Bridge/);
 assert.match(html,/Qwen bağlantısını test et/);
});
test('cloud model identifies itself only as GÖLGE while legacy auth survives',()=>{
 const app=fs.readFileSync(path.join(root,'../app.py'),'utf8');
 const persona=fs.readFileSync(path.join(root,'../conversation_persona.py'),'utf8');
 assert.match(persona,/You are GÖLGE/);
 assert.match(persona,/Use only the name GÖLGE/);
 assert.match(app,/You are ONE GÖLGE/);
 assert.match(app,/X-ULTRON-DEVICE/);
 assert.match(app,/ULTRON_SESSION_SECRET/);
});
