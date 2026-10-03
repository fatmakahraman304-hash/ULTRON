import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from '../ultron/frontend/node_modules/typescript/lib/typescript.js';
const source=fs.readFileSync(new URL('../ultron/frontend/src/hologram/project.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText;
const {validateProject}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
const good={schema:'ultron-project-v1',name:'Test',view:{explosion:.5,selected:0,isolated:false,wire:true,cut:0,camera:[0,0,8],target:[0,0,0],offsets:[[1,0,0]],notes:['Bakım notu']},parts:[{name:'Panel',description:'test',positions:[0,0,0,1,0,0,0,1,0],indices:null,base:[0,0,0],rotation:[0,0,0]}]};
assert.equal(validateProject(good).view.notes[0],'Bakım notu');
for(const mutate of [p=>p.parts[0].positions[0]=NaN,p=>p.parts[0].indices=[0,1,99],p=>p.parts[0].indices=[],p=>p.view.offsets=[],p=>p.view.selected=200,p=>p.view.camera=[0,0,0],p=>p.view.cut=Infinity,p=>p.view.notes=['x'.repeat(2001)],p=>p.schema='unsupported',p=>p.parts=Array(201).fill(p.parts[0])]){const p=structuredClone(good);mutate(p);assert.throws(()=>validateProject(p));}
console.log('PROJECT_VALIDATION_PASS (11 checks)');
