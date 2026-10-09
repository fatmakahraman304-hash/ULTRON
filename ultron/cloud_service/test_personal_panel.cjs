"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const personal = require("./static/personal-panel.js");

function fakeDocument() {
  class Element {
    constructor(id = "") {
      this.id = id;
      this.children = [];
      this.listeners = {};
      this.disabled = false;
      this.textContent = "";
      this.className = "";
    }
    append(...items) { this.children.push(...items); }
    appendChild(item) { this.children.push(item); return item; }
    replaceChildren(...items) { this.children = items; }
    addEventListener(name, fn) { this.listeners[name] = fn; }
  }
  const ids = ["refreshBriefing", "briefingStatus", "briefingItems",
               "refreshReadiness", "readinessStatus", "readinessItems"];
  const items = Object.fromEntries(ids.map(id => [id, new Element(id)]));
  return {
    createElement() { return new Element(); },
    getElementById(id) { return items[id] || null; },
    items,
  };
}
test("briefing entries retain only explicitly provided saved records", () => {
  const values = personal.briefingEntries({
    items: [{key: "B2 İngilizce", value: "Her gün çalış", category: "GOAL", source: "owner_saved_memory"},
            {key: " ", value: "empty"}],
  });
  assert.equal(values.length, 1);
  assert.equal(values[0].source, "ULTRON hafızası");
});
test("capabilities are not all presented as available", () => {
  const values = personal.capabilityEntries({capabilities: [
    {name:"Fiziksel hologram",status:"blocked_hardware",detail:"Özel cihaz gerekli"},
    {name:"iPhone",status:"requires_native_setup",detail:"İzin gerekli"},
  ]});
  assert.equal(values[0].status, "Donanım gerekiyor");
  assert.equal(values[1].status, "iOS kurulumu gerekiyor");
});
test("panel does not fetch anything until explicit button click", async () => {
  const doc = fakeDocument(), calls = [];
  const view = personal.create({document:doc, fetchJson: async url => {
    calls.push(url);
    if (url === "/api/personal-briefing") return {items:[{key:"Hedef",value:"Kod test et",category:"GOAL",source:"owner_saved_memory"}]};
    if (url === "/api/capability-readiness") return {desktop_online:false,capabilities:[{name:"Laptop",status:"blocked_hardware",detail:"Kapalı"}]};
    throw Error("unexpected_url");
  }});
  assert.equal(view.init(),true);
  assert.deepEqual(calls,[]);
  await doc.items.refreshBriefing.listeners.click();
  assert.deepEqual(calls,["/api/personal-briefing"]);
  assert.equal(doc.items.briefingItems.children.length,1);
  assert.equal(doc.items.briefingItems.children[0].children[1].textContent,"Kod test et");
  await doc.items.refreshReadiness.listeners.click();
  assert.deepEqual(calls,["/api/personal-briefing","/api/capability-readiness"]);
  assert.match(doc.items.readinessStatus.textContent,/çevrimdışı/);
  assert.equal(doc.items.refreshReadiness.disabled,false);
});
test("injected HTML is never passed to an HTML parsing sink", async () => {
  const doc=fakeDocument();
  const payload={items:[{key:"<img src=x onerror=alert(1)>",value:"<script>evil()</script>",source:"owner_saved_memory"}]};
  const view=personal.create({document:doc,fetchJson:async()=>payload});
  view.init();
  await doc.items.refreshBriefing.listeners.click();
  const card=doc.items.briefingItems.children[0];
  assert.equal(card.children[0].textContent,"<img src=x onerror=alert(1)>");
  assert.equal(card.children[1].textContent,"<script>evil()</script>");
  assert.equal(card.children.length,3);
  assert.equal(fs.readFileSync(path.join(__dirname,"static/personal-panel.js"),"utf8").includes(".innerHTML"),false);
});
test("errors show only as status and buttons recover", async () => {
  const doc=fakeDocument();
  const view=personal.create({document:doc,fetchJson:async()=>{throw Error("network problem")}});
  view.init();
  await doc.items.refreshBriefing.listeners.click();
  assert.match(doc.items.briefingStatus.textContent,/network problem/);
  assert.equal(doc.items.refreshBriefing.disabled,false);
  assert.deepEqual(doc.items.briefingItems.children,[]);
});
test("iPhone page includes buttons, module and explicit init hook", () => {
  const html=fs.readFileSync(path.join(__dirname,"static/index.html"),"utf8");
  assert.ok(html.includes('id="refreshBriefing"'));
  assert.ok(html.includes('id="refreshReadiness"'));
  assert.ok(html.includes('<script src="/static/personal-panel.js"></script>'));
  assert.ok(html.includes('ULTRONPersonalPanel?.create({fetchJson: path => api(path), document}).init()'));
});
