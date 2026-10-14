/* Owner-initiated local Qwen analysis over Render; only result GETs retry automatically. */
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
  function failure(code,message,extra={}){return Object.assign(new Error(message),{code,...extra});}
  function safeFailure(error){
    const code=error?.data?.error;
    if(code==='invalid_local_analysis')
      return failure(code,'Laptop görevi tamamladı, fakat analiz sonucu doğrulanamadı.');
    if(error?.status===401||error?.status===403)
      return failure('analysis_auth_required','Oturum izni doğrulanamadı. Yeniden giriş yap.');
    if(['local_analysis_offline','local_analysis_busy','request_id_conflict'].includes(code))
      return failure(code,'Yerel analiz isteği şu anda kabul edilemiyor.');
    return failure(error?.network?'analysis_network_error':'analysis_request_failed',
      'Analiz bağlantısı doğrulanamadı. Konuşma ve mevcut görev kimliği korunuyor.');
  }
  function create({api,now=()=>Date.now(),sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms)),id=()=>crypto.randomUUID(),timeoutMs=240000}){
    if(typeof api!=='function')throw new Error('Authenticated API required');
    const seen=new Map();
    async function request(body){
      const stage=body?.stage;
      const text=body?.text;
      if(!['map','reduce','final'].includes(stage)||typeof text!=='string'||Array.from(text).length>12000||!text.trim())
        throw failure('invalid_analysis_request','Qwen analiz aşaması veya metni geçersiz.');
      // Retain the exact identity after an accepted-but-lost POST. Only the
      // owner's explicit retry can repeat that POST; the server deduplicates it.
      const key=JSON.stringify([stage,text,body.part,body.total]);
      let state=seen.get(key);
      if(!state){state={requestId:id(),commandId:null,result:null};seen.set(key,state);}
      if(state.result)return {...state.result};
      const deadline=now()+timeoutMs;
      let taskId=state.commandId;
      if(!taskId){
        let result;
        try{
          result=await api('/api/local-listening-analysis',{
            method:'POST',timeoutMs:Math.max(1,Math.min(16000,deadline-now())),
            body:JSON.stringify({...body,request_id:state.requestId})
          });
        }catch(error){throw safeFailure(error);}
        if(!Number.isSafeInteger(result?.id)||result.id<=0)
          throw failure('invalid_analysis_acceptance','Qwen görev kabulü doğrulanamadı.');
        taskId=result.id;state.commandId=taskId;
      }
      while(now()<deadline){
        let result;
        try{
          result=await api('/api/local-listening-analysis/'+taskId,
            {timeoutMs:Math.max(1,Math.min(12000,deadline-now()))});
        }catch(error){
          // A lost read says nothing about model success. Poll the SAME job
          // within the deadline, without resubmitting inference or switching provider.
          if(error?.data?.error!=='invalid_local_analysis'&&
              (error?.network===true||error?.status>=500||[408,429].includes(error?.status))){
            await sleep(Math.max(0,Math.min(2300,deadline-now())));continue;
          }
          throw safeFailure(error);
        }
        if(result?.status==='completed'){
          if(result.stage!==stage||result.provider!=='local-ollama'||typeof result.analysis!=='string'||!result.analysis.trim())
            throw failure('invalid_local_analysis','Qwen doğrulanmamış analiz yanıtı verdi.');
          state.result={stage,analysis:result.analysis,provider:result.provider,model:result.model};
          return {...state.result};
        }
        if(['failed','expired','cancelled'].includes(result?.status))
          throw failure('local_analysis_unavailable','Yerel Qwen bu konuşma bölümünü tamamlayamadı.');
        if(!['queued','delivered'].includes(result?.status))
          throw failure('invalid_analysis_status','Yerel analiz kuyruğunda bilinmeyen durum.');
        await sleep(Math.max(0,Math.min(2300,deadline-now())));
      }
      throw failure('local_analysis_pending',
        'Qwen sonucu henüz alınamadı. Cevap ver ile aynı görevden devam edebilirsin.',
        {pending:true,commandId:taskId,stage});
    }
    function clear(){seen.clear();}
    return {request,clear,pending:()=>seen.size};
  }
  return {ready,create};
});