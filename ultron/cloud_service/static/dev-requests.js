/* ULTRON Dev Control: no secret keys and no mythical consumer-ChatGPT API.
   Users explicitly copy the job to ChatGPT; only server proof may mark done.
 */
(function(root){
 "use strict";
 const $=id=>document.getElementById(id);
 let latest=[],seen=new Set(),polling=false,pendingVoice='',voiceAt=0,lastAutoVerification=0;
 const statusLabels={
   awaiting_chatgpt:'CHATGPT İÇİN AKTARILMAYI BEKLİYOR',
   tests_pending:'GITHUB KODU BULUNDU • TESTLER BEKLENİYOR',
   tests_failed:'TEST BAŞARISIZ • YENİ COMMIT GEREK',
   release_pending:'GITHUB TESTLERİ GEÇTİ • RENDER BEKLENİYOR',
   desktop_pending:'CLOUD HAZIR • WINDOWS KURULUMU BEKLENİYOR',
   completed:'DOĞRULANDI • GÜNCELLEME TAMAMLANDI'
 };
 const detect=text=>{
  const t=String(text||'').toLocaleLowerCase('tr-TR').replace(/\s+/g,' ').trim();
  return /(?:ultron|kendini|kod|arayüz|uygulama|sistem)/.test(t)
    &&/(?:geliştir|güncelle|düzelt|özellik ekle|kod(?:u|larını)? değiştir|yeni özellik)/.test(t);
 };
 const suggestTarget=text=>{
  const t=String(text||'').toLocaleLowerCase('tr-TR');
  if(/(?:yalnız|sadece) (?:i(?:phone|os)|telefon|mobil)/.test(t))return 'phone';
  if(/(?:yalnız|sadece) (?:laptop|windows|masaüstü|bilgisayar)/.test(t))return 'desktop';
  return 'both';
 };
 async function api(path,method='GET',body){
  const res=await fetch(path,{method,credentials:'same-origin',
   headers:{'Content-Type':'application/json'},
   body:body?JSON.stringify(body):undefined});
  const data=await res.json().catch(()=>({}));
  if(!res.ok)throw Error(data.error||'HTTP '+res.status);
  return data;
 }
 async function create(prompt,target='both'){
  const d=await api('/api/dev-requests','POST',{prompt,target});
  if(d.request)latest.unshift(d.request);
  render();
  return d.request;
 }
 function render(){
  const rootList=$('devRequestsList');if(!rootList)return;
  rootList.replaceChildren();
  if(!latest.length){const p=document.createElement('p');p.textContent='Henüz kayıtlı geliştirme isteği yok.';rootList.append(p);return}
  latest.slice(0,20).forEach(item=>{
   const div=document.createElement('article');div.className='dev-card';
   const h=document.createElement('strong');h.textContent=String(item.prompt||'').slice(0,160);
   const status=document.createElement('p');status.textContent=statusLabels[item.status]||item.status;
   status.className=item.status==='completed'?'dev-done':item.status==='tests_failed'?'dev-error':'dev-wait';
   const minor=document.createElement('small');minor.textContent='ULTRON-DEV-'+item.id+
      (item.commit_sha?' • '+item.commit_sha.slice(0,9):'')+
      (item.target==='phone'?' • iPhone':item.target==='desktop'?' • Windows':' • iPhone + Windows');
   const actions=document.createElement('div');actions.className='dev-actions';
   const copy=document.createElement('button');copy.textContent='CHATGPT GÖREVİNİ KOPYALA';
   copy.onclick=()=>copyRequest(item).catch(e=>notice(e.message));
   const open=document.createElement('button');open.textContent='CHATGPT AÇ ↗';
   open.onclick=()=>root.open('https://chatgpt.com/','_blank','noopener,noreferrer');
   const verify=document.createElement('button');verify.textContent='TEST + RENDER DOĞRULA';
   verify.onclick=async()=>{
    verify.disabled=true;notice('GitHub testleri ve Render sürümü kontrol ediliyor…');
    try{const d=await api('/api/dev-requests/'+encodeURIComponent(item.id)+'/verify','POST');
     Object.assign(item,d.request);render();
     notice(statusLabels[item.status]||item.status);
     if(item.status==='completed'&&!seen.has(item.id)){
      seen.add(item.id);
      if($('devAnnounce'))$('devAnnounce').textContent='Tamam efendim, doğrulanmış güncelleme tamamlandı.';
      if(typeof root.speakUltron==='function')root.speakUltron('Tamam efendim, güncelleme tamamlandı.',true);
     }
    }catch(e){notice('Kontrol tamamlanamadı: '+e.message)}
    finally{verify.disabled=false}
   };
   actions.append(copy,open,verify);div.append(h,status,minor,actions);rootList.append(div);
  });
 }
 async function copyRequest(item){
  const text=String(item.handoff||'');
  if(!text)throw Error('Geliştirme metni bulunamadı');
  if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(text);
  else{
   const el=document.createElement('textarea');el.value=text;el.style.position='fixed';
   el.style.top='-1000px';document.body.append(el);el.select();
   try{if(!document.execCommand('copy'))throw Error('Kopyalanamadı')}finally{el.remove()}
  }
  notice('Görev kopyalandı. ChatGPT sohbetine yapıştır ve gönder. Bu adım otomatik değil.');
 }
 function notice(text){const e=$('devNotice');if(e)e.textContent=String(text||'').slice(0,280)}
 async function refresh(){
  if(polling)return;
  polling=true;
  try{const d=await api('/api/dev-requests');latest=d.requests||[];render()}
  catch(e){notice('İstekler yüklenemedi: '+e.message)}
  finally{polling=false}
 }
 async function passiveVerify(){
  if(document.hidden||Date.now()-lastAutoVerification<600000||!latest.length)return;
  const item=latest.find(row=>row.status!=='completed');
  if(!item)return;
  lastAutoVerification=Date.now();
  try{
   const previous=item.status;
   const d=await api('/api/dev-requests/'+encodeURIComponent(item.id)+'/verify','POST');
   if(!d.request)return;
   Object.assign(item,d.request);render();
   if(previous!=='completed'&&item.status==='completed'&&!seen.has(item.id)){
    seen.add(item.id);
    if($('devAnnounce'))$('devAnnounce').textContent='Tamam efendim, test edilen güncelleme doğrulandı.';
    if(typeof root.speakUltron==='function')root.speakUltron('Tamam efendim, güncelleme doğrulandı.',true);
   }
  }catch(e){notice('Otomatik kontrol daha sonra yeniden denenecek: '+e.message)}
 }
 async function fromSpeech(text){
  if(!detect(text)||!text.trim())return false;
  // Streaming Gemini input transcripts can be repeated. Never double insert
  // the same utterance in a Live session.
  const fingerprint=text.toLocaleLowerCase('tr-TR').replace(/\s+/g,' ').trim();
  if(fingerprint===pendingVoice&&Date.now()-voiceAt<120000)return true;
  pendingVoice=fingerprint;voiceAt=Date.now();
  try{
   const item=await create(text,suggestTarget(text));
   notice('İstek Cloud’a kaydedildi. ChatGPT’ye aktarmak için görevini kopyala.');
   if(typeof root.showView==='function')root.showView('develop');
   if(typeof root.toast==='function')root.toast('Geliştirme isteği kaydedildi; ChatGPT’ye aktarmak için onay gerekiyor.');
   return !!item;
  }catch(e){pendingVoice='';notice('Geliştirme isteği kaydedilemedi: '+e.message);return false}
 }
 async function fromText(text){
  if(!detect(text))return false;
  await fromSpeech(text);
  return true;
 }
 function init(){
  const submit=$('devSubmit');if(!submit)return;
  submit.onclick=async()=>{
   const prompt=$('devPrompt').value.trim();
   if(prompt.length<12){notice('İsteğini en az 12 karakterle yaz.');return}
   submit.disabled=true;notice('İstek kaydediliyor…');
   try{await create(prompt,$('devTarget').value);$('devPrompt').value='';notice('Kaydedildi. CHATGPT GÖREVİNİ KOPYALA ve ChatGPT AÇ düğmelerini kullan.')}
   catch(e){notice('Kaydedilemedi: '+e.message)}
   finally{submit.disabled=false}
  };
  $('devRefresh').onclick=()=>refresh();
  root.addEventListener('visibilitychange',()=>{if(!document.hidden&&$('developView').classList.contains('active')){refresh().then(passiveVerify)}});
  setInterval(()=>{if(!document.hidden&&$('developView').classList.contains('active')){refresh().then(passiveVerify)}},600000);
 }
 root.ULTRONDevRequests={init,refresh,fromSpeech,fromText,detect,suggestTarget,
   labels:statusLabels,create,copyRequest,passiveVerify};
})(window);
