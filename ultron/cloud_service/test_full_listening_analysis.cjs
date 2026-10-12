const {test}=require('node:test');
const assert=require('node:assert/strict');
const analysis=require('./static/listening-analysis.js');

test('all 300k characters are assigned to bounded ordered chunks without data loss',()=>{
  const text=('Birinci bölüm.\n'+'duyulan karar ve notlar '.repeat(410)) .repeat(29).slice(0,300000);
  const chunks=analysis.split(text);
  assert.equal(chunks.join(''),text);
  assert.ok(chunks.length<=32);
  assert.ok(chunks.every(s=>s.length<=analysis.CHUNK_SIZE&&s.length>0));
});
test('analysis rejects oversize and empty transcripts before any upload',()=>{
  assert.throws(()=>analysis.split('   '));
  assert.throws(()=>analysis.split('x'.repeat(300001)));
});
test('map reduce final reads every fragment and only submits bounded read-only analysis calls',async()=>{
  const transcript='giriş '+('orta bölüm konuşması '.repeat(11000))+' SON KARAR: buton yok.';
  const chunks=analysis.split(transcript),calls=[],events=[];
  const client=analysis.create({
    async request(payload){
      calls.push(payload);
      if(payload.stage==='map'){
        assert.equal(payload.total,chunks.length);
        assert.equal(payload.text,chunks[payload.part-1]);
        return {stage:'map',analysis:'not-'+payload.part};
      }
      if(payload.stage==='reduce'){
        assert.ok(payload.text.length<=12000);
        return {stage:'reduce',analysis:'birleştirilmiş '+payload.text.slice(0,500)};
      }
      assert.equal(payload.stage,'final');
      return {stage:'final',analysis:'Kararlar: buton istemiyor. Yapılacak işler: öneriler, uygulanmadı.'};
    },
    onProgress:e=>events.push(e)
  });
  const reply=await client.run(transcript);
  assert.equal(reply.chunksAnalyzed,chunks.length);
  assert.equal(reply.parts,chunks.length);
  assert.ok(calls.filter(c=>c.stage==='map').length===chunks.length);
  assert.ok(calls.filter(c=>c.stage==='reduce').length>=1);
  assert.equal(calls.at(-1).stage,'final');
  assert.match(reply.answer,/uygulanmadı/);
  assert.equal(reply.saved,false);
  assert.equal(events.at(-1).status,'Tamamlandı');
});
test('failed map request keeps verified partial progress until explicit re-invocation',async()=>{
  const text='Not '.repeat(7500),parts=analysis.split(text),seen=[];
  let failed=false;
  const worker=analysis.create({
    async request(body){
      seen.push(body);
      if(body.stage==='map'&&body.part===2&&!failed){failed=true;throw Error('network');}
      return {stage:body.stage,analysis:'tamam'};
    }
  });
  await assert.rejects(worker.run(text),/network/);
  assert.equal(worker.checkpoint().mapped,1);
  assert.equal(seen.length,2);
  const response=await worker.run(text);
  assert.equal(response.chunksAnalyzed,parts.length);
  assert.equal(seen.filter(s=>s.stage==='map'&&s.part===1).length,1);
  assert.equal(seen.filter(s=>s.stage==='map'&&s.part===2).length,2);
});
test('failed reduce resumes without repeating successful chunk map work',async()=>{
  const text='uzun konuşma '.repeat(5000);let failed=false;
  const calls=[],worker=analysis.create({
    async request(p){
      calls.push(p.stage);
      if(p.stage==='reduce'&&!failed){failed=true;throw Error('reducer offline');}
      return {stage:p.stage,analysis:'kısa not'};
    }
  });
  await assert.rejects(worker.run(text),/offline/);
  const checkpoint=worker.checkpoint();
  assert.equal(checkpoint.mapped,checkpoint.parts);
  const result=await worker.run(text);
  assert.equal(result.parts,checkpoint.parts);
  assert.equal(calls.filter(s=>s==='map').length,checkpoint.parts);
});
test('invalid response and abandoned local analysis produce no false success',async()=>{
  const worker=analysis.create({async request(){return {stage:'wrong',analysis:'sahte'};}});
  await assert.rejects(worker.run('test'),/doğrulanmamış/);
  assert.equal(worker.checkpoint().mapped,0);
  assert.equal(worker.clear(),true);
  assert.equal(worker.checkpoint(),null);
});

test('user can stop lengthy analysis without sending remaining chunks',async()=>{
  const text='konuşma '.repeat(7000);
  let release,requests=[];
  const first=new Promise(resolve=>{release=resolve;});
  const worker=analysis.create({
    async request(payload){requests.push(payload);if(requests.length===1)await first;return {stage:payload.stage,analysis:'not'};}
  });
  const promise=worker.run(text);
  assert.equal(worker.active(),true);
  assert.equal(worker.clear(),false);
  assert.equal(worker.stop(),true);
  release();
  await assert.rejects(promise,/kullanıcı tarafından durduruldu/);
  assert.equal(worker.active(),false);
  assert.equal(requests.length,1);
  assert.equal(worker.checkpoint().mapped,0);
  const resumed=await worker.run(text);
  assert.equal(resumed.chunksAnalyzed,analysis.split(text).length);
  assert.equal(worker.clear(),true);
});
test('UI exposes manual memory save, stopped analysis and readonly authenticated endpoint',()=>{
  const fs=require('node:fs');
  const html=fs.readFileSync(__dirname+'/static/index.html','utf8');
  for(const needle of ['longListenStopAnalysis','longListenSaveMemory','ULTRONListeningAnalysis.create',
                       "/api/listening-analysis", "window.confirm(", "category:'NOTE'",
                       "longListenAnalyzer.run(meta.transcript)"])assert.ok(html.includes(needle),needle);
});
