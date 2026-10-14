'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'static/index.html'),'utf8');
test('mobile composer exposes stop while a chat request is active',()=>{
 assert.match(html,/if\(activeChatRequest\)\{cancelActiveChat\(\);return\}/);
 assert.match(html,/classList\.add\('is-stop'\)/);
 assert.match(html,/chatRequestGeneration\+\+;chatSendVersion\+\+;chatSending=false/);
 assert.match(html,/if\(mayFinalizeChatSend\(sendGeneration\)\)\{/);
 assert.match(html,/speechSynthesis\.cancel\(\)/);
 assert.match(html,/function stopPlayback\(\)/);
});
test('an interrupted older send cannot clear a newer send state',()=>{
 const ctx={chatRequestGeneration:9};vm.createContext(ctx);
 const helper=html.match(/function mayFinalizeChatSend\(generation\)\{return generation===chatRequestGeneration\}/);
 assert.ok(helper);vm.runInContext(helper[0],ctx);
 assert.equal(ctx.mayFinalizeChatSend(8),false);
 assert.equal(ctx.mayFinalizeChatSend(9),true);
});
test('spoken stop phrases interrupt only an active chat request',()=>{
 const helper=html.match(/function isSpokenStopCommand\(text\)\{[\s\S]*?\n\}/);
 assert.ok(helper);const ctx={};vm.createContext(ctx);vm.runInContext(helper[0],ctx);
 for(const phrase of ['Dur','Gölge dur.','Sus','Konuşmayı kes','konusmayi kes','Yanıtı durdur','Stop speaking'])
  assert.equal(ctx.isSpokenStopCommand(phrase),true,phrase);
 for(const phrase of ['Durumu açıkla','Lütfen durumu kontrol et','devam et'])
  assert.equal(ctx.isSpokenStopCommand(phrase),false,phrase);
 assert.match(html,/if\(activeChatRequest&&isSpokenStopCommand\(d\.text\)\)\{/);
});
test('late cancel acknowledgement cannot replace the conversation of a newer request',()=>{
 const helper=html.match(/function mayApplyChatCancelResult\(requestId\)\{[\s\S]*?\n\}/);
 assert.ok(helper);const ctx={activeChatRequest:{identity:{request_id:'new-request'}}};
 vm.createContext(ctx);vm.runInContext(helper[0],ctx);
 assert.equal(ctx.mayApplyChatCancelResult('old-request'),false);
 assert.equal(ctx.mayApplyChatCancelResult('new-request'),true);
 ctx.activeChatRequest=null;
 assert.equal(ctx.mayApplyChatCancelResult('old-request'),true);
});
function functionSource(name){const start=html.indexOf('async function '+name+'(');const end=html.indexOf('\n}',start);assert.ok(start>=0&&end>start);return html.slice(start,end+2)}
test('forced typed-chat routing rechecks presence even when Gemini Live is active',async()=>{
 let calls=0;
 const ctx={liveDesired:true,voiceListening:true,localVoiceController:null,brainMode:'gemini',brainLastCheck:0,brainChecking:null,Date,
  updateBrainModeUi(){},api:async()=>{calls++;return {devices:[{device:'desktop',online:true,state:{local_chat_ready:true}}]}},
  window:{ULTRONAutoBrain:require('./static/auto-brain.js')}};
 vm.createContext(ctx);vm.runInContext(functionSource('refreshAutoBrain'),ctx);
 assert.equal(await ctx.refreshAutoBrain(true),'local');assert.equal(calls,1);
});
const transport=require('./static/chat-transport.js');
test('timeout covers stalled response body, not just response headers',async()=>{
 await assert.rejects(transport.request('/test',{timeoutMs:15},async(_url,{signal})=>({ok:true,json:()=>new Promise((_,reject)=>signal.addEventListener('abort',()=>reject(new Error('aborted'))))})),e=>e.network&&e.timeout);
});
test('caller interruption aborts transport distinctly from timeout',async()=>{
 const controller=new AbortController();let observed=false;
 const pending=transport.request('/test',{timeoutMs:1000,signal:controller.signal},async(_url,{signal})=>({
  ok:true,json:()=>new Promise((_,reject)=>{
   const abort=()=>{observed=true;reject(new Error('aborted'))};
   if(signal.aborted)abort();else signal.addEventListener('abort',abort,{once:true});
  })
 }));
 controller.abort();
 await assert.rejects(pending,e=>e.name==='AbortError');
 assert.equal(observed,true);
});
test('lost submit response retries identical ID and body, then tolerates one poll disconnect',async()=>{
 let submissions=0,polls=0,clock=0;const bodies=[];
 const result=await transport.localAnswer(async(url,opts)=>{
  if(opts.method==='POST'){bodies.push(opts.body);if(++submissions===1)throw Object.assign(new Error('lost'),{network:true});return {command_id:12}}
  if(++polls===1)throw Object.assign(new Error('reset'),{network:true});
  return {status:'completed',reply:'Synthetic reply'};
 },{request_id:'test-identity',message:'Synthetic request'},{now:()=>clock,sleep:async ms=>{clock+=ms}});
 assert.equal(result.reply,'Synthetic reply');assert.equal(submissions,2);assert.equal(new Set(bodies).size,1);assert.equal(polls,2);
});
test('accepted local request never resubmits on poll timeout and always reaches a deadline',async()=>{
 let posts=0,clock=0;
 await assert.rejects(transport.localAnswer(async(url,opts)=>{
  if(opts.method==='POST'){posts++;return {command_id:13}}
  throw Object.assign(new Error('lost'),{network:true});
 },{request_id:'test-id'},{now:()=>clock,sleep:async ms=>{clock+=ms},deadlineMs:2500}),e=>e.pending&&e.commandId===13);
 assert.equal(posts,1);assert.ok(clock<=3500);
});
test('interrupted local chat stops polling and never resubmits the accepted request',async()=>{
 const controller=new AbortController();let posts=0,polls=0,clock=0;
 const pending=transport.localAnswer(async(_url,opts)=>{
  if(opts.method==='POST'){posts++;return {command_id:14}}
  polls++;return {status:'queued'};
 },{request_id:'interrupt-id'},{signal:controller.signal,now:()=>clock,sleep:async()=>{controller.abort();clock+=1000}});
 await assert.rejects(pending,e=>e.name==='AbortError');
 assert.equal(posts,1);assert.equal(polls,0);
});
test('queue rejection and invalid provenance fail without retries',async()=>{
 for(const error of [{status:429,data:{error:'local_brain_busy'}},{status:502,data:{error:'invalid_local_reply'}}]){
  let calls=0;
  await assert.rejects(transport.localAnswer(async()=>{calls++;throw Object.assign(new Error('rejected'),error)}, {request_id:'test-id'}));
  assert.equal(calls,1);
 }
});
test('forced routing waits for a background poll then makes its own fresh check',async()=>{
 let calls=0;
 const ctx={liveDesired:false,voiceListening:false,localVoiceController:null,brainMode:'gemini',brainLastCheck:0,brainChecking:Promise.resolve('gemini'),Date,
  updateBrainModeUi(){},api:async()=>{calls++;return {devices:[{device:'desktop',online:true,state:{local_chat_ready:true}}]}},window:{ULTRONAutoBrain:require('./static/auto-brain.js')}};
 vm.createContext(ctx);vm.runInContext(functionSource('refreshAutoBrain'),ctx);
 assert.equal(await ctx.refreshAutoBrain(true),'local');assert.equal(calls,1);
});

test('unavailable readiness probe selects Gemini before any local task is submitted',async()=>{
 const ctx={liveDesired:false,voiceListening:false,localVoiceController:null,brainMode:'local',brainLastCheck:0,brainChecking:null,Date,
  updateBrainModeUi(){},api:async()=>{throw Object.assign(new Error('presence unavailable'),{network:true})},
  window:{ULTRONAutoBrain:require('./static/auto-brain.js')}};
 vm.createContext(ctx);vm.runInContext(functionSource('refreshAutoBrain'),ctx);
 assert.equal(await ctx.refreshAutoBrain(true),'gemini');
 assert.equal(ctx.brainMode,'gemini');
});

test('pending typed message remains deduplicable beyond the old 45-second voice window',()=>{
 let clock=0;const ctx={pendingVoiceMessages:[],Date:{now:()=>clock},cleanChatText:s=>s.trim()};
 vm.createContext(ctx);
 for(const name of ['rememberPendingVoice','consumePendingVoice']){
  const start=html.indexOf('function '+name+'('),end=html.indexOf('\n}',start);
  vm.runInContext(html.slice(start,end+2),ctx);
 }
 ctx.rememberPendingVoice('user','Synthetic typed request',180000);
 clock=70000;
 assert.equal(ctx.consumePendingVoice('user','Synthetic typed request'),true);
 assert.equal(ctx.consumePendingVoice('user','Synthetic typed request'),false);
});
