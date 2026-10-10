/* ULTRON command-first panels. Exact user intent: no LLM needed for navigation.
 * Pure function, shared by mobile text and Live voice transcripts.
 */
(function(root,factory) {
 "use strict";
 const value=factory();
 if(typeof module!=="undefined"&&module.exports)module.exports=value;
 if(root)root.ULTRONPanelIntents=value;
})(typeof window!=="undefined"?window:null,function() {
 "use strict";
 const normal=s=>String(s||"").toLocaleLowerCase("tr-TR").replace(/[’']/g,"'").replace(/\s+/g," ").trim();
 function resolve(text) {
  const t=normal(text);
  if(!t||t.length>400)return null;
  const verb=/(?:^|\s)(?:aç|ac|göster|goster|getir|çıkart|cikart|geç|gec|bak|izle|başlat|baslat|open|show|bring)(?=$|\s|[.!?])/;
  if(/^(?:ana ekrana dön|ana ekrana don|sohbete dön|sohbete don|paneli kapat|ekranı kapat|ekrani kapat|close panel|back to chat|ultron ana ekran)$/.test(t))
    return {view:"chat"};
  if(!verb.test(t))return null;
  if(/(?:hologram\s*(?:lab|laboratuvar|çalışma alanı|calisma alani)|hologram laboratuvarı|hologram laboratuvari|hologram tasarım|hologram tasarim)/.test(t))
    return {view:"hologram"};
  if(/(?:dünya|dunya|world|harita|earth watch|uçak|ucak|deprem|hava durumu|weather)/.test(t))
    return {view:"world"};
  if(/(?:hafıza|hafiza|hatıra|hatira|öğrenme|ogrenme|takvim|planlarım|planlarim)/.test(t))
    return {view:"memory"};
  if(/(?:uzaktan|laptop kontrol|bilgisayar kontrol|remote)/.test(t))
    return {view:"remote"};
  if(/(?:geliştir|gelistir|geliştirme panel|kod panel|development)/.test(t))
    return {view:"develop"};
  if(/(?:sohbet|konuşma|konusma|chat)/.test(t))
    return {view:"chat"};
  return null;
 }
 return {resolve};
});
