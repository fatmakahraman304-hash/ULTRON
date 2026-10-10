/* Owner-approved ULTRON learning inbox. Never fetch or save without a tap.
 * Untrusted proposed text is always rendered with textContent.
 */
(function (global, factory) {
  "use strict";
  const api=factory();
  if (typeof module!=="undefined" && module.exports) module.exports=api;
  if (global) global.ULTRONLearningReview=api;
})(typeof window!=="undefined"?window:null,function () {
  "use strict";
  function create(opts) {
    const o=opts||{};
    const doc=o.document||(typeof document!=="undefined"?document:null);
    const api=o.fetchJson;
    const ask=o.confirmRemove||(typeof window!=="undefined"?(s=>window.confirm(s)):(()=>false));
    const memoryChanged=o.onMemoryChanged||(()=>{});
    if(!doc||typeof api!=="function") throw Error("document_and_fetchJson_required");
    const el=id=>doc.getElementById(id);
    let busy=false, autoLoaded=false, autoEnabled=false;
    async function toggleAuto() {
      if(busy)return;
      busy=true;
      const button=el("autoLearningToggle"), status=el("autoLearningStatus");
      button.disabled=true;
      try {
        if(!autoLoaded) {
          const info=await api("/api/auto-learning");
          autoEnabled=Boolean(info.enabled);
          autoLoaded=true;
        } else {
          const next=!autoEnabled;
          if(next && !ask("ULTRON yalnızca senin açıkça yazdığın 'Tercihim:', 'Hedefim:' ve 'Projem:' ifadelerini sohbet sırasında otomatik hafızaya kaydetsin mi? Bu ayarı istediğin zaman kapatabilirsin.")) {
            return;
          }
          const result=await api("/api/auto-learning",{method:"PUT",body:JSON.stringify({enabled:next})});
          autoEnabled=Boolean(result.enabled);
        }
        status.textContent=autoEnabled
          ? "AÇIK • Yalnızca açıkça belirttiğin hedef/tercih/projeler kaydedilir. Şifre ve hassas bilgiler dışlanır. İstediğinde kapatabilirsin."
          : "KAPALI • Sohbetlerden otomatik bilgi kaydedilmez. Elle onaylama kullanılabilir.";
        button.textContent=autoEnabled?"OTOMATİK ÖĞRENMEYİ KAPAT":"OTOMATİK ÖĞRENMEYİ AÇ";
      } catch(e) {
        status.textContent="Öğrenme ayarı okunamadı/değiştirilemedi: "+String(e.message||e).slice(0,130);
      } finally {busy=false;button.disabled=false;}
    }
    function makeItem(p) {
      const card=doc.createElement("div");card.className="memory";
      const title=doc.createElement("b");
      title.textContent="["+String(p.category||"").slice(0,40)+"] "+String(p.key||"").slice(0,120);
      const value=doc.createElement("div");value.textContent=String(p.value||"").slice(0,1000);
      const state=doc.createElement("small");
      state.textContent=p.status==="pending"?"Onay bekliyor • henüz öğrenilmedi":
        p.status==="approved"?"Onaylandı • hafızaya kaydedildi":"Reddedildi • hafızaya eklenmedi";
      const actions=doc.createElement("div");actions.className="row";
      if(p.status==="pending") {
        for(const [label,approve] of [["ONAYLA",true],["REDDET",false]]) {
          const button=doc.createElement("button");
          button.type="button";button.className="secondary";button.textContent=label;
          button.addEventListener("click",()=>decide(p.id,approve));
          actions.appendChild(button);
        }
      }
      const remove=doc.createElement("button");
      remove.type="button";remove.className="secondary";remove.textContent="ÖNERİYİ SİL";
      remove.addEventListener("click",()=> {
        if(ask("Öğrenme önerisini silmek istiyor musun? Onaylanmış hafıza ayrı silinir."))return discard(p.id);
      });
      actions.appendChild(remove);
      card.append(title,value,state,actions);
      return card;
    }
    async function refresh() {
      if(busy)return;
      busy=true;
      el("refreshLearning").disabled=true;
      el("learningStatus").textContent="Öneriler okunuyor…";
      try {
        const data=await api("/api/learning-proposals");
        const items=Array.isArray(data.proposals)?data.proposals.slice(0,60):[];
        const list=el("learningItems");list.replaceChildren();
        items.forEach(p=>list.appendChild(makeItem(p)));
        el("learningStatus").textContent=items.length
          ? items.length+" öneri • yalnızca ONAYLA ile hafızaya yazılır"
          : "Henüz öneri yok. Kaydedilmesini istediğin bilgiyi öner.";
      } catch (e) {
        el("learningStatus").textContent="Öneriler alınamadı: "+String(e.message||e).slice(0,130);
      } finally {busy=false;el("refreshLearning").disabled=false;}
    }
    async function propose() {
      if(busy)return;
      const category=el("learningCategory").value;
      const key=el("learningKey").value.trim();
      const value=el("learningValue").value.trim();
      if(!key||!value) {
        el("learningStatus").textContent="Öneri anahtarı ve açıklama gerekli.";return;
      }
      busy=true;el("submitLearning").disabled=true;
      let ok=false;
      try {
        await api("/api/learning-proposals",{method:"POST",body:JSON.stringify({category,key,value})});
        ok=true;
        el("learningKey").value="";el("learningValue").value="";
      } catch(e) {
        el("learningStatus").textContent="Öneri gönderilemedi: "+String(e.message||e).slice(0,130);
      } finally {busy=false;el("submitLearning").disabled=false;}
      if(ok)await refresh();
    }
    async function decide(id,approve) {
      if(busy||!Number.isSafeInteger(Number(id))||Number(id)<=0)return;
      busy=true;let ok=false;
      try {
        await api("/api/learning-proposals/"+encodeURIComponent(String(id))+"/decision",{
          method:"POST",body:JSON.stringify({approve})
        });
        ok=true;
      } catch(e) {
        el("learningStatus").textContent="Karar kaydedilemedi: "+String(e.message||e).slice(0,130);
      } finally {busy=false;}
      if(ok) {
        if(approve) { try {await memoryChanged();}catch(_){} }
        await refresh();
      }
    }
    async function discard(id) {
      if(busy||!Number.isSafeInteger(Number(id))||Number(id)<=0)return;
      busy=true;let ok=false;
      try {
        await api("/api/learning-proposals/"+encodeURIComponent(String(id)),{method:"DELETE"});
        ok=true;
      } catch(e) {
        el("learningStatus").textContent="Silinemedi: "+String(e.message||e).slice(0,130);
      } finally {busy=false;}
      if(ok)await refresh();
    }
    function init() {
      if(!el("submitLearning")||!el("refreshLearning"))return false;
      el("submitLearning").addEventListener("click",propose);
      el("refreshLearning").addEventListener("click",refresh);
      el("autoLearningToggle")?.addEventListener("click",toggleAuto);
      return true;
    }
    return {init,refresh,propose};
  }
  return {create};
});
