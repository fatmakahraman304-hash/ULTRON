const {test}=require('node:test');
const assert=require('node:assert/strict');
const moduleUnderTest=require('./static/long-listen.js');

function harness(available=true){
  let clock=0,nextId=1,recognizer=null;
  const timers=new Map(), state=[];
  const sent=[];
  const document={hidden:false, events:{}, addEventListener(name,fn){this.events[name]=fn;}};
  class Recognition {
    constructor(){recognizer=this;this.started=false;this.stopped=false;}
    start(){this.started=true;}
    stop(){this.stopped=true;}
    deliver(text,final=true){
      const record=[{transcript:text}];
      record.isFinal=final;
      this.onresult({resultIndex:0,results:[record]});
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
  assert.equal(h.ctrl.state(),'ready');
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
  assert.match(h.sent[0],/ar[a-d]aki konuşmalar bu isteğe dahil edilmedi/i);
});
test('permission error stops listening and does not send transcript',()=>{
  const h=harness();h.ctrl.start();
  h.rec.onerror({error:'not-allowed'});
  assert.equal(h.ctrl.state(),'interrupted');
  assert.equal(h.sent.length,0);
});
