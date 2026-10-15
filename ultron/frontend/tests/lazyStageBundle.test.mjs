import assert from 'node:assert/strict';
import {readFile,readdir} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..','dist');

async function imports(source){
  return [...source.matchAll(/from\s*["']([^"']+\.js)["']/g)].map(match=>match[1]);
}

test('the initial dashboard graph defers the Three.js WebGL renderer',async()=>{
  const html=await readFile(path.join(root,'index.html'),'utf8');
  const entry=html.match(/<script[^>]+src="([^"]+\.js)"/);
  assert.ok(entry,'Vite entry script should be present');
  const staticGraph=new Set();
  const visit=async file=>{
    file=path.resolve(root,file);
    if(staticGraph.has(file))return;
    staticGraph.add(file);
    const source=await readFile(file,'utf8');
    for(const specifier of await imports(source)){
      if(specifier.startsWith('.'))await visit(path.relative(root,path.resolve(path.dirname(file),specifier)));
    }
  };
  await visit(entry[1].replace(/^\.\//,'').replace(/^\//,''));

  const scripts=(await readdir(path.join(root,'assets'))).filter(name=>name.endsWith('.js'));
  const rendererFiles=[];
  for(const name of scripts){
    if((await readFile(path.join(root,'assets',name),'utf8')).includes('WebGLRenderer'))rendererFiles.push(name);
  }
  assert.ok(rendererFiles.length,'The requested 3D renderer must remain in the production build');
  for(const name of rendererFiles){
    assert.ok(!staticGraph.has(path.join(root,'assets',name)),`${name} must not load with the initial chat dashboard`);
  }
});
