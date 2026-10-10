"use strict";
const {test}=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const parser=require("./static/panel-intents.js");
const html=fs.readFileSync(path.join(__dirname,"static/index.html"),"utf8");
const sw=fs.readFileSync(path.join(__dirname,"static/sw.js"),"utf8");
test("Turkish natural-language requests summon panels, not permanent buttons",()=>{
  const checks=[
    ["Dünyayı aç","world"],["Haritayı göster","world"],
    ["Depremleri göster","world"],["Hologram Lab'i aç","hologram"],
    ["Hologram çalışma alanını getir","hologram"],
    ["Hafızamı göster","memory"],["Takvimi aç","memory"],
    ["Uzaktan kontrolü aç","remote"],["Geliştir panelini aç","develop"],
    ["Sohbeti aç","chat"],["Ana ekrana dön","chat"],
    ["Paneli kapat","chat"],
  ];
  for(const [input,expected] of checks)assert.equal(parser.resolve(input)?.view,expected,input);
});
test("ordinary chat remains chat and never launches tools or panels",()=>{
  for(const phrase of ["Dünyanın yaşı ne?","Hologram nasıl yapılır?",
    "Hologram video yap","Bugün neler yapabilirim?","Terminalde hata var",
    "Dünyayı kapatmak mümkün mü?", "", " ".repeat(20)])
    assert.equal(parser.resolve(phrase),null,phrase);
});
test("mobile routes typed messages and Live voice transcripts into same UI dispatcher",()=>{
  assert.match(html,/handlePanelIntent\(heard\)/);
  assert.match(html,/const panelHandled=handlePanelIntent\(text\)/);
  assert.match(html,/if\(!worldVoiceIntent\(text\)\)showView\('world'\)/);
  assert.match(html,/<section id="hologramView"/);
  assert.match(html,/id="closeMobileHologram"/);
  assert.match(html,/id="panelMenuToggle"/);
  assert.match(html,/panel-nav-open/);
  assert.match(html,/\.tabs:not\(\.panel-nav-open\)\{opacity:0!important/);
  assert.match(html,/\$\('#panelMenuToggle'\)\.onclick/);
  assert.match(html,/<script src="\/static\/panel-intents.js"><\/script>/);
  assert.match(sw,/\'\/static\/panel-intents\.js\'/);
});
test("mobile inline JS stays valid after new command dispatch and on-demand panels",()=>{
  const scripts=[...html.matchAll(/<script(?:\s+[^>]*)?>([\s\S]*?)<\/script>/g)].map(x=>x[1]).filter(Boolean);
  assert.ok(scripts.length);
  for(const source of scripts)assert.doesNotThrow(()=>new vm.Script(source));
});
