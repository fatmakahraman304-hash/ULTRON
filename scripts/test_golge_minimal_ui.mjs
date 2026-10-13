import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=(path)=>readFileSync(new URL('../'+path,import.meta.url),'utf8');
const html=read('ultron/cloud_service/static/index.html');
const mobile=read('ultron/cloud_service/static/golge-minimal.css');
const sw=read('ultron/cloud_service/static/sw.js');
const dashboard=read('ultron/frontend/src/dashboard/Dashboard.tsx');
const desktop=read('ultron/frontend/src/dashboard/golge-minimal.css');
assert.match(html, /<link rel="stylesheet" href="\/static\/golge-minimal\.css"\s*\/>/);
assert.doesNotMatch(html, /class="golge-welcome"/);
assert.match(html, /golge-reference-mobile\.css/);
assert.doesNotMatch(html, /class="golge-welcome-orb"/);
assert.match(mobile, /#chatView:has\(#messages \.msg\) \.golge-welcome\{display:none\}/);
for(const id of ['app','login','chatView','messages','voiceBtn','sendBtn','plusBtn','attachMenu','longListenPanel','longListenBegin','longListenAnswer','panelMenuToggle','tabs','phoneActionApproval']) {
  assert.ok(html.includes('id="'+id+'"'),'Missing mobile control: '+id);
}
assert.match(sw,/ultron-shell-v71/);
assert.match(sw,/\/static\/golge-reference-mobile\.css/);
assert.match(sw,/\/static\/golge-minimal\.css/);
assert.match(dashboard, /import '\.\/golge-minimal\.css'/);
assert.match(dashboard, /ultron-app voice-first golge-minimal/);
assert.match(dashboard, /<CenterStage stage=\{u\.stage\}/);
assert.match(dashboard, /u\.native\?\.action\('mute'\)/);
assert.match(dashboard, /<Panel title="SOHBET"/);
assert.match(desktop, /@media\(max-width:840px\)/);
assert.match(desktop, /transform:none!important/);
assert.match(desktop, /\.golge-minimal \.modal-shade/);
console.log('GÖLGE UI static contract: PASS (both devices, 16 controls, safe PWA cache)');
