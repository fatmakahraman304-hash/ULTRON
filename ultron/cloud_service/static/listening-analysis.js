/* Owner-triggered, sequential transcript map/reduce. No local persistence. */
(function(root,factory){
  'use strict';
  const api=factory();
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  if(root)root.ULTRONListeningAnalysis=api;
})(typeof window!=='undefined'?window:null,function(){
  'use strict';
  const CHUNK_SIZE=11500, MAX_CHUNKS=32, MAX_TEXT=300000, FAN_IN=5;
  function split(text){
    if(typeof text!=='string'||!text.trim()||text.length>MAX_TEXT)
      throw new Error('Konuşma uzunluğu desteklenen sınırın dışında.');
    const parts=[];
    let offset=0;
    while(offset<text.length){
      let end=Math.min(text.length,offset+CHUNK_SIZE);
      if(end<text.length){
        let boundary=text.lastIndexOf('\n',end-1);
        if(boundary<=offset+CHUNK_SIZE/2)boundary=text.lastIndexOf(' ',end-1);
        if(boundary>offset+CHUNK_SIZE/2)end=boundary+1;
      }
      // UTF-16 slicing must not send an unpaired surrogate to Python/UTF-8.
      if(end<text.length&&/[\uD800-\uDBFF]/.test(text[end-1])&&/[\uDC00-\uDFFF]/.test(text[end]))end--;
      const segment=text.slice(offset,end);
      // A bounded slice is NEVER silently dropped. Preserve every character.
      parts.push(segment);
      offset=end;
    }
    if(parts.length>MAX_CHUNKS)throw new Error('Konuşma çok fazla bölüme ayrıldı.');
    if(parts.join('')!==text)throw new Error('Konuşma bölünürken veri kayboldu.');
    return parts;
  }
  // Python len() counts Unicode code points, unlike JavaScript string.length.
  const chars=text=>Array.from(text).length;
  function failure(code,message){return Object.assign(new Error(message),{code});}
  function errorMessage(error){
    const messages={
      local_analysis_pending:'Sonuç henüz alınamadı. Cevap ver ile aynı görevden devam edebilirsin.',
      invalid_local_analysis:'Laptop görevi tamamladı, fakat analiz sonucu doğrulanamadı.',
      invalid_analysis_response:'Analiz yanıtı doğrulanamadı.',
      analysis_auth_required:'Oturum izni doğrulanamadı. Yeniden giriş yap.',
      local_analysis_offline:'Laptop Qwen analiz işçisi hazır değil.',
      local_analysis_busy:'Önceki analiz bölümü hâlâ bekleniyor.',
      analysis_stopped:'Analiz isteğinle durduruldu.',
      analysis_budget_exceeded:'Bölüm notları analiz sınırına sığmadı.',
      analysis_round_limit:'Bölüm notları yeterince kısalmadı; ilerleme korundu.'
    };
    const phase={map:'Bölüm analizi',reduce:'Not birleştirme',final:'Son rapor'}[error?.stage];
    const message=Object.hasOwn(messages,error?.code)?messages[error.code]:'Analiz bağlantısı veya yanıtı doğrulanamadı.';
    return (typeof phase==='string'?phase+': ':'')+message;
  }
  function reduceGroups(notes){
    const groups=[];let items=[],size=0;
    notes.forEach((note,i)=>{
      const item='[Not '+(i+1)+']\n'+note;
      const length=chars(item);
      if(length>12000)throw failure('analysis_budget_exceeded','Ara analiz bütçeyi aştı.');
      if(items.length&&(items.length===FAN_IN||size+2+length>12000)){
        groups.push(items.join('\n\n'));items=[];size=0;
      }
      size+=(items.length?2:0)+length;items.push(item);
    });
    if(items.length)groups.push(items.join('\n\n'));
    return groups;
  }
  function create({request,onProgress=()=>{}}){
    if(typeof request!=='function')throw new Error('Analiz isteği göndericisi gerekli.');
    let state=null,working=false,stopRequested=false;
    function progress(status,completed,total){
      onProgress({status,completed,total,parts:state?state.parts.length:0});
    }
    async function ask(stage,text,part,total){
      if(stopRequested)throw failure('analysis_stopped','Analiz kullanıcı tarafından durduruldu.');
      const body={stage,text};
      if(stage==='map'){body.part=part;body.total=total;}
      const response=await request(body);
      if(stopRequested)throw failure('analysis_stopped','Analiz kullanıcı tarafından durduruldu.');
      if(!response||response.stage!==stage||typeof response.analysis!=='string'||!response.analysis.trim())
        throw failure('invalid_analysis_response','Analiz sunucusundan doğrulanmamış cevap geldi.');
      if(chars(response.analysis)>9500)throw failure('invalid_analysis_response','Analiz cevabı beklenenden uzun.');
      return response.analysis.trim();
    }
    async function run(text){
      if(working)throw new Error('Dinleme analizi zaten çalışıyor.');
      if(!state||state.text!==text){
        state={text,parts:split(text),mapped:[],phase:'map',round:[],next:[],
          group:0,roundNumber:0,result:null};
      }
      stopRequested=false;
      working=true;
      try{
        while(true){
          if(state.phase==='map'){
            while(state.mapped.length<state.parts.length){
              const i=state.mapped.length;
              progress('Konuşmanın tamamı inceleniyor',i,state.parts.length);
              state.mapped.push(await ask('map',state.parts[i],i+1,state.parts.length));
            }
            state.round=state.mapped.slice();
            state.next=[];state.group=0;state.phase='reduce';
          }
          if(state.phase==='reduce'){
            if(state.round.length===1){state.phase='final';continue;}
            const groups=reduceGroups(state.round);
            while(state.group<groups.length){
              progress('Bölüm notları birleştiriliyor',state.group,groups.length);
              state.next.push(await ask('reduce',groups[state.group]));
              state.group++;
            }
            state.round=state.next.slice();state.next=[];state.group=0;state.roundNumber++;
            if(state.roundNumber>8)throw failure('analysis_round_limit','Birleştirme aşaması sınırı aşıldı.');
            continue;
          }
          if(state.phase==='final'){
            progress('Kararlar ve yapılacak işler hazırlanıyor',0,1);
            state.result=await ask('final',state.round[0]);
            state.phase='complete';
          }
          if(state.phase==='complete'){
            progress('Tamamlandı',1,1);
            return {answer:state.result,parts:state.parts.length,
              chunksAnalyzed:state.mapped.length,saved:false};
          }
        }
      }catch(err){
        // Keep successful chunk notes only in this open tab, ready for
        // explicit owner retry, without uploading again automatically.
        if(err&&typeof err==='object')err.stage=state.phase;
        progress('Analiz kesildi; güvenli kısmi ilerleme korundu',state.mapped.length,state.parts.length);
        throw err;
      }finally{working=false;}
    }
    function stop(){if(!working)return false;stopRequested=true;return true;}
    function clear(){if(working)return false;state=null;stopRequested=false;return true;}
    return {run,clear,stop,active:()=>working,checkpoint:()=>state
      ?{stage:state.phase,parts:state.parts.length,mapped:state.mapped.length,group:state.group}
      :null};
  }
  return {create,split,errorMessage,CHUNK_SIZE,MAX_TEXT};
});
