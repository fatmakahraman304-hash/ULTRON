"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const learning=require("./static/learning-review.js");
function fixture(){
  class N{
    constructor(){this.children=[];this.listeners={};this.textContent="";this.value="";this.disabled=false;}
    addEventListener(k,fn){this.listeners[k]=fn}
    append(...args){this.children.push(...args)}
    appendChild(c){this.children.push(c);return c}
    replaceChildren(...args){this.children=args}
  }
  const ids=["submitLearning","refreshLearning","learningStatus","learningItems","learningKey",
    "learningValue","learningCategory","autoLearningToggle","autoLearningStatus"];
  const nodes=Object.fromEntries(ids.map(id=>[id,new N()]));
  return {nodes,doc:{getElementById:id=>nodes[id]||null,createElement:()=>new N()}};
}
test("learning is OFF until user loads setting and explicitly enables it",async()=>{
 const {nodes,doc}=fixture(), calls=[];
 const ui=learning.create({document:doc,confirmRemove:()=>true,
 fetchJson:async(path,opts)=>{
   calls.push([path,opts]);
   if(opts?.method==="PUT")return {enabled:true};
   return {enabled:false};
 }});
 ui.init();
 assert.equal(calls.length,0);
 await nodes.autoLearningToggle.listeners.click();
 assert.deepEqual(calls.map(x=>x[0]),["/api/auto-learning"]);
 assert.match(nodes.autoLearningStatus.textContent,/KAPALI/);
 await nodes.autoLearningToggle.listeners.click();
 assert.equal(calls[1][1].method,"PUT");
 assert.deepEqual(JSON.parse(calls[1][1].body),{enabled:true});
 assert.match(nodes.autoLearningStatus.textContent,/AÇIK/);
});
test("owner can deny enabling and turn it back off without another approval",async()=>{
 const {nodes,doc}=fixture(),calls=[];
 let consent=false,enabled=false;
 const ui=learning.create({document:doc,confirmRemove:()=>consent,
 fetchJson:async(path,opts)=>{
  calls.push([path,opts]);
  if(opts?.method==="PUT"){enabled=JSON.parse(opts.body).enabled;return {enabled};}
  return {enabled};
 }});
 ui.init();
 await nodes.autoLearningToggle.listeners.click();
 await nodes.autoLearningToggle.listeners.click();
 assert.equal(calls.length,1);
 consent=true;
 await nodes.autoLearningToggle.listeners.click();
 await nodes.autoLearningToggle.listeners.click();
 assert.deepEqual(JSON.parse(calls[2][1].body),{enabled:false});
 assert.match(nodes.autoLearningStatus.textContent,/KAPALI/);
});
test("auto-learning settings and code are bundled in iPhone shell",()=>{
 const html=fs.readFileSync(path.join(__dirname,"static/index.html"),"utf8");
 const js=fs.readFileSync(path.join(__dirname,"static/learning-review.js"),"utf8");
 assert.ok(html.includes('id="autoLearningToggle"'));
 assert.ok(html.includes('id="autoLearningStatus"'));
 assert.ok(html.includes("Tercihim:"));
 assert.ok(js.includes('"/api/auto-learning"'));
 assert.ok(!js.includes(".innerHTML"));
});
