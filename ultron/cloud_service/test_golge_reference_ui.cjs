const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..');
const file=(p)=>fs.readFileSync(path.join(root,p),'utf8');

test('phone has no central orb; chat and composer remain available',()=>{
 const html=file('ultron/cloud_service/static/index.html');
 const minimal=html.indexOf('/static/golge-minimal.css');
 const newSkin=html.indexOf('/static/golge-reference-mobile.css');
 assert.ok(minimal>0 && newSkin>minimal);
 assert.doesNotMatch(html,/class="golge-welcome"/);
 assert.doesNotMatch(html,/class="golge-welcome-orb"/);
 assert.doesNotMatch(html,/id="golgeHeroStatus"/);
 assert.match(html,/<div id="messages"><\/div>/);
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
  '#chatView.active{justify-content:flex-start}',
  ':has(#message:placeholder-shown)',
  '#chatView .composer .row'
 ]) assert.ok(css.includes(expected),'missing layout: '+expected);
 assert.ok(!css.includes('.shell{max-width:760px;height:100dvh'),'must not lock remote panels');
 assert.doesNotMatch(css,/\.golge-welcome-orb|\.golge-orbit|\.golge-welcome\{/);
 // The old HTML theme paints bright red decorative ::after dots by default.
 // Our final stylesheet must explicitly suppress both owner/assistant markers.
 assert.match(css,/#chatView \.msg\.assistant::after,/);
 assert.match(css,/#chatView \.msg\.user::after\{/);
 assert.match(css,/content:none!important;display:none!important/);
 assert.match(css,/#chatView \.msg\.user::before\{/);
 assert.match(css,/border:1px solid #315460!important/);
 assert.match(css,/position:fixed!important;inset:0!important/);
 assert.match(css,/\/static\/golge-night-lake\.webp/);
 assert.ok(fs.existsSync(path.join(root,'ultron/cloud_service/static/golge-night-lake.webp')));

 const sw=file('ultron/cloud_service/static/sw.js');
 assert.match(sw,/ultron-shell-v74/);
 assert.match(sw,/\/static\/golge-reference-mobile\.css/);
 assert.match(sw,/\/static\/golge-night-lake\.webp/);
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
 const transition=file('ultron/frontend/src/dashboard/CoreEarthStage.tsx');
 assert.match(stage,/stage.mode==='core_idle'\|\|stage.mode==='earth_watch'/);
 assert.match(stage,/<CoreEarthStage/);
 assert.match(transition,/<GolgeOrb/);
 assert.match(transition,/<EarthWatch/);
 assert.match(transition,/clearTimeout\(timer\)/);
 for(const mode of ['animation_preview','hologram_lab','world_map']){
  assert.ok(stage.includes("stage.mode==='"+mode+"'"),'existing stage '+mode+' gone');
 }
 assert.match(dash,/className="golge-navigation"/);
 for(const name of ['Sohbet','Geçmiş','Belgeler','Araçlar','Ayarlar']){
  assert.ok(dash.includes('>'+name+'</button>'), 'missing real sidebar action '+name);
 }
 assert.match(dash,/import '\.\/golge-reference\.css'/);
 assert.match(skin,/grid-template-columns:clamp/);
 assert.match(skin,/@media\(max-width:840px\)/);
 assert.match(skin,/prefers-reduced-motion:reduce/);
});


test('iPhone uploads keep normal chat usable and display sent images',()=>{
 const html=file('ultron/cloud_service/static/index.html');
 const sendImage=html.split('async function sendImage(){')[1].split('function toast(')[0];
 const sendPdf=html.split('async function sendPdf(){')[1].split('async function cameraFrameApi(')[0];
 assert.match(sendImage,/showSubmittedPhoto\(userBubble,file\)/);
 assert.match(sendImage,/catch\(e\)\{[\s\S]*?clearPendingImage\(\)/);
 assert.match(sendPdf,/catch\(e\)\{[\s\S]*?clearPendingPdf\(\)/);
 assert.match(html,/id="pdfInput"[^>]*\.txt/);
 assert.match(html,/if\(pendingImage\)\{await sendImage\(\);return\}/);
 assert.match(html,/if\(pendingPdf\)\{await sendPdf\(\);return\}/);
 const backend=file('ultron/cloud_service/app.py');
 assert.match(backend,/def _gemini_text_document_reply/);
 assert.match(backend,/supported_document_required/);
 assert.match(backend,/application\/octet-stream/);
});
