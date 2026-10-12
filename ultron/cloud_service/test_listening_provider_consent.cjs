const {test}=require('node:test');
const assert=require('node:assert/strict');
const p=require('./static/listening-provider.js');
const fs=require('node:fs'),vm=require('node:vm');

const online=[{device:'desktop',online:true,state:{local_listening_analysis_ready:true}}];
const older=[{device:'desktop',online:true,state:{local_chat_ready:true}}];

test('auto chooses fresh worker Qwen; otherwise Gemini with disclosure',()=>{
  assert.equal(p.select('auto',online),'local');
  assert.equal(p.select('auto',older),'gemini');
  assert.equal(p.select('auto',null),'gemini');
  assert.match(p.disclosure('local',152000),/Render.*Windows/);
  assert.match(p.disclosure('local',152000),/PostgreSQL|veritaban/);
  assert.match(p.disclosure('gemini',14200),/Gemini Cloud/);
});
test('explicit Qwen choice cannot silently fall back to Gemini when offline',()=>{
  assert.throws(()=>p.select('local',older),/gizlice geçilmeyecek/);
  assert.throws(()=>p.select('local',[]),/hazır değil/);
  assert.equal(p.select('local',online),'local');
  assert.equal(p.select('gemini',online),'gemini');
});
test('reject unknown provider, no speech and oversized text before disclosure',()=>{
  assert.throws(()=>p.select('agent_tool',online),/Bilinmeyen/);
  for(const size of [0,-1,300001,NaN,1.4])
    assert.throws(()=>p.disclosure('gemini',size),/uzunluğu/);
  assert.throws(()=>p.disclosure('unknown',123),/belirlenmedi/);
});
test('UI loads consent policy and checks approval before sending any chunk',()=>{
  const html=fs.readFileSync(__dirname+'/static/index.html','utf8');
  const js=html.match(/<script>([\s\S]*?)<\/script>/);
  assert.ok(js,'Expected inline UI');
  new vm.Script(js[1]);
  for(const needle of ['id="longListenProvider"','value="auto"','value="local"',
    'value="gemini"', '/static/listening-provider.js',
    'window.ULTRONListeningProvider.select(requested,devices)',
    'window.ULTRONListeningProvider.disclosure(chosen,meta.transcript.length)',
    'if(!approved){',
    'longListenController.failDelivery',
    'longListenAnalysisProvider=chosen',
    "const report=await longListenAnalyzer.run(meta.transcript);"]){
    assert.ok(html.includes(needle),'missing UI gate: '+needle);
  }
  const positionConsent=html.indexOf('if(!approved){');
  const positionProviderLock=html.indexOf('longListenAnalysisProvider=chosen;');
  const positionUpload=html.indexOf('const report=await longListenAnalyzer.run(meta.transcript);');
  assert.ok(positionConsent<positionProviderLock&&positionProviderLock<positionUpload);
  assert.ok(html.includes("const permitted=requested===longListenRequestedChoice")); 
  assert.ok(html.includes("$('#longListenProvider').disabled=true;"));
  assert.ok(html.includes("longListenAnalyzer.active()||longListenController.state()==='submitting'"));
});
