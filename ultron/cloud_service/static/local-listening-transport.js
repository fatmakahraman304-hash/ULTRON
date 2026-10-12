/* Explicit laptop-only Qwen listening-analysis transport.
 * Chunk text temporarily crosses Render's authenticated device-command DB.
 * No implicit Gemini fallback, browser token exposure, or device actions.
 */
(function(root,factory){
 'use strict';
 const api=factory();
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 if(root)root.ULTRONLocalListeningTransport=api;
})(typeof window!=='undefined'?window:null,function(){
 'use strict';
 function create({api,uuid,now=Date.now,sleep=ms=>new Promise(r=>setTimeout(r,ms)),deadlineMs=220000}){
   if(typeof api!=='function'||typeof uuid!=='function')throw Error('Güvenli istek kimliği gerekir.');
   const pending=new Map();
   async function request(body){
     if(!body||!['map','reduce','final'].includes(body.stage)||typeof body.text!=='string')
       throw Error('Geçersiz yerel analiz isteği.');
     const key=JSON.stringify(body);
     let info=pending.get(key);
     if(!info){info={request_id:uuid(),command_id:null};pending.set(key,info);}
     const until=now()+deadlineMs;
     if(!info.command_id){
       // If the previous POST reply was lost, reusing this same UUID prevents
       // duplicate queue tasks when the owner explicitly retries.
       const posted=await api('/api/listening-analysis/local',{
         method:'POST',timeoutMs:15000,
         body:JSON.stringify({...body,request_id:info.request_id})
       });
       if(posted?.status!=='queued'||!Number.isSafeInteger(posted.command_id)||posted.command_id<1)
         throw Error('Yerel analiz kuyruğunun onayı doğrulanamadı.');
       info.command_id=posted.command_id;
     }
     while(now()<until){
       const d=await api('/api/listening-analysis/local/'+info.command_id,{timeoutMs:9000});
       if(d?.status==='completed'){
         if(d.stage!==body.stage||typeof d.analysis!=='string'||!d.analysis.trim()||
            d.provider!=='local-ollama')throw Error('Beklenmeyen Qwen analiz cevabı.');
         pending.delete(key);
         return d;
       }
       if(['failed','cancelled','expired'].includes(d?.status))
         throw Error('Laptop Qwen analiz bölümünü tamamlayamadı. Gemini’ye otomatik geçilmedi.');
       if(!['queued','delivered'].includes(d?.status))throw Error('Bilinmeyen yerel analiz durumu.');
       await sleep(1600);
     }
     // Command may still complete after this timeout. The owner can retry
     // with the same UUID/command ID, without queueing duplicate work.
     throw Error('Yerel analiz zaman aşımı. Aynı bölümü tekrar isteyerek durumunu kontrol et.');
   }
   function clear(){pending.clear();}
   return {request,clear,pendingCount:()=>pending.size};
 }
 return {create};
});
