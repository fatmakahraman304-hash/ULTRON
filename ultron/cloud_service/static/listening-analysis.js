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
        let boundary=text.lastIndexOf('\n',end);
        if(boundary<=offset+CHUNK_SIZE/2)boundary=text.lastIndexOf(' ',end);
        if(boundary>offset+CHUNK_SIZE/2)end=boundary+1;
      }
      const segment=text.slice(offset,end);
      // A bounded slice is NEVER silently dropped. Preserve every character.
      parts.push(segment);
      offset=end;
    }
    if(parts.length>MAX_CHUNKS)throw new Error('Konuşma çok fazla bölüme ayrıldı.');
    if(parts.join('')!==text)throw new Error('Konuşma bölünürken veri kayboldu.');
    return parts;
  }
  function create({request,onProgress=()=>{}}){
    if(typeof request!=='function')throw new Error('Analiz isteği göndericisi gerekli.');
    let state=null,working=false,stopRequested=false;
    function progress(status,completed,total){
      onProgress({status,completed,total,parts:state?state.parts.length:0});
    }
    async function ask(stage,text,part,total){
      if(stopRequested)throw new Error('Analiz kullanıcı tarafından durduruldu.');
      const body={stage,text};
      if(stage==='map'){body.part=part;body.total=total;}
      const response=await request(body);
      if(stopRequested)throw new Error('Analiz kullanıcı tarafından durduruldu.');
      if(!response||response.stage!==stage||typeof response.analysis!=='string'||!response.analysis.trim())
        throw new Error('Analiz sunucusundan doğrulanmamış cevap geldi.');
      if(response.analysis.length>9500)throw new Error('Analiz cevabı beklenenden uzun.');
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
            const groups=Math.ceil(state.round.length/FAN_IN);
            while(state.group<groups){
              progress('Bölüm notları birleştiriliyor',state.group,groups);
              const offset=state.group*FAN_IN;
              const items=state.round.slice(offset,offset+FAN_IN)
                .map((s,i)=>'[Not '+(offset+i+1)+']\n'+s);
              const input=items.join('\n\n');
              if(input.length>12000)throw new Error('Ara analiz bütçeyi aştı.');
              state.next.push(await ask('reduce',input));
              state.group++;
            }
            state.round=state.next.slice();state.next=[];state.group=0;state.roundNumber++;
            if(state.roundNumber>5)throw new Error('Birleştirme aşaması sınırı aşıldı.');
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
        progress('Analiz kesildi; güvenli kısmi ilerleme korundu',0,1);
        throw err;
      }finally{working=false;}
    }
    function stop(){if(!working)return false;stopRequested=true;return true;}
    function clear(){if(working)return false;state=null;stopRequested=false;return true;}
    return {run,clear,stop,active:()=>working,checkpoint:()=>state
      ?{stage:state.phase,parts:state.parts.length,mapped:state.mapped.length,group:state.group}
      :null};
  }
  return {create,split,CHUNK_SIZE,MAX_TEXT};
});
