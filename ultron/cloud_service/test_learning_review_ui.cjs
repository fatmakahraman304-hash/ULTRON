"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const moduleUi=require("./static/learning-review.js");
function fakeDOM(){
 class Node{
  constructor(){this.children=[];this.listeners={};this.textContent="";this.value="";this.disabled=false;}
  append(...items){this.children.push(...items);}
  appendChild(x){this.children.push(x);return x;}
  replaceChildren(...items){this.children=items;}
  addEventListener(key,fn){this.listeners[key]=fn;}
 }
 const ids=["learningCategory","learningKey","learningValue","learningStatus","learningItems","submitLearning","refreshLearning"];
 const items=Object.fromEntries(ids.map(x=>[x,new Node()]));
 return {document:{getElementById:id=>items[id]||null,createElement:()=>new Node()},items};
}
test("learning never invokes API without explicit user clicks",async()=>{
 const {document,items}=fakeDOM(),calls=[];
 const view=moduleUi.create({document,fetchJson:async(url,opt)=>{calls.push({url,opt});return {proposals:[]}}});
 assert.equal(view.init(),true);
 assert.equal(calls.length,0);
 await items.refreshLearning.listeners.click();
 assert.deepEqual(calls.map(c=>c.url),["/api/learning-proposals"]);
});
test("suggesting is not approval, and approval is an additional direct click",async()=>{
 const {document,items}=fakeDOM(),calls=[];
 const proposal={id:9,category:"PREFERENCE",key:"Ton",value:"Ciddi konuş",status:"pending"};
 let memoryCount=0;
 items.learningCategory.value="PREFERENCE";items.learningKey.value="Ton";items.learningValue.value="Ciddi konuş";
 const view=moduleUi.create({document,fetchJson:async(url,opt)=>{
  calls.push({url,opt});return opt?.method==="POST" && url==="/api/learning-proposals"
    ? {proposal,memory_saved:false}:{proposals:[proposal]};
 },onMemoryChanged:async()=>memoryCount++});
 view.init();
 await items.submitLearning.listeners.click();
 assert.equal(calls[0].url,"/api/learning-proposals");
 assert.equal(calls[0].opt.method,"POST");
 assert.equal(memoryCount,0);
 const controls=items.learningItems.children[0].children[3];
 await controls.children[0].listeners.click();
 assert.equal(calls[2].url,"/api/learning-proposals/9/decision");
 assert.deepEqual(JSON.parse(calls[2].opt.body),{approve:true});
 assert.equal(memoryCount,1);
});
test("reject and delete use explicit controls, delete requires confirmation",async()=>{
 const {document,items}=fakeDOM(),calls=[];
 let confirm=false;
 const proposal={id:6,category:"GOAL",key:"Plan",value:"<img src=x onerror=evil()>",status:"pending"};
 const view=moduleUi.create({document,confirmRemove:()=>confirm,
 fetchJson:async(url,opt)=>{calls.push({url,opt});return {proposals:[proposal]}}});
 view.init();await items.refreshLearning.listeners.click();
 const card=items.learningItems.children[0];
 assert.equal(card.children[1].textContent,proposal.value);
 assert.equal(fs.readFileSync(path.join(__dirname,"static/learning-review.js"),"utf8").includes(".innerHTML"),false);
 const controls=card.children[3];
 await controls.children[2].listeners.click();
 assert.equal(calls.length,1);
 await controls.children[1].listeners.click();
 assert.deepEqual(JSON.parse(calls[1].opt.body),{approve:false});
 confirm=true;await controls.children[2].listeners.click();
 assert.equal(calls[3].opt.method,"DELETE");
});
test("new mobile panel, script and PWA shell are wired",()=>{
 const html=fs.readFileSync(path.join(__dirname,"static/index.html"),"utf8");
 const sw=fs.readFileSync(path.join(__dirname,"static/sw.js"),"utf8");
 for(const id of ["learningCategory","learningKey","learningValue","learningStatus","learningItems","submitLearning","refreshLearning"])
  assert.ok(html.includes('id="'+id+'"'),id);
 assert.ok(html.includes('ULTRONLearningReview?.create'));
 assert.ok(html.includes('/static/learning-review.js'));
 assert.ok(sw.includes("'/static/learning-review.js'"));
});
