"use strict";
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const voice=require('./static/local-voice.js');
const html=fs.readFileSync(path.join(__dirname,'static','index.html'),'utf8');
const serviceWorker=fs.readFileSync(path.join(__dirname,'static','sw.js'),'utf8');

class Recognition {
  static last;
  constructor(){ Recognition.last=this;this.startCalls=0;this.abortCalls=0; }
  start(){this.startCalls++;this.onstart?.()}
  stop(){this.onend?.()}
  abort(){this.abortCalls++;this.onend?.()}
  result(text){
    const arr=[Object.assign([{transcript:text}],{isFinal:true})];
    this.onresult?.({results:arr});
  }
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));

test('explicit local mic click triggers one Turkish speech turn',async()=>{
  const heard=[],states=[];
  const app=voice.create({host:{webkitSpeechRecognition:Recognition},
    onState:s=>states.push(s),onTranscript:s=>heard.push(s)});
  assert.equal(app.state,'idle');
  assert.equal(Recognition.last,undefined);
  assert.equal(app.toggle(),true);
  const mic=Recognition.last;
  assert.equal(mic.lang,'tr-TR');
  assert.equal(mic.continuous,false);
  assert.equal(mic.interimResults,false);
  assert.equal(mic.startCalls,1);
  mic.result('Merhaba ULTRON');
  mic.result('Duplike');
  await flush();await flush();
  assert.deepEqual(heard,['Merhaba ULTRON']);
  assert.deepEqual(states,['starting','listening','processing','idle']);
});
test('unsupported Safari voice fails clearly without enabling Gemini',()=>{
 const errors=[];
 const app=voice.create({host:{},onError:m=>errors.push(m)});
 assert.equal(app.toggle(),false);
 assert.equal(app.active(),false);
 assert.match(errors[0],/desteklemiyor/);
 assert.match(errors[0],/bulut bağlantısı denenebilir/);
});
test('permission denied and no-speech are honest failures',()=>{
 const errors=[];
 const app=voice.create({host:{SpeechRecognition:Recognition},onError:m=>errors.push(m)});
 app.start();
 Recognition.last.onerror({error:'not-allowed'});
 assert.match(errors[0],/izni reddedildi/);
 assert.equal(app.state,'idle');
 app.start();
 Recognition.last.onerror({error:'no-speech'});
 assert.match(errors[1],/Ses algılanmadı/);
});
test('stop cancels recognition and any late transcription',async()=>{
 const heard=[];
 const app=voice.create({host:{SpeechRecognition:Recognition},onTranscript:m=>heard.push(m)});
 app.start();const mic=Recognition.last;app.stop();mic.result('unsafe stale turn');
 await flush();assert.equal(mic.abortCalls,1);
 assert.deepEqual(heard,[]);
});
test('async transcript turn cannot double-submit',async()=>{
 let done;
 const received=[];
 const app=voice.create({host:{SpeechRecognition:Recognition},onTranscript:t=>{
   received.push(t);return new Promise(r=>{done=r});
 }});
 app.start();const mic=Recognition.last;mic.result('ULTRON konuş');
 await flush();
 assert.equal(app.state,'processing');
 assert.equal(app.start(),false);
 done();await flush();await flush();
 assert.deepEqual(received,['ULTRON konuş']);
 assert.equal(app.state,'idle');
});
test('PWA voice picks connected local first, otherwise Cloud, only after tap',()=>{
 assert.match(html,/localVoiceController=window\.ULTRONLocalVoice\?\.create/);
 assert.match(html,/localVoiceController\?\.toggle\(\)/);
 assert.match(html,/await send\(true\)/);
 assert.match(html,/const preferred=await refreshAutoBrain\(true\)/);
 assert.match(html,/if\(preferred==='local'\)/);
 assert.match(html,/await startVoice\(\)/);
 assert.doesNotMatch(html,/setTimeout\(\(\)=>startHandsFreeVoice\(\),(?:180|220|250)\)/);
 assert.doesNotMatch(html,/id="brainMode"/);
 assert.doesNotMatch(html,/ULTRON BEYİN/);
 assert.match(serviceWorker,/ultron-shell-v[0-9]+/);
 assert.ok(serviceWorker.includes("'/static/auto-brain.js'"));
 assert.match(serviceWorker,/\/static\/local-voice\.js/);
});
