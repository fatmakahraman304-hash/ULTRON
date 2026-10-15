import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from '../ultron/frontend/node_modules/typescript/lib/typescript.js';
const source=fs.readFileSync('ultron/frontend/src/spatial/design.ts','utf8');
const js=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText;
const {validateDesign}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
const good={name:'Masa',parts:[{name:'Tabla',shape:'box',size:[3,.2,2],position:[0,1,0],rotation:[0,0,0]}]};
assert.deepEqual(validateDesign(JSON.stringify(good)),good);
for(const bad of [null,{},'```js\nalert(1)\n```',{...good,code:'alert(1)'},{...good,parts:Array(25).fill(good.parts[0])},...[
 {shape:'script'},{size:[Infinity,1,1]},{size:[0,1,1]},{position:[true,0,0]},{position:[7,0,0]},{rotation:[0,0,9]},{url:'http://localhost/private'}
].map(p=>({...good,parts:[{...good.parts[0],...p}]}))])assert.throws(()=>validateDesign(bad));
console.log('Data-only scene design validation passed');
