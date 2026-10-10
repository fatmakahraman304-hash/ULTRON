"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const playback=require("./static/live-playback.js");
const html=fs.readFileSync(path.join(__dirname,"static/index.html"),"utf8");
const sw=fs.readFileSync(path.join(__dirname,"static/sw.js"),"utf8");

test("turn_complete keeps final audio until all scheduled buffers finish",()=>{
 let drained=0;
 const output=playback.create({onDrained:()=>drained++});
 const end1=output.enqueue(),end2=output.enqueue(),end3=output.enqueue();
 assert.equal(output.pending,3);
 assert.equal(output.turnComplete(),true);
 assert.equal(drained,0);
 end1();end2();
 assert.equal(output.pending,1);
 assert.equal(drained,0);
 end3();
 assert.equal(output.pending,0);
 assert.equal(drained,1);
 end3();assert.equal(drained,1,"ended callback must be idempotent");
});

test("instant interruption invalidates previous audio and stale onended events",()=>{
 let drained=0;
 const output=playback.create({onDrained:()=>drained++});
 const old1=output.enqueue(),old2=output.enqueue();
 assert.equal(output.turnComplete(),true);
 output.cancel();
 assert.equal(output.pending,0);
 old1();old2();
 assert.equal(drained,0);
 const newTurn=output.enqueue();
 assert.equal(output.pending,1);
 assert.equal(output.turnComplete(),true);
 newTurn();
 assert.equal(drained,1);
});

test("empty response immediately goes back to listening, no lingering audio lock",()=>{
 let drained=0;
 const output=playback.create({onDrained:()=>drained++});
 assert.equal(output.turnComplete(),false);
 assert.equal(drained,1);
 output.cancel();
 assert.equal(output.complete,false);
 assert.equal(output.pending,0);
 const finish=output.enqueue();
 finish();assert.equal(drained,1);
 assert.equal(output.turnComplete(),false);
 assert.equal(drained,2);
});

test("mobile live socket drains normal endings but cancels real interruption",()=>{
 assert.match(html,/const livePlaybackState=window\.ULTRONLivePlayback\?\.create/);
 assert.match(html,/const finish=livePlaybackState\?\.enqueue\(\)/);
 assert.match(html,/src\.onended=\(\)=>\{scheduledSources\.delete\(src\);finish\?\.\(\)\}/);
 assert.match(html,/function stopPlayback\(\)\{\s*livePlaybackState\?\.cancel\(\)/);
 const start=html.indexOf("if(d.type==='turn_complete'){");
 const end=html.indexOf("if(d.type==='error')",start);
 assert.ok(start>=0&&end>start);
 const normal=html.slice(start,end);
 assert.match(normal,/livePlaybackState\?\.turnComplete\(\)/);
 assert.doesNotMatch(normal,/stopPlayback\(\)/,"normal end must not clip sound");
 const interrupted=html.slice(html.indexOf("if(d.type==='interrupted')"),start);
 assert.match(interrupted,/stopPlayback\(\)/);
 assert.match(html,/if\(bargeBlocks>=2\)\{[\s\S]{0,140}stopPlayback\(\)/);
 assert.match(html,/src\.start\(when\)/);
 assert.match(sw,/ultron-shell-v[0-9]+/);
 assert.ok(sw.includes("'/static/live-playback.js'"));
 assert.ok(html.includes('<script src="/static/live-playback.js"></script>'));
 for(const m of html.matchAll(/<script(?:\s+[^>]*)?>([\s\S]*?)<\/script>/g)){
  if(m[1].trim())assert.doesNotThrow(()=>new vm.Script(m[1]));
 }
});

test("live voice owns microphone and does not switch to browser speech synthesis",()=>{
 assert.match(html,/if\(liveDesired\|\|voiceListening\|\|liveSpeaking\)/);
 assert.match(html,/if\(remoteResultSpeaking\)return/);
 assert.match(html,/if\(!liveDesired\|\|!voiceListening\|\|!liveSocket/);
 assert.doesNotMatch(html,/setTimeout\(\(\)=>startHandsFreeVoice\(\),250\)/);
});
