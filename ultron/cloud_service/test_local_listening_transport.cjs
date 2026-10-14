const {test}=require('node:test');
const assert=require('node:assert/strict');
const {ready,create}=require('./static/local-listening.js');

test('local provider requires fresh desktop heartbeat and explicit worker capability',()=>{
  assert.equal(ready([{device:'desktop',online:true,state:{local_listening_analysis_ready:true}}]),true);
  for(const state of [
    [{device:'desktop',online:false,state:{local_listening_analysis_ready:true}}],
    [{device:'desktop',online:true,state:{local_chat_ready:true}}],
    [{device:'phone',online:true,state:{local_listening_analysis_ready:true}}],
    [],null
  ])assert.equal(ready(state),false);
});
test('accepted Qwen job is polled until verified matching local Ollama result',async()=>{
  const sent=[],responses=[{status:'queued'},{status:'delivered'},
    {status:'completed',stage:'map',analysis:'Tasarım kararları',provider:'local-ollama',model:'qwen3:4b'}];
  let stamp=0;
  const client=create({
    api:async(path,opts)=>{
      sent.push({path,opts});
      return opts?.method==='POST'?{id:42,status:'queued'}:responses.shift();
    },
    id:()=> '123e4567-e89b-12d3-a456-426614174000',
    now:()=>stamp,sleep:async()=>{stamp+=2300;}
  });
  const result=await client.request({stage:'map',text:'Mimarlık sunumum',part:1,total:2});
  assert.equal(result.analysis,'Tasarım kararları');
  assert.equal(sent.filter(x=>x.opts?.method==='POST').length,1);
  assert.equal(sent.filter(x=>x.path.endsWith('/42')).length,3);
  assert.match(sent[0].opts.body,/123e4567-e89b/);
});
test('lost submission response reuses same request ID on owner retry',async()=>{
  let failed=false,posts=[],polls=0;
  const client=create({id:()=> 'first-request',
    api:async(path,opts)=>{
      if(opts?.method==='POST'){
        posts.push(JSON.parse(opts.body));
        if(!failed){failed=true;throw Error('network');}
        return {id:98,status:'queued',replayed:true};
      }
      polls++;
      return {status:'completed',stage:'final',analysis:'Kısa rapor',provider:'local-ollama'};
    },
    sleep:async()=>{},
  });
  const body={stage:'final',text:'Konuşma özeti'};
  await assert.rejects(client.request(body),error=>error.code==='analysis_request_failed');
  const answer=await client.request(body);
  assert.equal(answer.analysis,'Kısa rapor');
  assert.equal(posts.length,2);
  assert.equal(posts[0].request_id,posts[1].request_id);
  assert.equal(polls,1);
});
test('Qwen worker error never silently resubmits or switches provider',async()=>{
  let posts=0;
  const client=create({id:()=> 'fail',
    api:async(path,opts)=>{
      if(opts?.method==='POST'){posts++;return {id:10};}
      return {status:'failed'};
    }
  });
  await assert.rejects(client.request({stage:'map',text:'Günlük notlar',part:1,total:1}),/tamamlayamadı/);
  assert.equal(posts,1);
});
test('mismatched stage and non-local analysis are rejected',async()=>{
  for(const result of [
    {status:'completed',stage:'reduce',analysis:'x',provider:'local-ollama'},
    {status:'completed',stage:'map',analysis:'x',provider:'cloud-gemini'},
    {status:'completed',stage:'map',analysis:'' ,provider:'local-ollama'},
  ]){
    const client=create({id:()=> 'id',api:async(path,opts)=>opts?.method==='POST'?{id:9}:result});
    await assert.rejects(client.request({stage:'map',text:'not',part:1,total:1}),/doğrulanmamış/);
  }
});
test('invalid or oversize payload never reaches the network',async()=>{
  let calls=0;
  const client=create({api:async()=>{calls++;}});
  await assert.rejects(client.request({stage:'execute',text:'dosyayı sil'}),/geçersiz/);
  await assert.rejects(client.request({stage:'map',text:'X'.repeat(12001)}),/geçersiz/);
  assert.equal(calls,0);
});

test('transient result reads recover on the same accepted job without another POST',async()=>{
  let posts=0,polls=0,stamp=0;
  const client=create({id:()=> 'same-job',now:()=>stamp,sleep:async ms=>{stamp+=ms;},
    api:async(path,opts)=>{
      if(opts?.method==='POST'){posts++;return {id:51};}
      polls++;
      if(polls===1)throw Object.assign(Error('private network detail'),{network:true});
      if(polls===2)throw Object.assign(Error('private upstream detail'),{status:503});
      if(polls===3)throw Object.assign(Error('private server detail'),{status:500});
      return {status:'completed',stage:'final',analysis:'Kararlar hazır',provider:'local-ollama',model:'qwen3:4b'};
    }});
  assert.equal((await client.request({stage:'final',text:'Notlar'})).analysis,'Kararlar hazır');
  assert.equal(posts,1);assert.equal(polls,4);
});

test('verified result is reused in tab memory even after the network goes offline',async()=>{
  let calls=0;
  const client=create({id:()=> 'cached',api:async(path,opts)=>{
    calls++;if(calls>2)throw Object.assign(Error('offline'),{network:true});
    return opts?.method==='POST'?{id:52}:{status:'completed',stage:'map',analysis:'Doğrulanmış not',provider:'local-ollama',model:'qwen3:4b'};
  }});
  const body={stage:'map',text:'Konuşma',part:1,total:1};
  const first=await client.request(body);
  assert.deepEqual(await client.request(body),first);
  assert.equal(calls,2);
});

test('poll deadline preserves accepted ID for explicit resume and gives safe pending status',async()=>{
  let posts=0,stamp=0,online=false;
  const client=create({id:()=> 'resume',timeoutMs:5000,now:()=>stamp,sleep:async ms=>{stamp+=ms;},
    api:async(path,opts)=>{
      if(opts?.method==='POST'){posts++;return {id:53};}
      if(!online)throw Object.assign(Error('SECRET network trace'),{network:true});
      return {status:'completed',stage:'reduce',analysis:'Birleşmiş not',provider:'local-ollama',model:'qwen3:4b'};
    }});
  const body={stage:'reduce',text:'Bölüm notları'};
  await assert.rejects(client.request(body),error=>error.pending===true&&error.commandId===53&&!error.message.includes('SECRET'));
  online=true;
  assert.equal((await client.request(body)).analysis,'Birleşmiş not');
  assert.equal(posts,1);
});

test('invalid completed API output is terminal even when its HTTP status is 502',async()=>{
  let reads=0;
  const client=create({id:()=> 'invalid',api:async(path,opts)=>{
    if(opts?.method==='POST')return {id:54};
    reads++;throw Object.assign(Error('SECRET raw provider trace'),{status:502,data:{error:'invalid_local_analysis'}});
  }});
  await assert.rejects(client.request({stage:'final',text:'Not'}),error=>error.code==='invalid_local_analysis'&&!error.message.includes('SECRET'));
  assert.equal(reads,1);
});