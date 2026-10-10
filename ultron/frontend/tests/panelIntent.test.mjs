import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {resolvePanelIntent} from "../src/dashboard/panelIntent.ts";
test("desktop natural voice/text commands open workspace and go home",()=>{
 const cases=[
  ["Dünyayı aç","world"],["3D dünya göster","world"],["Haritayı aç","world"],
  ["Hologram Lab aç","hologram"],["Hologram çalışma alanını aç","hologram"],
  ["Hafızamı göster","memory"],["Uzaktan kontrolü aç","remote"],
  ["Geliştirme panelini aç","develop"],["Araçları göster","tools"],
  ["Ayarları aç","settings"],["Ana ekrana dön","chat"],["Paneli kapat","chat"]
 ];
 for(const [input,result] of cases)assert.equal(resolvePanelIntent(input),result,input);
});
test("normal conversation is not intercepted",()=>{
 for(const input of ["Dünya kaç yaşında?","3D hologram nedir?",
    "Hologram oluştur","Dünya dosyalarını sil","Kapatınca ne olur?",""])
   assert.equal(resolvePanelIntent(input),null,input);
});
test("desktop actually hides extra chrome and uses React HologramLab on command",()=>{
 const jsx=fs.readFileSync(new URL("../src/dashboard/Dashboard.tsx",import.meta.url),"utf8");
 const css=fs.readFileSync(new URL("../src/dashboard/dashboard.css",import.meta.url),"utf8");
 assert.match(jsx,/resolvePanelIntent\(text\)/);
 assert.match(jsx,/setHologram\(true\)/);
 assert.match(jsx,/voiceRouteSeen/);
 assert.match(jsx,/voice-first-menu/);
 assert.match(jsx,/voice-first-mic/);
 assert.match(css,/\.ultron-app\.voice-first \.main-header nav,\.ultron-app\.voice-first \.bottom-toolbar\{display:none\}/);
 assert.match(css,/\.ultron-app\.voice-first \.system-rail\{display:none\}/);
});
