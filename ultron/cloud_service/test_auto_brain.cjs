"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const router=require("./static/auto-brain.js");
const html=fs.readFileSync(path.join(__dirname,"static/index.html"),"utf8");
const sw=fs.readFileSync(path.join(__dirname,"static/sw.js"),"utf8");
test("local only for currently online paired desktop, never just stale last_seen",()=>{
 assert.equal(router.select([]),"gemini");
 assert.equal(router.select(null),"gemini");
 assert.equal(router.select([{device:"desktop",online:false}]),"gemini");
 assert.equal(router.select([{device:"phone",online:true}]),"gemini");
 assert.equal(router.select([{device:"desktop",online:"true"}]),"gemini");
 assert.equal(router.select([{device:"desktop",online:true}]),"local");
 assert.equal(router.select([{device:"phone",online:true},{device:"desktop",online:true}]),"local");
});
test("fallback replays only confirmed offline rejection made before queue creation",()=>{
 assert.equal(router.safeToFallback({status:409,data:{error:"desktop_offline"}}),true);
 for(const error of [
   {status:429,data:{error:"local_brain_busy"}},
   {status:502,data:{error:"invalid_model"}},
   {status:409,data:{error:"some_other_error"}},
   {network:true},new Error("timeout"),null
 ])assert.equal(router.safeToFallback(error),false);
});
test("main input hides provider tech, no manual picker, locally routes or cloud fallback",()=>{
 assert.doesNotMatch(html,/<div class="brain-picker">/);
 assert.doesNotMatch(html,/id="brainMode"/);
 assert.doesNotMatch(html,/ULTRON BEYİN/);
 assert.doesNotMatch(html,/GEMINI • İSTEĞE BAĞLI/);
 assert.match(html,/async function refreshAutoBrain\(force=false\)/);
 assert.match(html,/brainMode=window\.ULTRONAutoBrain\.select\(response\.devices\)/);
 assert.match(html,/const preferred=await refreshAutoBrain\(true\)/);
 assert.match(html,/if\(!window\.ULTRONAutoBrain\.safeToFallback\(e\)\)throw e/);
 assert.match(html,/d=await cloud\(\)/);
 assert.match(html,/id="voiceBtn"/);
 assert.match(html,/id="message"/);
 assert.match(html,/id="sendBtn"/);
 assert.match(sw,/ultron-shell-v50/);
 assert.match(sw,/\/static\/auto-brain\.js/);
});
test("no background microphone or cloud handoff on page load",()=>{
 assert.doesNotMatch(html,/setTimeout\(\(\)=>startHandsFreeVoice\(\),\s*\d+\)/);
 assert.match(html,/\$\('#voiceBtn'\)\.onclick=async\(\)=>/);
 const scripts=[...html.matchAll(/<script(?:\s+[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).filter(Boolean);
 assert.ok(scripts.length);
 for(const script of scripts)assert.doesNotThrow(()=>new vm.Script(script));
});
