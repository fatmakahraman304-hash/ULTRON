const {test}=require('node:test');
const assert=require('node:assert/strict');
const moduleUnderTest=require('./static/long-listen.js');

function harness(available=true){
  let clock=0,nextId=1,recognizer=null;
  const timers=new Map(), state=[];
  const sent=[];
  const document={hidden:false, events:{}, addEventListener(name,fn){this.events[name]=fn;}};
  class Recognition {
    constructor(){recognizer=this;this.started=false;this.stopped=false;this.results=[];}
    start(){this.started=true;}
    stop(){this.stopped=true;}
    deliver(text,final=true){
      const record=[{transcript:text}];
      record.isFinal=final;
      const index=this.results.length;
      this.results.push(record);
      this.onresult({resultIndex:index,results:this.results});
    }
  }
  const ctrl=moduleUnderTest.create({
    Recognition:available?Recognition:null,
    document:document, now:()=>clock,
    setTimeout(fn,ms){const id=nextId++;timers.set(id,{fn,ms});return id;},
    clearTimeout(id){timers.delete(id);},
    onState(s){state.push(s);},onAnswer(s){sent.push(s);}
  });
  return {ctrl,document,state,sent,timers,
    get rec(){return recognizer;},
    advance(ms){clock+=ms;},
    runDelay(delay){
      const found=[...timers.entries()].find(([,entry])=>entry.ms===delay);
      if(!found)throw Error('Timer '+delay+' missing');
      timers.delete(found[0]);found[1].fn();
    },
    runTimers(){
      const scheduled=[...timers.entries()];
      scheduled.forEach(([id,entry])=>{if(timers.has(id)){timers.delete(id);entry.fn();}});
    }
  };
}
test('only explicit one-hour request arms microphone',()=>{
  for(const text of ['1 saat dinle beni','Ultron, bir saat boyunca beni dinle','beni 1 saat dinle','bir saat dinle']){
    assert.equal(moduleUnderTest.isStart(text),true,text);
  }
  for(const text of ['1 saat dinleyebilir misin?', '1 saat dinle beni ve dosyayı sil','sessizce kaydet']){
    assert.equal(moduleUnderTest.isStart(text),false,text);
  }
});
test('unsupported browser never pretends to listen',()=>{
  const h=harness(false);
  assert.equal(h.ctrl.start(),false);
  assert.equal(h.ctrl.state(),'unsupported');
  assert.equal(h.sent.length,0);
});
test('one hour receives transcript locally, answers only after spoken command',()=>{
  const h=harness();
  assert.equal(h.ctrl.start(),true);
  assert.equal(h.rec.started,true);
  h.rec.deliver('Bugün mimarlık çizimimi konuşacağım');
  h.rec.deliver('henüz tamamlanmadı',false);
  assert.equal(h.sent.length,0);
  assert.match(h.ctrl.transcript(),/mimarlık çizimimi/);
  assert.doesNotMatch(h.ctrl.transcript(),/tamamlanmadı/);
  h.rec.deliver('Şimdi cevap ver');
  assert.equal(h.rec.stopped,true);
  assert.equal(h.ctrl.state(),'submitted');
  assert.equal(h.sent.length,1);
  assert.equal(h.ctrl.transcript(),'');
  assert.equal(h.ctrl.finish(true),false);
  assert.equal(h.sent.length,1);
  assert.match(h.sent[0],/mimarlık çizimimi/);
  assert.doesNotMatch(h.sent[0],/Şimdi cevap ver/);
});
test('deadline stops without automatically uploading or replying',()=>{
  const h=harness();
  h.ctrl.start();
  h.rec.deliver('Tek notum bu');
  h.advance(3600001);
  h.ctrl.tick();
  assert.equal(h.rec.stopped,true);
  assert.equal(h.ctrl.state(),'ready');
  assert.deepEqual(h.sent,[]);
  assert.equal(h.ctrl.finish(true),true);
  assert.equal(h.sent.length,1);
});
test('background or lock interrupts and retains partial text until explicit reply',()=>{
  const h=harness();
  h.ctrl.start();
  h.rec.deliver('Bu cümle kayıtlı');
  h.document.hidden=true;
  h.document.events.visibilitychange();
  assert.equal(h.ctrl.state(),'interrupted');
  assert.equal(h.rec.stopped,true);
  assert.equal(h.sent.length,0);
  assert.equal(h.ctrl.finish(true),true);
  assert.match(h.sent[0],/Bu cümle kayıtlı/);
});
test('cancel clears sensitive local transcript without submission',()=>{
  const h=harness();
  h.ctrl.start();
  h.rec.deliver('Özel bir bilgi');
  h.ctrl.cancel();
  assert.equal(h.ctrl.transcript(),'');
  assert.equal(h.ctrl.hasSession(),false);
  assert.deepEqual(h.sent,[]);
});
test('repeated recognizer events do not duplicate final segment',()=>{
  const h=harness();
  h.ctrl.start();
  const row=[{transcript:'Merhaba'}];row.isFinal=true;
  const event={resultIndex:0,results:[row]};
  h.rec.onresult(event);h.rec.onresult(event);
  assert.equal(h.ctrl.transcript(),'Merhaba');
});
test('very long transcripts are explicitly labelled excerpts within provider limit',()=>{
  const h=harness();h.ctrl.start();
  for(let i=0;i<160;i++)h.rec.deliver('mimarlık ve tasarım hakkında '+String(i)+' '+('uzun '.repeat(25)));
  assert.ok(h.ctrl.transcript().length<=26000);
  h.ctrl.finish(true);
  assert.equal(h.sent.length,1);
  assert.ok(h.sent[0].length<3000);
  assert.match(h.sent[0],/aradaki konuşmalar bu isteğe dahil edilmedi/i);
});
test('permission error stops listening and does not send transcript',()=>{
  const h=harness();h.ctrl.start();
  h.rec.onerror({error:'not-allowed'});
  assert.equal(h.ctrl.state(),'interrupted');
  assert.equal(h.sent.length,0);
});

test('speech service auto-end restarts within session and keeps earlier notes',()=>{
  const h=harness();
  h.ctrl.start();
  h.rec.deliver('Önce planı konuşacağız');
  const first=h.rec;
  first.onend();
  assert.ok([...h.timers.values()].some(t=>t.ms===600));
  h.runDelay(600);
  assert.notEqual(h.rec,first);
  assert.equal(h.rec.started,true);
  h.rec.deliver('Sonra maliyetleri');
  h.rec.deliver('Cevap ver');
  assert.equal(h.sent.length,1);
  assert.match(h.sent[0],/Önce planı konuşacağız/);
  assert.match(h.sent[0],/Sonra maliyetleri/);
});
test('repeated service resets without recognized speech stop rather than looping forever',()=>{
  const h=harness();
  h.ctrl.start();
  for(let i=0;i<9;i++){
    h.rec.onend();
    if(i<8)h.runDelay(600);
  }
  assert.equal(h.ctrl.state(),'interrupted');
  assert.equal(h.sent.length,0);
});
test('spoken cancel command erases transcript and does not contact assistant',()=>{
  const h=harness();
  h.ctrl.start();
  h.rec.deliver('Kaydedilmiş bilgi');
  h.rec.deliver('Dinlemeyi durdur');
  assert.equal(h.ctrl.state(),'idle');
  assert.equal(h.ctrl.transcript(),'');
  assert.equal(h.sent.length,0);
});

test('pause and resume preserve prior dictation and original one-hour clock',()=>{
  const h=harness();
  assert.equal(h.ctrl.start(),true);
  h.rec.deliver('İlk bölümde tasarım konuşuldu');
  h.advance(20*60*1000);
  assert.equal(h.ctrl.pause(),true);
  assert.equal(h.ctrl.state(),'interrupted');
  assert.equal(h.ctrl.active(),false);
  h.advance(5*60*1000);
  assert.equal(h.ctrl.resume(),true);
  assert.equal(h.ctrl.state(),'listening');
  assert.equal(h.state.at(-1).secondsLeft,35*60);
  h.rec.deliver('Devamında maliyetler konuşuldu');
  assert.match(h.ctrl.transcript(),/İlk bölümde/);
  assert.match(h.ctrl.transcript(),/maliyetler/);
  assert.equal(h.sent.length,0);
  h.advance(35*60*1000+1);
  h.ctrl.tick();
  assert.equal(h.ctrl.state(),'ready');
  assert.equal(h.sent.length,0);
  assert.equal(h.ctrl.finish(true),true);
  assert.equal(h.sent.length,1);
});
test('resume never starts an expired session or a hidden microphone',()=>{
  const h=harness();
  assert.equal(h.ctrl.resume(),false);
  h.ctrl.start();
  h.rec.deliver('Görev başladı');
  h.document.hidden=true;
  h.document.events.visibilitychange();
  assert.equal(h.ctrl.resume(),false);
  assert.equal(h.ctrl.state(),'interrupted');
  h.document.hidden=false;
  h.advance(60*60*1000+1);
  assert.equal(h.ctrl.resume(),false);
  assert.equal(h.ctrl.state(),'ready');
  assert.equal(h.sent.length,0);
  assert.match(h.ctrl.transcript(),/Görev başladı/);
});
test('full exported draft has higher cap and clearly reports memory omissions',()=>{
  const h=harness();h.ctrl.start();
  const longSentence='A'.repeat(1180);
  for(let i=0;i<300;i++)h.rec.deliver('Not '+i+' '+longSentence);
  assert.ok(h.ctrl.omitted()>0);
  assert.ok(h.ctrl.transcript().length<302000);
  assert.match(h.ctrl.transcript(),/Not 0 /);
  assert.match(h.ctrl.transcript(),/Not 299 /);
  h.ctrl.finish(true);
  assert.equal(h.sent.length,1);
  assert.match(h.sent[0],/\[Orta bölümden örnek\]/);
  assert.match(h.sent[0],/aradaki konuşmalar bu isteğe dahil edilmedi/);
  assert.ok(h.sent[0].length<=3000);
  assert.equal(h.ctrl.omitted(),0);
});
test('pausing and resuming never auto-answers or repeats a finished submission',()=>{
  const h=harness();h.ctrl.start();
  h.rec.deliver('Konuşmaya başladım');
  h.ctrl.pause();h.ctrl.resume();
  h.rec.deliver('Devam ettim');
  h.ctrl.pause();h.ctrl.resume();
  assert.deepEqual(h.sent,[]);
  h.rec.deliver('Cevap ver');
  assert.equal(h.sent.length,1);
  assert.equal(h.ctrl.state(),'submitted');
  assert.equal(h.ctrl.resume(),false);
  assert.equal(h.ctrl.finish(true),false);
  assert.equal(h.sent.length,1);
});
