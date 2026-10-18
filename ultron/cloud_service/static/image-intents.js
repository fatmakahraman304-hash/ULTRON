/* One deterministic router for PWA and React. No provider calls or permissions. */
(function(root,factory){const api=factory();if(typeof module!=='undefined')module.exports=api;root.GolgeImages=api;})(globalThis,function(){
 function resolve(text){
  const t=String(text||'').toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i');
  if(!t||t.length>4000)return null;
  if(/\b(?:bul|ara|indir|analiz|incele|hakkinda|nedir|nasil|find|search|download|analyze|explain)\b/.test(t))return null;
  const noun=/fotograf|gorsel|res(?:im|mi)|duvar kagidi|image|picture|wallpaper|photo|digital sanat/.test(t);
  if(noun&&/sinematik yap|duzenle|iyilestir|degistir|edit|enhance/.test(t)&&/\b(?:bu|bunu|this|it)\b/.test(t))return 'edit';
  if((noun&&/olustur|uret|ciz|yarat|\byap\b|generate|create|draw|paint/.test(t))||/\bciz\b|\bdraw\b/.test(t)||/^(?:bana )?(?:bir )?.{1,60}\bdaire olustur/.test(t))return 'generate';
  return null;
 }
 function options(text){const t=String(text).toLocaleLowerCase('tr-TR');return {aspect_ratio:/dikey|telefon.*duvar|portrait/.test(t)?'9:16':/yatay|masaüstü.*duvar|landscape/.test(t)?'16:9':'1:1',style:/sinematik|cinematic/.test(t)?'cinematic':/anime|çizim/.test(t)?'anime':/3d|3 boyut/.test(t)?'3d':/dijital sanat/.test(t)?'digital-art':/fotoğraf|gerçekçi|photo/.test(t)?'photo':'natural'};}
 function confirmCost(detail,signal){
  // Non-blocking consent: a native confirm() pauses audio/work on the JS thread.
  return new Promise(done=>{
   if(signal?.aborted){done(false);return;}
   const previous=document.activeElement,dialog=document.createElement('dialog');
   dialog.setAttribute('aria-label','Görsel üretimi maliyet onayı');
   dialog.style.cssText='color:#dff6ff;background:#071522;border:1px solid #28758e;border-radius:16px;padding:24px;max-width:min(420px,90vw);z-index:9999';
   const text=document.createElement('p');text.textContent=detail+' Ücretli tek görsel üretimini onaylıyor musun?';
   const approve=document.createElement('button');approve.textContent='Ücretli üretimi onayla';approve.type='button';
   const deny=document.createElement('button');deny.textContent='Vazgeç';deny.type='button';
   for(const button of [approve,deny])button.style.cssText='padding:12px;margin:5px;border:1px solid #28758e;border-radius:10px;background:#10364b;color:#e1f7ff;cursor:pointer';
   let settled=false;
   const finish=value=>{if(settled)return;settled=true;signal?.removeEventListener('abort',abort);dialog.remove();previous?.focus?.();done(value);};
   const abort=()=>finish(false);
   approve.onclick=()=>finish(true);deny.onclick=()=>finish(false);
   dialog.oncancel=e=>{e.preventDefault();finish(false)};
   signal?.addEventListener('abort',abort,{once:true});dialog.append(text,approve,deny);document.body.append(dialog);
   if(typeof dialog.showModal!=='function'){finish(false);return;}
   dialog.showModal();deny.focus();
  });
 }
 async function awaitResult(poll,result,signal){
  const deadline=Date.now()+270000;
  while(result.status==='queued'||result.status==='running'){
   if(signal.aborted)throw new DOMException('İptal edildi','AbortError');
   if(Date.now()>deadline)throw Error('Yerel üretimin sonucu zamanında alınamadı. Otomatik tekrar veya ücretli geçiş yapılmadı.');
   await new Promise((resolve,reject)=>{
    const abort=()=>{clearTimeout(timer);reject(new DOMException('İptal edildi','AbortError'));};
    const timer=setTimeout(()=>{signal.removeEventListener('abort',abort);resolve()},800);
    signal.addEventListener('abort',abort,{once:true});
   });
   result=await poll();
  }
  return result;
 }
 return {resolve,options,confirmCost,awaitResult};
});
