"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const guard=require("./static/voice-turn-guard.js");
const html=fs.readFileSync(path.join(__dirname,"static/index.html"),"utf8");
const sw=fs.readFileSync(path.join(__dirname,"static/sw.js"),"utf8");

test("a new phone mic turn cancels stale answers without cancelling their text",()=>{
 const current=guard.create();
 const first=current.begin();
 assert.equal(current.current(first),true);
 current.cancel(); // user tapped mic again during long Qwen reply
 assert.equal(current.current(first),false);
 const second=current.begin();
 assert.equal(current.current(first),false);
 assert.equal(current.current(second),true);
 current.cancel(); // mute, background or pagehide
 assert.equal(current.current(second),false);
});

test("stale timers, invalid and guessed tokens cannot revive a cancelled turn",()=>{
 const local=guard.create();
 const id=local.begin();
 for(const candidate of [null,undefined,"1",0,-1,1.5,NaN,Infinity,{},[]])
  assert.equal(local.current(candidate),false);
 assert.equal(local.current(id),true);
 local.cancel();local.cancel();
 assert.equal(local.current(id),false);
 const fresh=local.begin();
 assert.equal(local.current(fresh),true);
});

test("PWA voice microphone click interrupts browser TTS before starting local STT",()=>{
 const start=html.indexOf("$('#voiceBtn').onclick=async()=>");
 const end=html.indexOf("$('#plusBtn').onclick",start);
 assert.ok(start>=0&&end>start);
 const click=html.slice(start,end);
 assert.match(click,/if\(localVoiceController\?\.active\(\)\)/);
 assert.match(click,/voiceTurnGuard\.cancel\(\)/);
 assert.match(click,/speechSynthesis\.cancel\(\)/);
 assert.ok(click.indexOf("speechSynthesis.cancel()")<click.lastIndexOf("localVoiceController?.toggle()"));
 assert.match(click,/const preferred=await refreshAutoBrain\(true\)/);
});

test("stale Qwen reply stays in chat but never speaks after cancelled voice turn",()=>{
 assert.match(html,/const voiceToken=voiceTurnGuard\.begin\(\)/);
 assert.match(html,/await send\(true,voiceToken\)/);
 assert.match(html,/async function send\(fromVoice=false,voiceToken=null\)/);
 assert.match(html,/rememberPendingVoice\('assistant',d\.reply\);addMessage\('assistant',d\.reply\);/);
 assert.match(html,/voiceTurnGuard\.current\(voiceToken\)/);
 assert.match(html,/!fromVoice\|\|!document\.hidden/);
 assert.match(html,/if\(!fromVoice\)voiceTurnGuard\.cancel\(\)/);
 assert.match(html,/if\(!voiceEnabled\)\{voiceTurnGuard\.cancel\(\)/);
});

test("background, pagehide and mute invalidate turns without background mic access",()=>{
 assert.match(html,/pagehide',\(\)=>\{voiceTurnGuard\.cancel\(\)/);
 assert.match(html,/if\(document\.hidden\)\{voiceTurnGuard\.cancel\(\)/);
 assert.match(sw,/ultron-shell-v[0-9]+/);
 assert.ok(sw.includes("'/static/voice-turn-guard.js'"));
 assert.ok(html.includes('<script src="/static/voice-turn-guard.js"></script>'));
 assert.doesNotMatch(html,/setTimeout\(\(\)=>startHandsFreeVoice\(\),250\)/);
 const scripts=[...html.matchAll(/<script(?:\s+[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(x=>x[1]).filter(s=>s.trim());
 for(const source of scripts)assert.doesNotThrow(()=>new vm.Script(source));
});
