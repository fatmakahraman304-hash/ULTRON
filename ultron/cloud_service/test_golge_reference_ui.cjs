const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..');
const file=(p)=>fs.readFileSync(path.join(root,p),'utf8');

test('mobile uses screenshot cyan orb and always-available chat composer',()=>{
 const html=file('ultron/cloud_service/static/index.html');
 const minimal=html.indexOf('/static/golge-minimal.css');
 const newSkin=html.indexOf('/static/golge-reference-mobile.css');
 assert.ok(minimal>0 && newSkin>minimal);
 assert.match(html,/class="golge-welcome-orb"/);
 assert.match(html,/class="golge-orbit second"/);
 assert.match(html,/Sadece söyle\.<br><span id="golgeHeroStatus">GÖLGE hazır\.<\/span>/);
 assert.match(html,/hero\.textContent=voiceListening\?'GÖLGE seni dinliyor\.'\:'GÖLGE hazır\.'/);
 for(const id of ['voiceBtn','plusBtn','message','sendBtn','panelMenuToggle','longListenPanel','attachMenu','cameraPanel']){
  assert.ok(html.includes('id="'+id+'"'), 'missing working control: '+id);
 }
 assert.match(html,/list\.scrollTo\(\{top:list\.scrollHeight/);
 const fn=html.match(/function scrollChatToBottom\(smooth=false\)\{([\s\S]*?)\n\}/);
 assert.ok(fn,'chat scroll handler missing');
 assert.doesNotMatch(fn[1],/window\.scrollTo/);
});

test('mobile layout separates scrollable messages and fixed composer without hiding other views',()=>{
 const css=file('ultron/cloud_service/static/golge-reference-mobile.css');
 for(const expected of [
  '.shell:has(#chatView.active)',
  '#chatView.active{display:flex',
  '#chatView #messages{flex:1',
  'overflow-y:auto!important',
  '#chatView .composer',
  '#chatView .golge-welcome-orb',
  ':has(#message:placeholder-shown)',
  'prefers-reduced-motion:reduce'
 ]) assert.ok(css.includes(expected),'missing layout: '+expected);
 assert.ok(!css.includes('.shell{max-width:760px;height:100dvh'),'must not lock remote panels');
 const sw=file('ultron/cloud_service/static/sw.js');
 assert.match(sw,/ultron-shell-v68/);
 assert.match(sw,/\/static\/golge-reference-mobile\.css/);
});

test('desktop procedural 3D remains bounded and other feature stages remain functional',()=>{
 const src=file('ultron/frontend/src/dashboard/GolgeOrb.tsx');
 const stage=file('ultron/frontend/src/dashboard/CenterStage.tsx');
 const dash=file('ultron/frontend/src/dashboard/Dashboard.tsx');
 const skin=file('ultron/frontend/src/dashboard/golge-reference.css');
 assert.match(src,/new THREE\.WebGLRenderer/);
 assert.match(src,/TorusGeometry/);
 assert.match(src,/ResizeObserver/);
 assert.match(src,/cancelAnimationFrame\(frame\)/);
 assert.match(src,/renderer\.dispose\(\)/);
 assert.match(src,/orb-css-only/);
 assert.match(stage,/mode==='core_idle'&&<GolgeOrb/);
 for(const mode of ['animation_preview','hologram_lab','world_map']){
  assert.ok(stage.includes("stage.mode==='"+mode+"'"),'existing stage '+mode+' gone');
 }
 assert.match(dash,/className="golge-navigation"/);
 for(const name of ['Sohbet','Bugün','Düşün','Araştır','Yarat','Hatırla']){
  assert.ok(dash.includes('>'+name+'</button>'), 'missing real sidebar action '+name);
 }
 assert.match(dash,/import '\.\/golge-reference\.css'/);
 assert.match(skin,/grid-template-columns:120px/);
 assert.match(skin,/@media\(max-width:840px\)/);
 assert.match(skin,/prefers-reduced-motion:reduce/);
});
