const {test}=require('node:test');
const assert=require('node:assert/strict');
const probe=require('./static/local-listening-probe.js');
const fs=require('node:fs');
const vm=require('node:vm');
const ready=[{device:'desktop',online:true,state:{local_listening_analysis_ready:true}}];

test('probe submits only synthetic example after fresh Windows capability check',async()=>{
  const payloads=[],statuses=[],p=probe.create({
    presence:async()=>({devices:ready}),
    id:()=> 'probe-test-12345678',now:()=>4242,
    request:async b=>{
      payloads.push(b);
      return {stage:'map',provider:'local-ollama',model:'qwen3:4b',analysis:'Bu bir sentetik bağlantı testidir.'};
    },
    onStatus:s=>statuses.push(s)
  });
  const r=await p.run();
  assert.equal(r.ok,true);
  assert.equal(r.synthetic,true);
  assert.equal(r.model,'qwen3:4b');
  assert.equal(payloads.length,1);
  assert.equal(payloads[0].stage,'map');
  assert.equal(payloads[0].part,1);
  assert.equal(payloads[0].total,1);
  assert.match(payloads[0].text,/probe-test-12345678/);
  assert.match(payloads[0].text,/Gerçek kullanıcı konuşması yoktur/);
  assert.equal(statuses.at(-1).phase,'success');
  assert.equal(p.active(),false);
});

test('unavailable laptop and old desktop never send an analysis request',async()=>{
  for(const devices of [[],[{device:'desktop',online:false,state:{local_listening_analysis_ready:true}}],
      [{device:'desktop',online:true,state:{local_chat_ready:true}}]]){
    const payloads=[],status=[];
    const p=probe.create({presence:async()=>({devices}),
      request:async x=>payloads.push(x),onStatus:s=>status.push(s)});
    await assert.rejects(p.run(),/Laptop /);
    assert.equal(payloads.length,0);
    assert.equal(status.at(-1).phase,'failure');
    assert.equal(p.active(),false);
  }
});

test('probe never confuses Gemini replies or unrelated stage with local Qwen success',async()=>{
  for(const result of [
    {stage:'map',provider:'gemini',model:'qwen3:4b',analysis:'x'},
    {stage:'final',provider:'local-ollama',model:'qwen3:4b',analysis:'x'},
    {stage:'map',provider:'local-ollama',model:'llava:7b',analysis:'x'},
    {stage:'map',provider:'local-ollama',model:'qwen3:4b',analysis:'  '}
  ]){
    const p=probe.create({presence:async()=>({devices:ready}),id:()=> 'abcdefgh-1234',
      request:async()=>result});
    await assert.rejects(p.run(),/doğrulanmış/);
    assert.equal(p.active(),false);
  }
});

test('probe cannot launch a concurrent second Qwen job',async()=>{
  let release,requests=0;
  const block=new Promise(resolve=>release=resolve);
  const p=probe.create({presence:async()=>({devices:ready}),
    id:()=> 'abcdefgh-2345',
    request:async()=>{requests++;await block;
      return {stage:'map',provider:'local-ollama',model:'qwen2.5-coder:7b',analysis:'ok'};}});
  const first=p.run();
  await assert.rejects(p.run(),/zaten devam ediyor/);
  release();
  await first;
  assert.equal(requests,1);
  assert.equal(p.active(),false);
});

test('fresh owner clicks generate new challenges and never reuse a stale confirmation',async()=>{
  let i=0;const texts=[];
  const p=probe.create({presence:async()=>({devices:ready}),
    id:()=> 'test-nonce-'+(++i)+'-aaaaaa',
    request:async body=>{texts.push(body.text);
      return {stage:'map',provider:'local-ollama',model:'qwen3:8b',analysis:'Yalnızca örnek metin'};}
  });
  await p.run();await p.run();
  assert.equal(texts.length,2);
  assert.notEqual(texts[0],texts[1]);
});

test('probe errors never put raw provider error or model conversation into UI',async()=>{
  let status;
  const p=probe.create({presence:async()=>({devices:ready}),
    id:()=> 'abcdefgh-1234',
    request:async()=>{throw new Error('ultron token sk-proj-test-never-show');},
    onStatus:s=>{status=s;}
  });
  await assert.rejects(p.run(),/ultron token/);
  assert.equal(status.phase,'failure');
  assert.doesNotMatch(status.message,/sk-proj-test-never-show/);
});

test('mobile UI includes probe without a permanent main-screen navigation button',()=>{
  const html=fs.readFileSync(__dirname+'/static/index.html','utf8');
  const js=html.match(/<script>([\s\S]*?)<\/script>/);
  assert.ok(js);new vm.Script(js[1]);
  for(const mark of [
    '/static/local-listening-probe.js','id="longListenQwenProbe"',
    'id="longListenQwenProbeStatus"','window.ULTRONLocalListeningProbe.create(',
    "$('#longListenQwenProbe').onclick=async()=>", 'longListenController.active()',
    'longListenAnalyzer.active()','await qwenListeningProbe.run()'
  ])assert.ok(html.includes(mark),mark);
  const start=html.indexOf('id="longListenProviderWrap"'),
    end=html.indexOf('</details>',start);
  assert.ok(start>=0&&end>start);
  assert.ok(html.slice(start,end).includes('id="longListenQwenProbe"'));
  assert.ok(html.includes('id="sceneCanvas"')); // production 3D intact
});
