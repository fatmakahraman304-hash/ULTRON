/* Explicit, synthetic-only Render -> paired Windows Qwen diagnostic. No microphone. */
(function(root,factory){
  'use strict';
  const api=factory();
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  if(root)root.ULTRONLocalListeningProbe=api;
})(typeof window!=='undefined'?window:null,function(){
  'use strict';
  function create({presence,request,id=()=>crypto.randomUUID(),now=()=>Date.now(),onStatus=()=>{}}){
    if(typeof presence!=='function'||typeof request!=='function')
      throw new Error('Bağlantı testi servisleri gerekli.');
    let running=false;
    function update(phase,message,extra={}){
      onStatus({phase,message,...extra});
    }
    async function run(){
      if(running)throw new Error('Qwen bağlantı testi zaten devam ediyor.');
      running=true;
      const started=now();
      try{
        update('checking','Laptop bağlantısı ve Qwen analiz işçisi kontrol ediliyor…');
        const data=await presence();
        const desktop=Array.isArray(data?.devices)
          ?data.devices.find(d=>d?.device==='desktop'):null;
        if(desktop?.online!==true){
          throw new Error('Laptop ULTRON çevrimiçi değil. Laptopta ULTRON ve Cloud bağlantısını başlat.');
        }
        if(desktop?.state?.local_listening_analysis_ready!==true){
          throw new Error('Laptop çevrimiçi ancak yeni Qwen analiz işçisi hazır değil. Windows ULTRON sürümünü güncelle.');
        }
        // A fresh generated challenge prevents a previous completed result
        // from being accidentally mistaken for an actual new device roundtrip.
        const token=String(id());
        if(!/^[a-zA-Z0-9-]{8,80}$/.test(token))
          throw new Error('Bağlantı testi kimliği geçersiz.');
        const speech='Bu yalnızca ULTRON Qwen bağlantı testi için sentetik bir nottur. '
          +'Gerçek kullanıcı konuşması yoktur. Test kodu '+token+'. '
          +'Önemli karar: sadece bağlantı doğrulanıyor; hiçbir işlem yapılmayacak.';
        update('testing','Render üzerinden laptop Qwen modeline örnek analiz gönderildi; yanıt bekleniyor…');
        const result=await request({stage:'map',text:speech,part:1,total:1});
        if(result?.provider!=='local-ollama'||result?.stage!=='map'
          ||typeof result?.analysis!=='string'||!result.analysis.trim()
          ||!/^qwen/i.test(String(result.model||''))){
          throw new Error('Yerel Qwen doğrulanmış bir analiz yanıtı döndürmedi.');
        }
        const latencyMs=Math.max(0,now()-started);
        const model=result.model;
        update('success','Gerçek Qwen yanıtı alındı • '+model
          +' • '+Math.round(latencyMs/1000)+' sn',{latencyMs,model});
        return {ok:true,model,latencyMs,route:'phone-render-windows-qwen',
          synthetic:true};
      }catch(error){
        const message=String(error?.message||'Bağlantı doğrulanamadı.');
        // Never show provider response text, model prompts or authentication data.
        const known=/^Laptop |^Yerel Qwen |^Bağlantı testi/.test(message);
        update('failure',known?message:'Qwen yanıtı alınamadı. Laptop ULTRON, Ollama ve Render bağlantısını kontrol et.');
        throw error;
      }finally{running=false;}
    }
    return {run,active:()=>running};
  }
  return {create};
});
