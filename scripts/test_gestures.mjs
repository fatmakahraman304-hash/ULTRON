import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from '../ultron/frontend/node_modules/typescript/lib/typescript.js';
const file=new URL('../ultron/frontend/src/hologram/gestures.ts',import.meta.url);
const js=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText;
const {GestureInterpreter}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
function hand(x=.3,pinch=false,scale=1){const p=Array.from({length:21},()=>({x,y:.5}));p[0]={x,y:.8};p[9]={x,y:.5};p[8]={x,y:.3};p[4]={x:x+(pinch?.04:.25),y:.3};return p.map(v=>({x:x+(v.x-x)*scale,y:.5+(v.y-.5)*scale}));}
const g=new GestureInterpreter();
assert.equal(g.read([]).kind,'idle');assert.equal(g.read([hand()]).kind,'rotate');
assert.equal(g.read([hand(.3,true)]).kind,'grab');
assert.equal(g.read([hand(.3,true,.5)]).kind,'grab','pinch must be invariant to hand distance');
assert.equal(g.read([hand(.3,true),hand(.7,true)]).kind,'spread');
assert.equal(g.read([hand(.3),hand(.7)]).kind,'zoom');
assert.equal(g.read([hand().slice(0,4)]).kind,'idle','incomplete hands cannot move objects');
assert.equal(g.read([hand(.3,true)]).x,.7,'cursor mirrors preview');
g.reset();assert.equal(g.read([]).kind,'idle');
console.log('GESTURE_TEST_PASS (8 assertions)');
