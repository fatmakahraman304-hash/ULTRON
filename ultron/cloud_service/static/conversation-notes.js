/* Owner-reviewed ULTRON chat notes. All controls are inside HAFIZA;
 * main cockpit is unchanged. No API reads/writes until the owner asks.
 */
(function(root,factory){
  "use strict";
  const api=factory();
  if(typeof module!=="undefined" && module.exports)module.exports=api;
  if(root)root.ULTRONConversationNotes=api;
})(typeof window!=="undefined"?window:null,function(){
  "use strict";
  const draftIntent=text=>/^(?:ultron[,.! ]+)?(?:bu\s+)?(?:sohbet|konuşma)\s+notu\s+(?:hazırla|oluştur|çıkar|çıkart)(?:\s+lütfen)?[.!?]*$/i.test(
    String(text||"").toLocaleLowerCase("tr-TR").trim()
  );
  const listIntent=text=>/^(?:ultron[,.! ]+)?(?:sohbet\s+)?notlarımı\s+(?:aç|göster|getir)[.!?]*$/i.test(
    String(text||"").toLocaleLowerCase("tr-TR").trim()
  );
  function create(options){
    const o=options||{}, doc=o.document;
    if(!doc || typeof o.fetchJson!=="function" || typeof o.getConversationId!=="function")
      throw Error("document_fetchJson_and_conversation_required");
    const node=id=>doc.getElementById(id);
    const confirmDelete=o.confirmDelete||(
      typeof window!=="undefined" ? msg=>window.confirm(msg) : ()=>false
    );
    const enter=o.openMemory||(()=>{});
    let busy=false,editId=null;
    const status=message=>{node("conversationNotesStatus").textContent=message};
    const thread=()=>{
      const id=o.getConversationId();
      return typeof id==="string" && /^[\da-fA-F-]{36}$/.test(id)?id:"";
    };
    const url=()=>"/api/conversation-notes?conversation_id="+encodeURIComponent(thread());
    function reset(){
      editId=null;
      node("conversationNoteTitle").value="";
      node("conversationNoteBody").value="";
      node("saveConversationNote").textContent="NOTU KAYDET";
    }
    async function preview(){
      if(busy)return;
      enter();
      const id=thread();
      if(!id){status("Önce ULTRON'la bir sohbet başlat.");return;}
      busy=true;
      try{
        const data=await o.fetchJson("/api/conversation-notes/preview?conversation_id="+encodeURIComponent(id));
        reset();
        node("conversationNoteTitle").value=data.draft?.title||"Sohbetten not";
        node("conversationNoteBody").value=data.draft?.body||"";
        status("Taslak hazır. Mesajlardan seçilmiş bölümlerdir; eksik veya hassas bilgileri kontrol et. KAYDET demeden saklanmaz.");
      }catch(e){status("Taslak hazırlanamadı: "+String(e.message||e).slice(0,120))}
      finally{busy=false;}
    }
    function render(note){
      const card=doc.createElement("div");card.className="memory";
      const title=doc.createElement("b");title.textContent=String(note.title||"").slice(0,140);
      const body=doc.createElement("div");body.textContent=String(note.body||"").slice(0,3000);
      const controls=doc.createElement("div");controls.className="row";
      const edit=doc.createElement("button");
      edit.type="button";edit.className="secondary";edit.textContent="DÜZENLE";
      edit.addEventListener("click",()=>{
        editId=note.id;
        node("conversationNoteTitle").value=note.title;
        node("conversationNoteBody").value=note.body;
        node("saveConversationNote").textContent="DEĞİŞİKLİĞİ KAYDET";
        status("Notu düzenle; değişiklik ancak KAYDET'e basınca saklanır.");
      });
      const remove=doc.createElement("button");
      remove.type="button";remove.className="secondary";remove.textContent="SİL";
      remove.addEventListener("click",()=> {
        if(!confirmDelete("Bu sohbet notunu kalıcı olarak silmek istiyor musun?"))return;
        return discard(note.id);
      });
      controls.append(edit,remove);card.append(title,body,controls);
      return card;
    }
    async function refresh(){
      if(busy)return;
      const id=thread();
      if(!id){status("Önce bir sohbet başlat.");return;}
      busy=true;
      try{
        const data=await o.fetchJson(url());
        const list=node("conversationNotesList");
        list.replaceChildren();
        const notes=Array.isArray(data.notes)?data.notes:[];
        notes.forEach(n=>list.appendChild(render(n)));
        status(notes.length?notes.length+" kayıtlı not; yalnızca bu sohbette görünür.":"Bu sohbete ait kayıtlı not yok.");
      }catch(e){status("Notlar alınamadı: "+String(e.message||e).slice(0,120))}
      finally{busy=false;}
    }
    async function save(){
      if(busy)return;
      const id=thread();
      if(!id){status("Önce bir sohbet başlat.");return;}
      const title=node("conversationNoteTitle").value.trim();
      const body=node("conversationNoteBody").value.trim();
      if(!title||!body){status("Not başlığı ve içeriği gerekli.");return;}
      busy=true;
      const editing=editId;
      try{
        await o.fetchJson(editing?"/api/conversation-notes/"+encodeURIComponent(String(editing)):"/api/conversation-notes",{
          method:editing?"PUT":"POST",body:JSON.stringify({conversation_id:id,title,body}),
        });
        reset();
      }catch(e){
        status("Not kaydedilemedi: "+String(e.message||e).slice(0,120));return;
      }finally{busy=false;}
      await refresh();
    }
    async function discard(id){
      if(busy)return;
      busy=true;
      try{await o.fetchJson("/api/conversation-notes/"+encodeURIComponent(String(id)),{method:"DELETE"});}
      catch(e){status("Not silinemedi: "+String(e.message||e).slice(0,120));return;}
      finally{busy=false;}
      if(editId===id)reset();
      await refresh();
    }
    function runCommand(text){
      if(draftIntent(text)){void preview();return true;}
      if(listIntent(text)){enter();void refresh();return true;}
      return false;
    }
    function init(){
      if(!node("previewConversationNote")||!node("saveConversationNote"))return false;
      node("previewConversationNote").addEventListener("click",preview);
      node("saveConversationNote").addEventListener("click",save);
      node("refreshConversationNotes").addEventListener("click",refresh);
      node("cancelConversationNote").addEventListener("click",()=>{reset();status("Düzenleme iptal edildi; kayıtlı not değişmedi.")});
      return true;
    }
    return {init,runCommand,preview,refresh,save,discard};
  }
  return {create,draftIntent,listIntent};
});
