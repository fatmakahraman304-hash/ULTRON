/* Bounded HTTP and idempotent read-only local chat. No device-task retries. */
(function(root,factory){'use strict';const api=factory();
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 if(root)root.ULTRONChatTransport=api;
})(typeof window!=='undefined'?window:null,function(){
 'use strict';
 async function request(path,options={},fetcher=fetch){
  const {timeoutMs=20000,...init}=options;
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),timeoutMs);
  try{
   const res=await fetcher(path,{...init,credentials:'include',cache:'no-store',signal:controller.signal,
    headers:{'Content-Type':'application/json',...(init.headers||{})}});
   let data;
   try{data=await res.json()}catch(error){
    if(controller.signal.aborted)throw error;
    const e=new Error('Sunucu yanıtı okunamadı.');e.network=true;throw e;
   }
   if(!res.ok){const e=new Error(data.detail||data.error||('HTTP '+res.status));e.status=res.status;e.data=data;throw e}
   return data;
  }catch(error){
   if(error.status)throw error;
   const e=new Error(controller.signal.aborted?'Bağlantı zaman aşımına uğradı.':'Bağlantı geçici olarak koptu.');
   e.network=true;e.timeout=controller.signal.aborted;throw e;
  }finally{clearTimeout(timer)}
 }
 async function localAnswer(api,body,{onSubmitted=()=>{},onWaiting=()=>{},sleep=ms=>new Promise(r=>setTimeout(r,ms)),now=Date.now,deadlineMs=150000}={}){
  if(!body.request_id)throw new Error('İstek kimliği eksik.');
  const end=now()+deadlineMs;
  let submitted;
  for(let attempt=0;attempt<3;attempt++){
   try{
    submitted=await api('/api/local-chat',{method:'POST',body:JSON.stringify(body),timeoutMs:15000});break;
   }catch(e){
    // Exactly the same request_id/body, protected by the server transaction.
    if(!e.network||attempt===2)throw e;
    onWaiting();await sleep(500*(attempt+1));
   }
  }
  if(!submitted?.command_id)throw new Error('Sohbet görevi doğrulanamadı.');
  onSubmitted(submitted);
  const id=encodeURIComponent(submitted.command_id);
  while(now()<end){
   await sleep(1000);
   let result;
   try{result=await api('/api/local-chat/'+id,{timeoutMs:Math.max(1,Math.min(8000,end-now()))})}
   catch(e){if(e.data?.error!=='invalid_local_reply'&&(e.network||e.status>=500)){onWaiting();continue}throw e}
   if(result.status==='completed'&&typeof result.reply==='string'&&result.reply.trim())return result;
   if(['failed','expired','cancelled'].includes(result.status))throw new Error(result.detail||'Sohbet yanıtı tamamlanamadı.');
   if(now()>end-120000)onWaiting();
  }
  const error=new Error('Yanıt gecikti. Mesajın kaydı korunuyor; aynı mesajı tekrar göndermeden sohbeti yenile.');
  error.pending=true;error.commandId=submitted.command_id;throw error;
 }
 return {request,localAnswer};
});
