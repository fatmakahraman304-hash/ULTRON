import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {resolvePanelIntent} from "../src/dashboard/panelIntent.ts";
test("desktop natural voice/text commands open workspace and go home",()=>{
 const cases=[
  ["Dünyayı aç","world"],["3D dünya göster","world"],["Haritayı aç","world"],
  ["GÖLGE kontrol merkezini aç","control-center"],["Kontrol panelini göster","control-center"],
  ["Hologram Lab aç","hologram"],["Hologram çalışma alanını aç","hologram"],
  ["Hafızamı göster","memory"],["Uzaktan kontrolü aç","remote"],
  ["Geliştirme panelini aç","develop"],["Araçları göster","tools"],
  ["Ayarları aç","settings"],["Ana ekrana dön","chat"],["Paneli kapat","chat"],
  ["GÖLGE, normal moda dön.","chat"],["Normal moda dön","chat"],["Sohbet ekranına dön","chat"]
 ];
 for(const [input,result] of cases)assert.equal(resolvePanelIntent(input),result,input);
});
test("normal conversation is not intercepted",()=>{
 for(const input of ["Dünya kaç yaşında?","3D hologram nedir?",
    "Hologram oluştur","Dünya dosyalarını sil","Kontrol merkezi nedir?","Kapatınca ne olur?",""])
   assert.equal(resolvePanelIntent(input),null,input);
});
test("mobile and desktop share the same conversation intent routing",()=>{
 const jsx=fs.readFileSync(new URL("../src/dashboard/Dashboard.tsx",import.meta.url),"utf8");
 const reactCss=fs.readFileSync(new URL("../src/dashboard/golge-control-center.css",import.meta.url),"utf8");
 const mobileCss=fs.readFileSync(new URL("../../cloud_service/static/golge-reference-mobile.css",import.meta.url),"utf8");
 const control=fs.readFileSync(new URL("../src/dashboard/ControlCenter.tsx",import.meta.url),"utf8");
 assert.match(jsx,/w==='control-center'/);
 assert.match(jsx,/matchMedia\('\(max-width:840px\)'\)/);
 assert.match(jsx,/ControlCenter/);
 assert.match(jsx,/!isMobile&&/);
 assert.match(reactCss,/position:fixed;inset:0;z-index:0;background:#03080d url\('\/golge-night-lake\.webp'\)/);
 assert.match(mobileCss,/position:fixed!important;inset:0!important/);
 assert.match(mobileCss,/\/static\/golge-night-lake\.webp/);
 assert.match(control,/system\?\.cpu\?\.percent/);
 assert.match(control,/devicePresence\.find/);
 assert.match(control,/notifications\.slice/);
 assert.match(control,/Kullanılamıyor/);
 assert.doesNotMatch(control,/request\(/);
});
test("desktop actually hides extra chrome and uses React HologramLab on command",()=>{
 const jsx=fs.readFileSync(new URL("../src/dashboard/Dashboard.tsx",import.meta.url),"utf8");
 const css=fs.readFileSync(new URL("../src/dashboard/dashboard.css",import.meta.url),"utf8");
 assert.match(jsx,/resolvePanelIntent\(text\)/);
 assert.match(jsx,/setHologram\(true\)/);
 assert.match(jsx,/voiceRouteSeen/);
 assert.match(jsx,/voice-first-menu/);
 assert.match(jsx,/voice-first-mic/);
 assert.match(jsx,/coreCaption=state===\'LISTENING\'/);
 assert.match(jsx,/\'THINKING\'\?\'Yanıt hazırlıyorum/);
 assert.match(jsx,/\'SPEAKING\'\?\'Konuşuyorum/);
 assert.match(jsx,/Sesli giriş açık/);
 assert.match(css,/\.ultron-app\.voice-first \.main-header nav,\.ultron-app\.voice-first \.bottom-toolbar\{display:none\}/);
 assert.match(css,/\.ultron-app\.voice-first \.system-rail\{display:none\}/);
});
test("visible dashboard, scene, hologram and accessibility labels use GÖLGE branding",()=>{
 for(const file of [
  "../src/dashboard/CenterStage.tsx",
  "../src/dashboard/ReferencePanels.tsx",
  "../src/dashboard/core/CoreAnimation.tsx",
  "../src/dashboard/core/CoreScene.ts",
  "../src/hologram/Standalone.tsx"
 ]){
  const source=fs.readFileSync(new URL(file,import.meta.url),"utf8");
  assert.doesNotMatch(source,/ULTRON|JARVIS|T\.O\.R\.V\.I\.S/,file);
 }
});
