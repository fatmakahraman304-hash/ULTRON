"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const plans = require("./static/owner-plans.js");

function fakeDOM() {
  class Node {
    constructor() { this.children=[]; this.listeners={}; this.textContent=""; this.value=""; this.disabled=false; this.className=""; this.classList={ add:()=>{}, remove:()=>{} }; }
    focus() {}
    append(...nodes) { this.children.push(...nodes); }
    appendChild(node) { this.children.push(node); return node; }
    replaceChildren(...nodes) { this.children=nodes; }
    addEventListener(event, fn) { this.listeners[event]=fn; }
  }
  const ids = ["refreshOwnerPlans","saveOwnerPlan","ownerPlansStatus","ownerPlansList",
               "planTitle","planDate","planTime","planNote","cancelPlanEdit"];
  const elements=Object.fromEntries(ids.map(id=>[id,new Node()]));
  return {document:{getElementById:id=>elements[id]||null,createElement:()=>new Node()},elements};
}
test("only explicit click triggers API and renders user plan using textContent", async()=>{
  const {document,elements}=fakeDOM(), calls=[];
  const view=plans.create({document,fetchJson:async(url,opt)=>{
    calls.push({url,opt});
    if(url==="/api/owner-plans")return {plans:[{id:7,title:"<svg onload=evil()>",scheduled_date:"2026-10-10",scheduled_time:"12:00",note:"<script>evil()</script>",is_done:false}]};
    throw Error("unexpected "+url);
  }});
  assert.equal(view.init(),true);
  assert.deepEqual(calls,[]);
  await elements.refreshOwnerPlans.listeners.click();
  assert.equal(calls.length,1);
  const card=elements.ownerPlansList.children[0];
  assert.equal(card.children[0].textContent,"<svg onload=evil()>");
  assert.match(card.children[1].textContent,/<script>evil/);
  assert.equal(fs.readFileSync(path.join(__dirname,"static/owner-plans.js"),"utf8").includes(".innerHTML"),false);
});
test("user saving manually posts selected date and does not auto-register a reminder", async()=>{
  const {document,elements}=fakeDOM(), calls=[];
  elements.planTitle.value="Çalışma"; elements.planDate.value="2026-10-12";
  elements.planTime.value="16:30"; elements.planNote.value="B2";
  const view=plans.create({document,fetchJson:async(url,opt)=>{
    calls.push({url,opt});
    return url==="/api/owner-plans"&&opt?.method==="POST"
      ? {plan:{id:8,notification_sent:false}} : {plans:[]};
  }});
  view.init();
  await elements.saveOwnerPlan.listeners.click();
  assert.equal(calls[0].opt.method,"POST");
  assert.deepEqual(JSON.parse(calls[0].opt.body),{title:"Çalışma",date:"2026-10-12",time:"16:30",note:"B2"});
  assert.equal(calls[1].url,"/api/owner-plans");
  assert.equal(elements.planTitle.value,"");
});
test("completion toggles via owner button and delete requires confirmation", async()=>{
  const {document,elements}=fakeDOM(), calls=[];
  const entry={id:42,title:"Ders",scheduled_date:"2026-10-13",scheduled_time:null,is_done:false};
  let confirm=false;
  const view=plans.create({document,confirmDelete:()=>confirm,fetchJson:async(url,opt)=>{
    calls.push({url,opt});
    if(opt?.method==="PATCH"||opt?.method==="DELETE")return {};
    return {plans:[entry]};
  }});
  view.init();
  await elements.refreshOwnerPlans.listeners.click();
  let controls=elements.ownerPlansList.children[0].children[3];
  await controls.children[2].listeners.click();
  assert.equal(calls.length,1,"rejected deletion must not call API");
  confirm=true;
  await controls.children[2].listeners.click();
  assert.equal(calls[1].opt.method,"DELETE");
  controls=elements.ownerPlansList.children[0].children[3];
  await controls.children[1].listeners.click();
  assert.equal(calls[3].opt.method,"PATCH");
  assert.deepEqual(JSON.parse(calls[3].opt.body),{is_done:true});
});
test("editing a plan populates form; PUT happens only on explicit save", async()=>{
  const {document,elements}=fakeDOM(), calls=[];
  const original={id:77,title:"Eski ders",scheduled_date:"2026-10-20",scheduled_time:"11:00",note:"A dersliği",is_done:false};
  const view=plans.create({document,fetchJson:async(url,opt)=>{
    calls.push({url,opt});
    return opt?.method==="PUT" ? {plan:{...original}} : {plans:[original]};
  }});
  view.init();
  await elements.refreshOwnerPlans.listeners.click();
  const controls=elements.ownerPlansList.children[0].children[3];
  await controls.children[0].listeners.click();
  assert.equal(calls.length,1,"editing must not write until Save");
  assert.equal(elements.planTitle.value,"Eski ders");
  assert.equal(elements.planTime.value,"11:00");
  assert.equal(elements.planNote.value,"A dersliği");
  assert.equal(elements.saveOwnerPlan.textContent,"DEĞİŞİKLİKLERİ KAYDET");
  elements.planTitle.value="Yeni ders"; elements.planDate.value="2026-10-24"; elements.planTime.value="18:30";
  await elements.saveOwnerPlan.listeners.click();
  assert.equal(calls[1].url,"/api/owner-plans/77");
  assert.equal(calls[1].opt.method,"PUT");
  assert.deepEqual(JSON.parse(calls[1].opt.body),
      {title:"Yeni ders",date:"2026-10-24",time:"18:30",note:"A dersliği"});
  assert.equal(elements.saveOwnerPlan.textContent,"PLANI KAYDET");
});
test("cancel editing does not write or modify stored plan", async()=>{
  const {document,elements}=fakeDOM(), calls=[];
  const p={id:78,title:"Plan",scheduled_date:"2026-10-20",note:"sır",is_done:false};
  const view=plans.create({document,fetchJson:async(url,opt)=>{calls.push({url,opt});return {plans:[p]}}});
  view.init();await elements.refreshOwnerPlans.listeners.click();
  await elements.ownerPlansList.children[0].children[3].children[0].listeners.click();
  elements.planNote.value="gizli yeni not";
  await elements.cancelPlanEdit.listeners.click();
  assert.equal(calls.length,1);
  assert.equal(elements.planNote.value,"");
  assert.equal(elements.saveOwnerPlan.textContent,"PLANI KAYDET");
});
test("failed edit preserves unsaved values for correction without falsely succeeding", async()=>{
  const {document,elements}=fakeDOM(),calls=[];
  const p={id:99,title:"Plan",scheduled_date:"2026-11-09",note:"not",is_done:false};
  const view=plans.create({document,fetchJson:async(url,opt)=>{
    calls.push({url,opt});
    if(opt?.method==="PUT")throw Error("server offline");
    return {plans:[p]};
  }});
  view.init();await elements.refreshOwnerPlans.listeners.click();
  await elements.ownerPlansList.children[0].children[3].children[0].listeners.click();
  elements.planTitle.value="Korunan değişiklik";
  await elements.saveOwnerPlan.listeners.click();
  assert.equal(calls.length,2);
  assert.match(elements.ownerPlansStatus.textContent,/server offline/);
  assert.equal(elements.planTitle.value,"Korunan değişiklik");
  assert.equal(elements.saveOwnerPlan.textContent,"DEĞİŞİKLİKLERİ KAYDET");
});
test("invalid input does not make network request", async()=>{
  const {document,elements}=fakeDOM(), calls=[];
  const view=plans.create({document,fetchJson:async (...args)=>{calls.push(args);return {plans:[]}}});
  view.init();
  await elements.saveOwnerPlan.listeners.click();
  assert.deepEqual(calls,[]);
  assert.match(elements.ownerPlansStatus.textContent,/gerekli/);
});
test("mobile UI has manual calendar fields, cache and initializer",()=>{
  const html=fs.readFileSync(path.join(__dirname,"static/index.html"),"utf8");
  const sw=fs.readFileSync(path.join(__dirname,"static/sw.js"),"utf8");
  for(const id of ["planTitle","planDate","planTime","planNote","saveOwnerPlan","cancelPlanEdit","refreshOwnerPlans","ownerPlansList"])
    assert.ok(html.includes('id="'+id+'"'),id);
  assert.ok(html.includes('ULTRONOwnerPlans?.create'));
  assert.ok(html.includes('<script src="/static/owner-plans.js"></script>'));
  assert.ok(sw.includes("'/static/owner-plans.js'"));
});
