/* Strict, one-at-a-time owner-initiated local Qwen analysis over Render queue. */
(function(root,factory){
  'use strict';
  const api=factory();
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  if(root)root.ULTRONLocalListening=api;
})(typeof window!=='undefined'?window:null,function(){
  'use strict';
  function ready(devices){
    const desktop=(Array.isArray(devices)?devices:[]).find(x=>x?.device==='desktop');
    return desktop?.online===true&&desktop?.state?.local_listening_analysis_ready===true;
  }
  function create({api,now=()=>Date.now(),sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms)),id=()=>crypto.randomUUID(),timeoutMs=240000}){
    if(typeof api!=='function')throw new Error('Authenticated API required');
    const seen=new Map();
    async function request(body){
      const stage=body?.stage;
      const text=body?.text;
      if(!['map','reduce','final'].includes(stage)||typeof text!=='string'||text.length>12000||!text.trim())
        throw new Error('Qwen analiz aşaması veya metni geçersiz.');
      // The same analysis stage reuses the exact request ID on manual retry.
      // This avoids a duplicate desktop job after an accepted-but-lost POST.
      const key=JSON.stringify([stage,text,body.part,body.total]);
      let state=seen.get(key);
      if(!state){
        state={requestId:id(),commandId:null};
        seen.set(key,state);
      }
      const deadline=now()+timeoutMs;
      let taskId=state.commandId;
      if(!taskId){
        const result=await api('/api/local-listening-analysis',{
          method:'POST',timeoutMs:16000,
          body:JSON.stringify({...body,request_id:state.requestId})
        });
        if(!Number.isSafeInteger(result?.id)||result.id<=0)
          throw new Error('Qwen görev kabulü doğrulanamadı.');
        taskId=result.id;
        state.commandId=taskId;
      }
      while(now()<deadline){
        const result=await api('/api/local-listening-analysis/'+taskId,{timeoutMs:12000});
        if(result?.status==='completed'){
          if(result.stage!==stage||result.provider!=='local-ollama'||typeof result.analysis!=='string'||!result.analysis.trim())
            throw new Error('Qwen doğrulanmamış analiz yanıtı verdi.');
          // No HTTP POST retry after confirmed result; retain value only
          // until the current tab/session is explicitly cleared.
          state.analysis=result.analysis;
          return {stage,analysis:result.analysis,provider:result.provider,model:result.model};
        }
        if(result?.status==='failed'||result?.status==='expired'||result?.status==='cancelled')
          throw new Error('Yerel Qwen bu konuşma bölümünü tamamlayamadı.');
        if(!['queued','delivered'].includes(result?.status))
          throw new Error('Yerel analiz kuyruğunda bilinmeyen durum.');
        await sleep(2300);
      }
      throw new Error('Qwen analizi bekleme süresi doldu. Oturumu yeniden denemeden önce görev durumunu kontrol et.');
    }
    function clear(){seen.clear();}
    return {request,clear,pending:()=>seen.size};
  }
  return {ready,create};
});
