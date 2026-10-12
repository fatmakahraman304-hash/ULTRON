const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const local=require('./static/local-listening-transport.js');

function demo({mode='success'}={}){
  let clock=0,count=0;
  const requests=[];
  const worker=local.create({
    uuid:()=> 'aaaaaaaa-aaaa-4aaa-8aaa-'+String(++count).padStart(12,'0'),
    now:()=>clock,
    sleep:async ms=>{clock+=ms;},
    deadlineMs:5000,
    async api(path,opts={}){
      requests.push({path,opts});
      if(opts.method==='POST'){
        if(mode==='offline')throw Error('network');
        return {status:'queued',command_id:1234};
      }
      if(mode==='timeout')return {status:'delivered'};
      if(mode==='failed')return {status:'failed'};
      return {status:'completed',stage:'map',analysis:'Tam analiz notu',
              provider:'local-ollama',model:'qwen3:4b'};
    }
  });
  return {worker,requests};
}
const chunk={stage:'map',part:1,total:2,text:'Birinci bölüm metni'};
test('completed Qwen chunk uses authenticated stage route, no Gemini fallback',async()=>{
 const h=demo();
 const result=await h.worker.request(chunk);
 assert.equal(result.analysis,'Tam analiz notu');
 assert.equal(result.provider,'local-ollama');
 assert.equal(h.requests.length,2);
 assert.equal(h.requests[0].path,'/api/listening-analysis/local');
 assert.equal(h.requests[1].path,'/api/listening-analysis/local/1234');
 assert.equal(h.requests[0].opts.method,'POST');
 assert.equal(h.worker.pendingCount(),0);
});
test('lost POST reply retains same UUID for explicit owner retry',async()=>{
 let posts=[],throwOnce=true;
 const c=local.create({
   uuid:()=> '00000000-0000-4000-8000-000000000001',
   sleep:async()=>{},
   async api(path,opts){
     if(opts.method==='POST'){
       const body=JSON.parse(opts.body);
       posts.push(body.request_id);
       if(throwOnce){throwOnce=false;throw Error('response lost');}
       return {status:'queued',command_id:4};
     }
     return {status:'completed',stage:'map',analysis:'Yanıt',
       provider:'local-ollama'};
   }
 });
 await assert.rejects(c.request(chunk),/response lost/);
 assert.equal(c.pendingCount(),1);
 const result=await c.request(chunk);
 assert.equal(result.analysis,'Yanıt');
 assert.deepEqual(posts,['00000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000001']);
});
test('timeout while task is queued does not duplicate POST on explicit recheck',async()=>{
 let posts=0,mode='timeout',clock=0;
 const transport=local.create({
   uuid:()=> '00000000-0000-4000-8000-000000000001',
   now:()=>clock,deadlineMs:4000,sleep:async ms=>{clock+=ms;},
   async api(path,options){
     if(options.method==='POST'){posts++;return {status:'queued',command_id:99};}
     if(mode==='timeout')return {status:'delivered'};
     return {status:'completed',stage:'map',analysis:'Tamam',
       provider:'local-ollama'};
   }
 });
 await assert.rejects(transport.request(chunk),/zaman aşımı/);
 assert.equal(posts,1);
 mode='done';
 await transport.request(chunk);
 assert.equal(posts,1);
});
test('queued failed jobs and forged providers never return a successful summary',async()=>{
 const bad=demo({mode:'failed'});
 await assert.rejects(bad.worker.request(chunk),/Gemini’ye otomatik geçilmedi/);
 const fake=local.create({
   uuid:()=> '00000000-0000-4000-8000-000000000001',
   async api(p,o){
     if(o.method==='POST')return {status:'queued',command_id:2};
     return {status:'completed',stage:'map',analysis:'Fake',provider:'gemini'};
   }
 });
 await assert.rejects(fake.request(chunk),/Beklenmeyen/);
});
test('provider selection is explicit and warns about Render transit before enabling',()=>{
 const html=fs.readFileSync(__dirname+'/static/index.html','utf8');
 for(const x of ['longListenProvider', 'value="local"', 'Render görev kuyruğu',
                 "window.confirm('Yerel Qwen analizi", "longListenQwenAnalyzer",
                 "longListenSelectedProvider", "longListenActiveAnalyzer"]){
    assert.ok(html.includes(x),x);
 }
 assert.equal(html.includes('autoLocalFallbackToGemini'),false);
});
