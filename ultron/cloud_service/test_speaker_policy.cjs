"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const policy=require("./static/speaker-policy.js");
const html=fs.readFileSync(path.join(__dirname,"static/index.html"),"utf8");
const sw=fs.readFileSync(path.join(__dirname,"static/sw.js"),"utf8");

test("only confirmed active, unmuted desktop can claim speaker",()=>{
 const speaking={speaking:true,voice_active:true,voice_output:true,muted:false};
 assert.equal(policy.desktopMayLead(true,speaking,{}),true);
 for(const desktop of [false,undefined,"true",null])
  assert.equal(policy.desktopMayLead(desktop,speaking,{}),false);
 for(const state of [
  {speaking:"true",voice_active:true,voice_output:true},
  {speaking:true,voice_active:"yes",voice_output:true},
  {speaking:false,voice_active:true,voice_output:true},
  {speaking:true,voice_active:false,voice_output:true},
  {speaking:true,voice_active:true,voice_output:false},
  {speaking:true,voice_active:true,muted:true},
  {},null
 ])assert.equal(policy.desktopMayLead(true,state,{}),false);
});

test("phone Gemini Live OR local Qwen microphone always wins",()=>{
 const desktop={speaking:true,voice_active:true,voice_output:true,muted:false};
 for(const phone of [
  {liveDesired:true},
  {voiceListening:true},
  {localVoiceActive:true},
  {liveDesired:true,localVoiceActive:true},
 ]){
  assert.equal(policy.phoneOwnsVoice(phone),true);
  assert.equal(policy.desktopMayLead(true,desktop,phone),false);
 }
 assert.equal(policy.desktopMayLead(true,desktop,{localVoiceActive:false}),true);
 assert.equal(policy.phoneOwnsVoice({localVoiceActive:"true"}),false);
});

test("desktop task speech never overlaps an already-leading laptop voice",()=>{
 const start=html.indexOf("function speakRemoteResult(");
 const end=html.indexOf("function setVoiceEnabled(",start);
 assert.ok(start>=0&&end>start);
 const fn=html.slice(start,end);
 assert.match(fn,/if\(liveDesired\|\|voiceListening\|\|liveSpeaking\|\|desktopVoiceLeader\)/);
 assert.match(fn,/speechSynthesis\.cancel\(\)/);
 assert.match(fn,/resetRemoteResultSpeech\(\)/);
 assert.ok(fn.indexOf("desktopVoiceLeader")<fn.indexOf("speechSynthesis.speak(u)"));
});

test("handoff stops prior playback and clears cancelled phone TTS locks",()=>{
 const start=html.indexOf("function setDesktopVoiceLeader(");
 const end=html.indexOf("async function watchDesktopPresence(",start);
 const fn=html.slice(start,end);
 assert.match(fn,/if\(active\)\{\s*stopPlayback\(\)/);
 assert.match(fn,/speechSynthesis\.cancel\(\)/);
 assert.match(fn,/resetRemoteResultSpeech\(\)/);
 assert.match(fn,/updateBrainModeUi\(\)/);
});

test("a late/out-of-order desktop presence response never overrides newer state",()=>{
 const start=html.indexOf("async function watchDesktopPresence(");
 const end=html.indexOf("async function loadRemoteState(",start);
 assert.ok(start>=0&&end>start);
 const block=html.slice(start,end);
 assert.match(block,/seq=\+\+desktopPresenceRequestSeq/);
 assert.match(block,/if\(seq!==desktopPresenceRequestSeq\)return/);
 assert.ok(block.indexOf("if(seq!==desktopPresenceRequestSeq)return") <
  block.indexOf("setDesktopVoiceLeader(laptopCanSpeak)"));
 assert.match(block,/localVoiceActive:localVoiceController\?\.active\(\)===true/);
 assert.match(block,/ULTRONSpeakerPolicy\.desktopMayLead/);
});

test("speaker policy is cached with PWA and adds no visible menu",()=>{
 assert.match(sw,/ultron-shell-v[0-9]+/);
 assert.ok(sw.includes("'/static/speaker-policy.js'"));
 assert.ok(html.includes('<script src="/static/speaker-policy.js"></script>'));
 assert.doesNotMatch(html,/id="speakerModePicker"/);
 const inline=[...html.matchAll(/<script(?:\s+[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(m=>m[1]).filter(x=>x.trim());
 for(const js of inline)assert.doesNotThrow(()=>new vm.Script(js));
});
