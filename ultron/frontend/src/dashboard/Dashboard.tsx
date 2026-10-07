import {lazy,Suspense,useEffect,useRef,useState,type CSSProperties} from 'react';
import {Home,Settings,Gamepad2,Box,Folder,Wrench,Puzzle,Power,Globe,Files,Terminal,Scan,ScanText,Calendar,Code,Activity,Grid2X2,PanelsTopLeft,Mic,MicOff,Send,Square,Trash2,MessageSquare,Command,ShieldCheck,X,Bell} from 'lucide-react';
import {useUltron,request,type CoreState} from './runtime';
import {Panel,ModelPanel,ToolPanel} from './Panels';
import {Brand,SystemRail,FileDrop} from './ReferencePanels';
import CenterStage from './CenterStage';
import './dashboard.css';
const HologramLab=lazy(()=>import('../hologram/HologramLab'));
export default function Dashboard(){
 const u=useUltron(),[modal,setModal]=useState(''),[model,setModel]=useState(''),[input,setInput]=useState(''),[command,setCommand]=useState(''),[busy,setBusy]=useState(false),[localState,setLocalState]=useState<CoreState>('IDLE'),[clock,setClock]=useState(new Date()),[hologram,setHologram]=useState(false),[scale,setScale]=useState(1),[compact,setCompact]=useState(false),[extra,setExtra]=useState(''),[mode,setMode]=useState('general');
 const messages=useRef<HTMLDivElement>(null),abort=useRef<AbortController|null>(null),errorTimer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined);
 useEffect(()=>{const resize=()=>setScale(Math.min(innerWidth/1920,innerHeight/1080));resize();window.addEventListener('resize',resize);const timer=setInterval(()=>setClock(new Date()),1000);return()=>{window.removeEventListener('resize',resize);clearInterval(timer);clearTimeout(errorTimer.current);abort.current?.abort();};},[]);
 useEffect(()=>{messages.current?.scrollTo({top:messages.current.scrollHeight});},[u.messages]);
 const notify=(message:string)=>{u.setNotice(message);setLocalState('ERROR');clearTimeout(errorTimer.current);errorTimer.current=setTimeout(()=>setLocalState('IDLE'),1800);};
 const stageIntent=async(raw:string)=>{
  const t=raw.toLocaleLowerCase('tr-TR').replace(/[’']/g,'').replace(/\s+/g,' ').trim();
  const action=async(operation:string,extra:Record<string,unknown>={})=>await request('/api/stage/command',{operation,...extra});
  const color=(()=>{
   if(/kırmızı|kirmizi|red/.test(t))return '#ff3047';if(/cyan|turkuaz/.test(t))return '#35ffe4';
   if(/mavi|blue/.test(t))return '#268bff';if(/yeşil|yesil|green/.test(t))return '#25ff8a';
   if(/mor|purple/.test(t))return '#a855f7';if(/beyaz|white/.test(t))return '#f5f7ff';
   if(/sarı|sari|yellow/.test(t))return '#ffd43b';if(/turuncu|orange/.test(t))return '#ff8a2b';return '';
  })();
  const durationMatch=t.match(/(\d+(?:[.,]\d+)?)\s*saniye/),duration=durationMatch?Math.max(2,Math.min(15,Number(durationMatch[1].replace(',','.')))):6;
  const current=u.stage.hologram;

  if(/(?:core.?a dön|çekirdeğe dön|orta alanı sıfırla|sahneyi sıfırla)/.test(t)){await action('reset');return 'Center Stage çekirdeğe döndü.';}
  if(/(?:bunu|hologramı|hologrami).*(?:videoya çevir|video yap)/.test(t)){await action('video_from_stage',{duration,title:current.label});return 'Hologram video renderına geçti.';}
  if(/(?:video|animasyon|intro).*(?:yap|oluştur|olustur|render|hazırla|hazirla)/.test(t)){
   let template='ultron_intro';if(/logo/.test(t))template='logo_reveal';else if(/enerji|çekirdek|cekirdek/.test(t))template='energy_core';else if(/sistem.*(?:aktiv|açıl|acil)/.test(t))template='system_activation';else if(/görev|gorev.*tamam/.test(t))template='task_complete';
   await action('video_create',{template,duration,title:/ultron/.test(t)?'ULTRON':current.label||'ULTRON'});return duration+' saniyelik video renderı başladı.';
  }
  if(/(?:videoyu|video).*(?:durdur|duraklat|pause)/.test(t)){await action('video_pause');return 'Video duraklatıldı.';}
  if(/(?:videoyu|video).*(?:oynat|devam|play)/.test(t)){await action('video_play');return 'Video oynatılıyor.';}
  if(/(?:videoyu|video).*(?:kaydet|indir)/.test(t)){await action('video_save');return 'Video kaydetme penceresi açıldı.';}
  if(/(?:hologramı|hologrami|tasarımı|tasarimi).*(?:kaydet|indir)/.test(t)){await action('hologram_save');return 'Hologram projesi kaydediliyor.';}

  const sceneMode=u.stage.mode==='scene_lab';
  const selected=sceneMode?u.stage.scene.objects.find(o=>o.id===u.stage.scene.selected_id):undefined;
  if(/(?:sahne|operasyon masası|operasyon masasi|scene lab).*(?:aç|ac|başlat|baslat|kur|oluştur|olustur)/.test(t)){await action('scene_open');return 'Scene Lab açıldı.';}
  if(/(?:operasyon|taktik).*(?:sahne|masa)/.test(t)){await action('scene_preset',{preset:'operations'});return 'Operasyon sahnesi kuruldu.';}
  if(/araç|arac|vehicle/.test(t)&&/tarama|scan/.test(t)&&/(?:sahne|göster|goster|oluştur|olustur|kur)/.test(t)){await action('scene_preset',{preset:'vehicle_scan'});return 'Araç tarama sahnesi kuruldu.';}
  if(/(?:drone).*(?:hangar|bay|sahne)/.test(t)){await action('scene_preset',{preset:'drone_bay'});return 'Drone sahnesi kuruldu.';}
  if(/(?:gezegen|planet|dünya|dunya).*(?:sahne|sistem)/.test(t)){await action('scene_preset',{preset:'planetary'});return 'Gezegen sahnesi kuruldu.';}
  if(/(?:komuta merkezi|command center|kontrol merkezi).*(?:sahne|kur|oluştur|olustur)?/.test(t)){await action('scene_preset',{preset:'command_center'});return 'Komuta merkezi sahnesi kuruldu.';}
  if(/(?:şehir|sehir|city).*(?:tarama|scan|sahne)/.test(t)){await action('scene_preset',{preset:'city_scan'});return 'Şehir tarama sahnesi kuruldu.';}
  if(/(?:uzay|space).*(?:operasyon|sahne|sistem)/.test(t)){await action('scene_preset',{preset:'space_ops'});return 'Uzay operasyon sahnesi kuruldu.';}
  if(/(?:robotik|robotics|robot laboratuvarı|robot laboratuvari)/.test(t)){await action('scene_preset',{preset:'robotics'});return 'Robotik laboratuvar sahnesi kuruldu.';}

  const multiScene=/\b(?:araba|araç|arac|vehicle|drone|dünya|dunya|globe|küre|kure|enerji|core|network|ağ|ag|logo|kule|tower|robot|robot kolu|uydu|satellite|uçak|ucak|aircraft|bina|building|gemi|ship|radar|portal|küp|kup|cube)\b/.test(t)&&
    (/(?:yanına|yanina|sağına|sagina|soluna|birlikte|ve|ile|iki|üç|uc|sahneye|sahne kur)/.test(t));
  if(multiScene&&/(?:koy|ekle|oluştur|olustur|göster|goster|kur|yerleştir|yerlestir)/.test(t)){
   const specs:Array<Record<string,unknown>>=[];
   const push=(kind:string,label:string,colorValue:string,count=1)=>{for(let i=0;i<count;i++)specs.push({kind,label:count>1?label+' '+(i+1):label,color:colorValue,scale:kind==='globe'?1.05:kind==='vehicle'?1.0:.78});};
   if(/dünya|dunya|globe/.test(t))push('globe','EARTH','#35ffe4');
   if(/araba|araç|arac|vehicle/.test(t))push('vehicle','VEHICLE',color||'#ff3047');
   if(/drone/.test(t)){const count=/(?:iki|2)\s*drone/.test(t)?2:/(?:üç|uc|3)\s*drone/.test(t)?3:1;push('drone','DRONE',color||'#ff3047',count);}
   if(/enerji|core|çekirdek|cekirdek/.test(t))push('energy','CORE',color||'#ff3047');
   if(/network|ağ|ag/.test(t))push('network','NETWORK','#ff3047');
   if(/logo/.test(t))push('logo','ULTRON','#ff3047');
   if(/kule|tower/.test(t))push('tower','TOWER','#ff3047');
   if(/robot kolu|robotic arm/.test(t))push('arm','ARM',color||'#35ffe4');
   else if(/robot/.test(t))push('robot','ROBOT',color||'#ff3047');
   if(/uydu|satellite/.test(t))push('satellite','SATELLITE',color||'#ff3047');
   if(/uçak|ucak|aircraft/.test(t))push('aircraft','AIRCRAFT',color||'#35ffe4');
   if(/bina|building/.test(t))push('building','BUILDING',color||'#ff3047');
   if(/gemi|ship/.test(t))push('ship','SHIP',color||'#dbe6ff');
   if(/radar/.test(t))push('radar','RADAR',color||'#ff3047');
   if(/portal/.test(t))push('portal','PORTAL',color||'#a855f7');
   if(/küp|kup|cube/.test(t))push('cube','CUBE',color||'#ff3047');
   const n=specs.length;specs.forEach((s,i)=>{s.x=(i-(n-1)/2)*2.15;s.y=0;s.z=0;});
   if(specs.length){await action('scene_batch',{objects_json:JSON.stringify(specs),camera:/üstten|ustten|top/.test(t)?'top':/önden|onden|front/.test(t)?'front':'isometric'});return specs.length+' nesneli Scene Lab sahnesi kuruldu.';}
  }

  const projectNameMatch=t.match(/(?:proje|sahne)(?:yi)?\s+["“]?([^"”]+?)["”]?\s+(?:diye|adıyla|adiyla)\s+(?:kaydet|save)/);
  if(sceneMode&&projectNameMatch){await action('scene_project_save',{project_name:projectNameMatch[1].trim().slice(0,80)});return 'Sahne cihaz içi proje olarak kaydedildi.';}
  if(sceneMode&&/(?:sahneyi|scene|bunu).*(?:kaydet|save)/.test(t)){await action('scene_save');return 'Scene Lab projesi kaydediliyor.';}
  if(sceneMode){
   const namedTarget=u.stage.scene.objects.find(o=>{const name=String(o.label||'').toLocaleLowerCase('tr-TR');return name.length>1&&t.includes(name);});
   const selectedCount=u.stage.scene.selected_ids?.length||0;
   const sceneAliases:Record<string,string[]>={
    vehicle:['vehicle','car','araba','araç','arac'],drone:['drone','dron'],globe:['globe','earth','dünya','dunya'],
    radar:['radar'],robot:['robot'],satellite:['satellite','uydu'],aircraft:['aircraft','uçak','ucak'],
    ship:['ship','gemi'],building:['building','bina'],arm:['arm','robot kolu'],tower:['tower','kule'],portal:['portal'],cube:['cube','küp','kup']
   };
   const sceneMentions=u.stage.scene.objects.map(o=>{const terms=[String(o.label||'').toLocaleLowerCase('tr-TR'),...(sceneAliases[o.kind]||[])].filter(Boolean);const pos=Math.min(...terms.map(v=>t.indexOf(v)).filter(v=>v>=0),Number.POSITIVE_INFINITY);return {o,pos};}).filter(x=>Number.isFinite(x.pos)).sort((a,b)=>a.pos-b.pos).map(x=>x.o);
   const sourceMention=sceneMentions[0]||selected,targetMention=sceneMentions.find(x=>x.id!==sourceMention?.id)||null;
   const triggerActionFromText=()=>{if(/x.?ray|röntgen|rontgen/.test(t))return {operation:'scene_render_mode',args:{render_mode:'xray'}};if(/thermal|termal/.test(t))return {operation:'scene_render_mode',args:{render_mode:'thermal'}};if(/blueprint|teknik çizim|teknik cizim/.test(t))return {operation:'scene_render_mode',args:{render_mode:'blueprint'}};if(/scan|tarama/.test(t))return {operation:'scene_animation',args:{animation:'scan'}};if(/hologram/.test(t))return {operation:'scene_render_mode',args:{render_mode:'hologram'}};return null;};
   if(sourceMention&&targetMention&&/(?:yaklaşınca|yaklasinca|yaklaştığında|yaklastiginda|mesafe).*(?:olunca|altına|altina|düşünce|dusunce)?/.test(t)){const actionSpec=triggerActionFromText();if(actionSpec){const m=t.match(/(\d+(?:[.,]\d+)?)\s*(?:birim|unit|metre|m)?/),threshold=m?Number(m[1].replace(',','.')):2;await action('scene_trigger_add',{trigger_name:'NEAR '+sourceMention.label+' → '+targetMention.label,condition_type:'distance_lt',source_id:sourceMention.id,target_id:targetMention.id,threshold,action_operation:actionSpec.operation,action_args:actionSpec.args,once:true});return sourceMention.label+' '+targetMention.label+' nesnesine yaklaşınca çalışacak trigger kuruldu.';}}
   if(sourceMention&&targetMention&&/(?:çarpışınca|carpisinca|çarpıştığında|carpistiginda|collision).*(?:olunca|sonra)?/.test(t)){const actionSpec=triggerActionFromText()||{operation:'scene_animation',args:{animation:'scan'}};await action('scene_trigger_add',{trigger_name:'COLLISION '+sourceMention.label+' ↔ '+targetMention.label,condition_type:'collision',source_id:sourceMention.id,target_id:targetMention.id,action_operation:actionSpec.operation,action_args:actionSpec.args,once:true});return 'Çarpışma trigger’ı kuruldu.';}
   if(/(?:\d+(?:[.,]\d+)?)\s*saniye\s*sonra/.test(t)){const m=t.match(/(\d+(?:[.,]\d+)?)\s*saniye\s*sonra/),delay=m?Number(m[1].replace(',','.')):3,actionSpec=triggerActionFromText();if(actionSpec){await action('scene_trigger_add',{trigger_name:delay+'S TIMER',condition_type:'timer',delay,action_operation:actionSpec.operation,action_args:actionSpec.args,once:true});return delay+' saniyelik trigger kuruldu.';}}
   if(/(?:trigger|tetikleyici).*(?:temizle|sil|sıfırla|sifirla|clear)/.test(t)){await action('scene_trigger_clear');return 'Scene Lab trigger’ları temizlendi.';}
   if(/(?:trigger|tetikleyici).*(?:yeniden kur|reset|arm|tekrar hazırla)/.test(t)){await action('scene_trigger_reset');return 'Scene Lab trigger’ları yeniden arm edildi.';}
   if(/(?:scan reveal|tarama açılışı|tarama acilisi).*(?:senaryo|sequence|sekans|kur|başlat|baslat)|(?:senaryo|sequence|sekans).*(?:scan reveal|tarama)/.test(t)){await action('scene_sequence_preset',{preset:'scan_reveal'});if(/başlat|baslat|oynat|play|çalıştır|calistir/.test(t))await action('scene_sequence_play');return 'Scan Reveal mission sequence hazır'+(/başlat|baslat|oynat|play|çalıştır|calistir/.test(t)?' ve çalışıyor.':'.');}
   if(/(?:target chase|hedef takip).*(?:senaryo|sequence|sekans|kur|başlat|baslat)|(?:senaryo|sequence|sekans).*(?:target chase|hedef takip)/.test(t)){await action('scene_sequence_preset',{preset:'target_chase'});if(/başlat|baslat|oynat|play|çalıştır|calistir/.test(t))await action('scene_sequence_play');return 'Target Chase mission sequence hazır'+(/başlat|baslat|oynat|play|çalıştır|calistir/.test(t)?' ve çalışıyor.':'.');}
   if(/(?:presentation|sunum).*(?:senaryo|sequence|sekans).*(?:kur|başlat|baslat)?|(?:senaryo|sequence|sekans).*(?:presentation|sunum)/.test(t)){await action('scene_sequence_preset',{preset:'presentation'});if(/başlat|baslat|oynat|play|çalıştır|calistir/.test(t))await action('scene_sequence_play');return 'Presentation mission sequence hazır'+(/başlat|baslat|oynat|play|çalıştır|calistir/.test(t)?' ve çalışıyor.':'.');}
   if(/(?:launch|kalkış|kalkis|fırlatma|firlatma).*(?:senaryo|sequence|sekans).*(?:kur|başlat|baslat)?|(?:senaryo|sequence|sekans).*(?:launch|kalkış|kalkis)/.test(t)){await action('scene_sequence_preset',{preset:'launch'});if(/başlat|baslat|oynat|play|çalıştır|calistir/.test(t))await action('scene_sequence_play');return 'Launch mission sequence hazır'+(/başlat|baslat|oynat|play|çalıştır|calistir/.test(t)?' ve çalışıyor.':'.');}
   if(/(?:mission sequence|senaryo|sekans).*(?:videoya|video).*(?:kaydet|çek|cek|record)|(?:videoya|video).*(?:mission sequence|senaryo|sekans).*(?:kaydet|çek|cek|record)?/.test(t)){await action('scene_sequence_record',{title:u.stage.scene.sequence?.name||'ULTRON MISSION'});return 'Mission sequence canlı 3D video olarak kaydediliyor.';}
   if(/(?:mission sequence|senaryo|sekans).*(?:başlat|baslat|oynat|play|çalıştır|calistir)/.test(t)){await action('scene_sequence_play');return 'Mission sequence başlatıldı.';}
   if(/(?:mission sequence|senaryo|sekans).*(?:durdur|stop|pause)/.test(t)){await action('scene_sequence_stop');return 'Mission sequence durduruldu.';}
   if(/(?:mission sequence|senaryo|sekans).*(?:temizle|sil|sıfırla|sifirla|clear)/.test(t)){await action('scene_sequence_clear');return 'Mission sequence temizlendi.';}
   if(/(?:snapshot|checkpoint|geri dönüş noktası|geri donus noktasi).*(?:kaydet|oluştur|olustur|al)/.test(t)){await action('scene_snapshot_save',{snapshot_name:(u.stage.scene.project_name||'Scene')+' snapshot'});return 'Sahne snapshot’ı kaydedildi.';}
   if(/(?:snapshot|checkpoint).*(?:listele|göster|goster)/.test(t)){const res=await action('scene_snapshot_list'),items=Array.isArray(res?.snapshot_result?.snapshots)?res.snapshot_result.snapshots:[];return items.length?items.slice(0,6).map((s:any)=>String(s.name)).join(', '):'Kayıtlı snapshot yok.';}
   if(/(?:son|en son).*(?:snapshot|checkpoint).*(?:dön|don|geri yükle|geri yukle|restore)|(?:snapshot|checkpoint).*(?:sonuncuya|en sonuncuya).*(?:dön|don)/.test(t)){const res=await action('scene_snapshot_list'),items=Array.isArray(res?.snapshot_result?.snapshots)?res.snapshot_result.snapshots:[];if(!items.length)return 'Kayıtlı snapshot yok.';await action('scene_snapshot_restore',{snapshot_id:items[0].id});return 'Son snapshot geri yüklendi.';}
   if(/(?:blueprint|mavi plan|teknik çizim|teknik cizim)/.test(t)){await action('scene_render_mode',{render_mode:'blueprint'});return 'Scene Lab blueprint moduna geçti.';}
   if(/(?:x.?ray|x ışını|x isini|röntgen|rontgen)/.test(t)){await action('scene_render_mode',{render_mode:'xray'});return 'Scene Lab X-ray moduna geçti.';}
   if(/(?:thermal|termal|ısı haritası|isi haritasi)/.test(t)){await action('scene_render_mode',{render_mode:'thermal'});return 'Scene Lab thermal moduna geçti.';}
   if(/(?:solid|katı görünüm|kati gorunum|normal model)/.test(t)){await action('scene_render_mode',{render_mode:'solid'});return 'Scene Lab solid moduna geçti.';}
   if(/(?:hologram modu|holografik görünüm|holografik gorunum|hologram görünüm|hologram gorunum)/.test(t)){await action('scene_render_mode',{render_mode:'hologram'});return 'Scene Lab hologram moduna geçti.';}
   if(sourceMention&&targetMention&&/(?:takip et|takip etsin|peşinden git|pesinden git|follow)/.test(t)){await action('scene_constraint',{object_id:sourceMention.id,constraint:'follow',target_id:targetMention.id,distance:2,constraint_speed:1});return sourceMention.label+' artık '+targetMention.label+' nesnesini takip ediyor.';}
   if(sourceMention&&targetMention&&/(?:etrafında dön|etrafinda don|çevresinde dön|cevresinde don|orbit target|yörüngesinde dön|yorungesinde don)/.test(t)){await action('scene_constraint',{object_id:sourceMention.id,constraint:'orbit_target',target_id:targetMention.id,distance:2.5,constraint_speed:1});return sourceMention.label+' artık '+targetMention.label+' çevresinde dönüyor.';}
   if(sourceMention&&targetMention&&/(?:baksın|baksin|ona bak|look at|yüzünü dön|yuzunu don|hedefe dön|hedefe don)/.test(t)){await action('scene_constraint',{object_id:sourceMention.id,constraint:'look_at',target_id:targetMention.id});return sourceMention.label+' artık '+targetMention.label+' yönüne bakıyor.';}
   if(selected&&/(?:takibi|constraint|hedef takibi).*(?:durdur|kapat|temizle|sil)/.test(t)){await action('scene_constraint',{object_id:selected.id,constraint:'none'});return 'Seçili nesnenin target constraint’i kapatıldı.';}
   if((namedTarget||selected)&&/(?:hedefle|target lock|hedef olarak kilitle|hedefe kilitle)/.test(t)){const target=namedTarget||selected!;await action('scene_target_lock',{object_id:target.id});return target.label+' hedef olarak kilitlendi.';}
   if(/(?:hedef kilidini|target lock).*(?:kaldır|kaldir|temizle|kapat)/.test(t)){await action('scene_target_clear');return 'Hedef kilidi kaldırıldı.';}
   if(selected&&/(?:waypoint|rota noktası|rota noktasi).*(?:ekle|koy|kaydet|işaretle|isaretle)|(?:burayı|burayi).*(?:waypoint|rota noktası|rota noktasi)/.test(t)){await action('scene_waypoint_add',{object_id:selected.id,x:selected.position?.[0]||0,y:selected.position?.[1]||0,z:selected.position?.[2]||0});return 'Seçili nesnenin rotasına waypoint eklendi.';}
   if(selected&&/(?:rotayı|rotayi|waypoint).*(?:başlat|baslat|oynat|takip et|play)/.test(t)){await action('scene_path_play',{object_id:selected.id,path_speed:selected.path?.speed||1,loop:true});return 'Seçili nesnenin waypoint rotası başladı.';}
   if(selected&&/(?:rotayı|rotayi|waypoint).*(?:durdur|pause|stop)/.test(t)){await action('scene_path_stop',{object_id:selected.id});return 'Waypoint rotası durduruldu.';}
   if(selected&&/(?:rotayı|rotayi|waypoint).*(?:temizle|sil|sıfırla|sifirla|clear)/.test(t)){await action('scene_waypoint_clear',{object_id:selected.id});return 'Seçili nesnenin waypoint rotası temizlendi.';}
   if(selectedCount===2&&/(?:mesafe|uzaklık|uzaklik|distance).*(?:ölç|olc|göster|goster|hesapla)|(?:seçtiklerimin|sectiklerimin).*(?:arasını|arasini|mesafesini).*(?:ölç|olc|hesapla)?/.test(t)){const res=await action('scene_measure');const d=Number(res?.measurement_result?.distance);return Number.isFinite(d)?'Seçili nesneler arası mesafe '+d.toFixed(2)+' birim.':'Mesafe ölçümü sahneye eklendi.';}
   if(/(?:ölçüm|olcum|measurement).*(?:temizle|sil|kaldır|kaldir)/.test(t)){await action('scene_measure_clear');return 'Sahne ölçümleri temizlendi.';}
   if(selected&&/(?:bunu|nesneyi|seçileni|secileni).*(?:düşür|dusur|drop)|(?:yerçekimi|yercekimi).*(?:aç|ac|uygula)/.test(t)){await action('scene_physics',{object_id:selected.id,physics_mode:'drop',gravity:9.81,bounce:.45});return 'Seçili nesne fiziksel düşüşe geçti.';}
   if(selected&&/(?:bunu|nesneyi|seçileni|secileni).*(?:fırlat|firlat|launch)/.test(t)){await action('scene_physics',{object_id:selected.id,physics_mode:'launch',vy:5,vx:1.2,gravity:9.81,bounce:.35});return 'Seçili nesne launch fiziğine geçti.';}
   if(selected&&/(?:zero.?g|sıfır yerçekimi|sifir yercekimi|ağırlıksız|agirliksiz)/.test(t)){await action('scene_physics',{object_id:selected.id,physics_mode:'zero_g',vx:.15,vy:.08,vz:.1,gravity:0});return 'Seçili nesne zero-G moduna geçti.';}
   if(selected&&/(?:bunu|nesneyi|seçileni|secileni).*(?:süzdür|suzdur|float|havada yüzdür|havada yuzdur)/.test(t)){await action('scene_physics',{object_id:selected.id,physics_mode:'float',gravity:0});return 'Seçili nesne float moduna geçti.';}
   if(selected&&/(?:fizik|physics|yerçekimi|yercekimi).*(?:kapat|durdur|off|sıfırla|sifirla)/.test(t)){await action('scene_physics',{object_id:selected.id,physics_mode:'off'});return 'Seçili nesnenin fizik simülasyonu kapatıldı.';}
   if(/(?:asset|model kütüphanesi|model kutuphanesi).*(?:listele|göster|goster|aç|ac)/.test(t)){const res=await action('scene_asset_list');const models=Array.isArray(res?.asset_result?.models)?res.asset_result.models:[];return models.length?models.slice(0,8).map((m:any)=>String(m.name)).join(', '):'Asset Library boş.';}
   if(/(?:sahneyi|scene).*(?:kontrol et|analiz et|diagnostic|teşhis|teshis|hata tara)|(?:diagnostic|teşhis|teshis).*(?:sahne|scene)/.test(t)){const res=await action('scene_diagnostics'),d=res?.diagnostics_result;return d?'Sahne: '+(d.objects??0)+' nesne, '+(d.issues?.length??0)+' sorun, '+(d.collisions?.length??0)+' olası çarpışma.':'Sahne analizi tamamlandı.';}
   if(/(?:çarpışma|carpisma|collision).*(?:göster|goster|aç|ac|aktif)/.test(t)){await action('scene_collision_overlay',{enabled:true});return 'Canlı çarpışma overlay’i açıldı.';}
   if(/(?:çarpışma|carpisma|collision).*(?:gizle|kapat|off)/.test(t)){await action('scene_collision_overlay',{enabled:false});return 'Çarpışma overlay’i kapatıldı.';}
   if(/(?:hepsini|tümünü|tumunu|bütününü|butununu).*(?:seç|sec|select all)/.test(t)){await action('scene_multi_select',{selection_mode:'all'});return 'Sahnedeki tüm nesneler seçildi.';}
   if(/(?:seçimi|secimi|selection).*(?:temizle|kaldır|kaldir|clear)/.test(t)){await action('scene_multi_select',{selection_mode:'clear'});return 'Çoklu seçim temizlendi.';}
   if(selectedCount>1&&/(?:seçtiklerimi|sectiklerimi|seçili nesneleri|secili nesneleri).*(?:grupla|grup yap|group)/.test(t)){await action('scene_group_create',{group_name:'GROUP '+((u.stage.scene.groups?.length||0)+1)});return 'Seçili nesneler grup haline getirildi.';}
   if(selectedCount>1&&/(?:seçtiklerimi|sectiklerimi|seçili nesneleri|secili nesneleri).*(?:sağa|saga)/.test(t)){await action('scene_batch_transform',{dx:.6});return 'Seçili nesneler sağa taşındı.';}
   if(selectedCount>1&&/(?:seçtiklerimi|sectiklerimi|seçili nesneleri|secili nesneleri).*(?:sola)/.test(t)){await action('scene_batch_transform',{dx:-.6});return 'Seçili nesneler sola taşındı.';}
   if(selectedCount>1&&/(?:seçtiklerimi|sectiklerimi|seçili nesneleri|secili nesneleri).*(?:yukarı|yukari)/.test(t)){await action('scene_batch_transform',{dy:.5});return 'Seçili nesneler yukarı taşındı.';}
   if(selectedCount>1&&/(?:seçtiklerimi|sectiklerimi|seçili nesneleri|secili nesneleri).*(?:büyüt|buyut)/.test(t)){await action('scene_batch_transform',{scale_factor:1.15});return 'Seçili nesneler büyütüldü.';}
   if(selectedCount>1&&/(?:seçtiklerimi|sectiklerimi|seçili nesneleri|secili nesneleri).*(?:küçült|kucult)/.test(t)){await action('scene_batch_transform',{scale_factor:.87});return 'Seçili nesneler küçültüldü.';}
   if(selectedCount>1&&/(?:x eksen|x axis).*(?:hizala|align)|(?:hizala|align).*(?:x eksen|x axis)/.test(t)){await action('scene_align',{axis:'x',align:'center'});return 'Seçili nesneler X ekseninde hizalandı.';}
   if(selectedCount>1&&/(?:y eksen|y axis).*(?:hizala|align)|(?:hizala|align).*(?:y eksen|y axis)/.test(t)){await action('scene_align',{axis:'y',align:'center'});return 'Seçili nesneler Y ekseninde hizalandı.';}
   if(selectedCount>1&&/(?:z eksen|z axis).*(?:hizala|align)|(?:hizala|align).*(?:z eksen|z axis)/.test(t)){await action('scene_align',{axis:'z',align:'center'});return 'Seçili nesneler Z ekseninde hizalandı.';}
   if(selectedCount>2&&/(?:eşit|esit).*(?:dağıt|dagit|distribute).*(?:x|yatay)/.test(t)){await action('scene_distribute',{axis:'x'});return 'Seçili nesneler X boyunca eşit dağıtıldı.';}
   if(selectedCount>2&&/(?:eşit|esit).*(?:dağıt|dagit|distribute).*(?:z|derinlik)/.test(t)){await action('scene_distribute',{axis:'z'});return 'Seçili nesneler Z boyunca eşit dağıtıldı.';}
   if(selected&&/(?:bundan|bunu).*(\d+)\s*(?:tane|adet).*(?:daire|çember|cember|radial|orbit)/.test(t)){const m=t.match(/(?:bundan|bunu).*?(\d+)\s*(?:tane|adet)/);await action('scene_array',{object_id:selected.id,count:Math.min(12,Math.max(2,Number(m?.[1]||6))),layout:'radial',radius:2.8});return 'Seçili nesneden dairesel array oluşturuldu.';}
   if(selected&&/(?:bundan|bunu).*(\d+)\s*(?:tane|adet).*(?:sıra|sira|line|çizgi|cizgi)/.test(t)){const m=t.match(/(?:bundan|bunu).*?(\d+)\s*(?:tane|adet)/);await action('scene_array',{object_id:selected.id,count:Math.min(12,Math.max(2,Number(m?.[1]||5))),layout:'line',spacing:1.3});return 'Seçili nesneden doğrusal array oluşturuldu.';}
   if(/(?:kamera|camera).*(?:keyframe|anahtar kare)|(?:keyframe|anahtar kare).*(?:kamera|camera)/.test(t)){await action('camera_keyframe_capture');return 'Kamera keyframe’i timeline’a eklendi.';}
   if(/(?:kamera|camera).*(?:track|timeline).*(?:temizle|sil|sıfırla|sifirla)/.test(t)){await action('camera_track_clear');return 'Kamera timeline’ı temizlendi.';}
   if(/(?:kamera|açı|aci).*(?:kaydet|bookmark)/.test(t)){await action('scene_camera_bookmark_save',{bookmark_name:'CAM '+((u.stage.scene.camera_bookmarks?.length||0)+1)});return 'Kamera açısı kaydedildi.';}
   const cameraMark=(u.stage.scene.camera_bookmarks||[]).find(b=>t.includes(String(b.name||'').toLocaleLowerCase('tr-TR')));
   if(cameraMark&&/(?:kamera|açı|aci|dön|don|yükle|yukle|aç|ac)/.test(t)){await action('scene_camera_bookmark_load',{bookmark_id:cameraMark.id});return cameraMark.name+' kamera açısı yüklendi.';}
   if(/(?:tüm sahneye|tum sahneye|hepsine).*(?:keyframe|anahtar kare).*(?:ekle|koy|yakala)/.test(t)){await action('timeline_capture_all',{selection_mode:'all'});return 'Tüm sahnenin keyframe’i yakalandı.';}
   if(namedTarget&&/(?:seç|sec|select)/.test(t)){await action('scene_select',{object_label:namedTarget.label});return namedTarget.label+' seçildi.';}
   if(namedTarget&&/(?:odaklan|focus)/.test(t)){await action('scene_focus',{object_label:namedTarget.label});return 'Kamera '+namedTarget.label+' nesnesine odaklandı.';}
   if(namedTarget&&/(?:kopyala|çoğalt|cogalt|duplicate)/.test(t)){await action('scene_duplicate',{object_label:namedTarget.label});return namedTarget.label+' çoğaltıldı.';}
   if(namedTarget&&/(?:sil|kaldır|kaldir|remove)/.test(t)&&!/(?:hud|link|bağlantı|baglanti)/.test(t)){await action('scene_remove',{object_label:namedTarget.label});return namedTarget.label+' sahneden kaldırıldı.';}
   if(selected&&/(?:hud|bilgi kartı|bilgi karti|data kartı|data karti).*(?:ekle|oluştur|olustur|göster|goster)/.test(t)){const valueMatch=t.match(/(?:değer|deger|value)\s*[:=]?\s*([^,;]+)/);await action('scene_hud_add',{object_id:selected.id,hud_title:/sıcaklık|sicaklik/.test(t)?'TEMP':/hız|hiz/.test(t)?'SPEED':'STATUS',hud_value:valueMatch?.[1]?.trim()||'ONLINE',color:color||selected.color||'#35ffe4'});return 'Seçili nesneye HUD kartı eklendi.';}
   if(/(?:hud|bilgi kartları|bilgi kartlari).*(?:temizle|sil|kaldır|kaldir)/.test(t)){await action('scene_hud_clear');return 'Scene Lab HUD kartları temizlendi.';}
   if(/(?:geri al|undo|son işlemi geri)/.test(t)){await action('scene_undo');return 'Son sahne işlemi geri alındı.';}
   if(/(?:yeniden yap|redo|geri aldığını yap|geri aldigini yap)/.test(t)){await action('scene_redo');return 'Sahne işlemi yeniden uygulandı.';}
   if(selected&&/(?:bunu|nesneyi|seçileni|secileni).*(?:kopyala|çoğalt|cogalt|duplicate)/.test(t)){await action('scene_duplicate',{object_id:selected.id});return 'Seçili nesne çoğaltıldı.';}
   if(selected&&/(?:buna|bunu|nesneye|seçilene|secilene).*(?:odaklan|focus)|(?:kamera).*(?:buna|nesneye).*(?:odaklan|focus)/.test(t)){await action('scene_focus',{object_id:selected.id});return 'Kamera seçili nesneye odaklandı.';}
   if(/(?:odağı|odagi|focus).*(?:kaldır|kaldir|kapat|sıfırla|sifirla)/.test(t)){await action('scene_focus',{object_id:''});return 'Kamera odağı serbest bırakıldı.';}
   if(/(?:hareket yolu|trajectory|trail).*(?:göster|goster|aç|ac)/.test(t)){await action('scene_theme',{theme:u.stage.scene.theme||'crimson',show_trails:true});return 'Hareket yolları gösteriliyor.';}
   if(/(?:hareket yolu|trajectory|trail).*(?:gizle|kapat)/.test(t)){await action('scene_theme',{theme:u.stage.scene.theme||'crimson',show_trails:false});return 'Hareket yolları gizlendi.';}
   if(/(?:sese tepki|sesle tepki|audio reactive|audio fx).*(?:aç|ac|başlat|baslat|aktif)/.test(t)){await action('scene_theme',{theme:u.stage.scene.theme||'crimson',audio_reactive:true});return 'Scene Lab ses tepkisi aktif.';}
   if(/(?:sese tepki|sesle tepki|audio reactive|audio fx).*(?:kapat|durdur|pasif)/.test(t)){await action('scene_theme',{theme:u.stage.scene.theme||'crimson',audio_reactive:false});return 'Scene Lab ses tepkisi kapatıldı.';}
   if(/(?:bütün|tum|tüm|hepsi|hepsini).*(?:bağla|bagla|link)/.test(t)){await action('scene_auto_link',{layout:/zincir|chain/.test(t)?'chain':'star',color:color||'#35ffe4'});return 'Sahne nesneleri holografik bağlantılarla bağlandı.';}
   if(/(?:bağlantı|baglanti|link).*(?:temizle|sil|kaldır|kaldir)/.test(t)){await action('scene_clear_links');return 'Sahne bağlantıları temizlendi.';}
   if(/(?:bağla|bagla|link)/.test(t)){const mentions=u.stage.scene.objects.filter(o=>t.includes(String(o.label||'').toLocaleLowerCase('tr-TR')));if(mentions.length>=2){await action('scene_link',{source_label:mentions[0].label,target_label:mentions[1].label,color:color||'#35ffe4'});return mentions[0].label+' ile '+mentions[1].label+' bağlandı.';}}
   if(selected&&/(?:orbitte dönsün|orbit hareket|çevremde dön|cevremde don)/.test(t)){await action('scene_motion',{object_id:selected.id,motion:'orbit',motion_speed:1,radius:1.5});return 'Seçili nesne orbit hareketine geçti.';}
   if(selected&&/(?:yukarı aşağı|yukari asagi|bob hareket)/.test(t)){await action('scene_motion',{object_id:selected.id,motion:'bob',motion_speed:1,amplitude:.6});return 'Seçili nesne dikey harekete geçti.';}
   if(selected&&/(?:devriye|patrol|sağa sola git|saga sola git)/.test(t)){await action('scene_motion',{object_id:selected.id,motion:'patrol',motion_speed:1,amplitude:1.4});return 'Seçili nesne devriye hareketine geçti.';}
   if(selected&&/(?:nabız|nabiz|pulse).*(?:hareket|yap|ver)/.test(t)){await action('scene_motion',{object_id:selected.id,motion:'pulse',motion_speed:1,amplitude:.8});return 'Seçili nesne pulse animasyonuna geçti.';}
   if(selected&&/(?:hareketi|animasyonu).*(?:durdur|kapat)/.test(t)){await action('scene_motion',{object_id:selected.id,motion:'none'});return 'Seçili nesnenin hareketi durduruldu.';}
   if(selected?.kind==='custom'&&/(?:model|glb).*(?:animasyon|hareket).*(?:durdur|duraklat|pause)/.test(t)){await action('scene_update',{object_id:selected.id,clip_paused:true});return 'Modelin dahili animasyonu duraklatıldı.';}
   if(selected?.kind==='custom'&&/(?:model|glb).*(?:animasyon|hareket).*(?:devam|oynat|play)/.test(t)){await action('scene_update',{object_id:selected.id,clip_paused:false});return 'Modelin dahili animasyonu devam ediyor.';}
   if(selected?.kind==='custom'&&/(?:model|glb).*(?:animasyon|hareket).*(?:hızlandır|hizlandir|daha hızlı|daha hizli)/.test(t)){await action('scene_update',{object_id:selected.id,clip_speed:Math.min(4,(selected.clip_speed??1)*1.35)});return 'Model animasyonu hızlandırıldı.';}
   if(selected?.kind==='custom'&&/(?:model|glb).*(?:animasyon|hareket).*(?:yavaşlat|yavaslat|daha yavaş|daha yavas)/.test(t)){await action('scene_update',{object_id:selected.id,clip_speed:Math.max(0,(selected.clip_speed??1)/1.35)});return 'Model animasyonu yavaşlatıldı.';}
   if(/(?:sahneyi|scene).*(?:analiz modu|analysis mode)|(?:analiz modu|analysis mode).*(?:yap|aç|ac)/.test(t)){await action('scene_director',{preset:'analysis',duration});return 'Scene Director analiz modu aktif.';}
   if(/(?:sahneyi|scene).*(?:savaş|savas|battle|taktik).*(?:mod|yap)|(?:battle mode|savaş modu|savas modu)/.test(t)){await action('scene_director',{preset:'battle',duration});return 'Scene Director battle modu aktif.';}
   if(/(?:sunum|presentation).*(?:mod|yap|sahne)/.test(t)){await action('scene_director',{preset:'presentation',duration});return 'Scene Director sunum modu aktif.';}
   if(/(?:launch sequence|kalkış sekansı|kalkis sekansi|fırlatma sekansı|firlatma sekansi)/.test(t)){await action('scene_director',{preset:'launch',duration});return 'Scene Director launch sekansı aktif.';}
   if(/(?:sahneyi|scene).*(?:showcase|sinematik göster|sinematik goster|etkileyici göster|etkileyici goster)/.test(t)){await action('scene_director',{preset:'showcase',duration});return 'Scene Director showcase modu aktif.';}
   if(/(?:sinematik|cinematic).*(?:kamera|başlat|baslat|aç|ac)/.test(t)){const preset=/spiral/.test(t)?'spiral':/flyby|geçiş|gecis/.test(t)?'flyby':/üstten|ustten/.test(t)?'topdown':/hero|kahraman/.test(t)?'hero':'orbit';await action('scene_cinematic',{cinematic:preset,duration,loop:true});return 'Sinematik kamera başladı.';}
   if(/(?:sinematik|cinematic).*(?:durdur|kapat)/.test(t)){await action('scene_cinematic',{cinematic:'off'});return 'Sinematik kamera durdu.';}
   if(/(?:cyan|turkuaz).*(?:tema|sahne)|(?:tema|sahne).*(?:cyan|turkuaz)/.test(t)){await action('scene_theme',{theme:'cyan'});return 'Scene Lab teması cyan oldu.';}
   if(/(?:mor|purple).*(?:tema|sahne)|(?:tema|sahne).*(?:mor|purple)/.test(t)){await action('scene_theme',{theme:'purple'});return 'Scene Lab teması mor oldu.';}
   if(/(?:amber|turuncu).*(?:tema|sahne)|(?:tema|sahne).*(?:amber|turuncu)/.test(t)){await action('scene_theme',{theme:'amber'});return 'Scene Lab teması amber oldu.';}
   if(/(?:kırmızı|kirmizi|crimson).*(?:tema|sahne)|(?:tema|sahne).*(?:kırmızı|kirmizi|crimson)/.test(t)){await action('scene_theme',{theme:'crimson'});return 'Scene Lab teması crimson oldu.';}
   if(/(?:etiket|label).*(?:kapat|gizle)/.test(t)){await action('scene_theme',{theme:u.stage.scene.theme||'crimson',show_labels:false});return 'Sahne etiketleri gizlendi.';}
   if(/(?:etiket|label).*(?:aç|ac|göster|goster)/.test(t)){await action('scene_theme',{theme:u.stage.scene.theme||'crimson',show_labels:true});return 'Sahne etiketleri açıldı.';}
   if(/(?:grid|ızgara|izgara).*(?:kapat|gizle)/.test(t)){await action('scene_theme',{theme:u.stage.scene.theme||'crimson',grid:false});return 'Sahne grid kapatıldı.';}
   if(/(?:grid|ızgara|izgara).*(?:aç|ac|göster|goster)/.test(t)){await action('scene_theme',{theme:u.stage.scene.theme||'crimson',grid:true});return 'Sahne grid açıldı.';}
   if(/(?:timeline|zaman çizelgesi|zaman cizelgesi).*(?:oynat|başlat|baslat)/.test(t)){await action('timeline_play');return 'Timeline oynatılıyor.';}
   if(/(?:timeline|zaman çizelgesi|zaman cizelgesi).*(?:durdur|duraklat|pause)/.test(t)){await action('timeline_pause');return 'Timeline duraklatıldı.';}
   if(selected&&/(?:keyframe|anahtar kare).*(?:ekle|koy|oluştur|olustur)/.test(t)){await action('timeline_capture');return 'Seçili nesnenin keyframe’i eklendi.';}
   if(selected&&/(?:showcase|vitrin).*(?:animasyon|hareket|yap|oluştur|olustur)/.test(t)){await action('timeline_preset',{preset:'showcase',duration});return 'Showcase timeline oluşturuldu.';}
   if(selected&&/(?:launch|fırlat|firlat|kalkış|kalkis).*(?:animasyon|hareket|yap|oluştur|olustur)/.test(t)){await action('timeline_preset',{preset:'launch',duration});return 'Launch timeline oluşturuldu.';}
   if(selected&&/(?:flyby|geçiş|gecis).*(?:animasyon|hareket|yap|oluştur|olustur)/.test(t)){await action('timeline_preset',{preset:'flyby',duration});return 'Flyby timeline oluşturuldu.';}
   if(/(?:timeline|keyframe).*(?:temizle|sil|sıfırla|sifirla)/.test(t)){await action('timeline_clear');return 'Timeline temizlendi.';}
   if(/(?:sahneyi|hepsini).*(?:videoya çevir|video yap|kaydet.*video|render)/.test(t)){await action('scene_record',{duration,title:'ULTRON SCENE'});return 'Canlı 3D Scene Lab video kaydı başladı.';}
   if(/(?:üstten|ustten|top).*(?:bak|göster|goster|kamera)/.test(t)){await action('scene_camera',{camera:'top'});return 'Kamera üst görünüme geçti.';}
   if(/(?:önden|onden|front).*(?:bak|göster|goster|kamera)/.test(t)){await action('scene_camera',{camera:'front'});return 'Kamera ön görünüme geçti.';}
   if(/(?:yandan|side).*(?:bak|göster|goster|kamera)/.test(t)){await action('scene_camera',{camera:'side'});return 'Kamera yan görünüme geçti.';}
   if(/(?:yakın|yakin|close).*(?:bak|kamera)/.test(t)){await action('scene_camera',{camera:'close'});return 'Kamera yakın görünüme geçti.';}
   if(/orbit.*(?:kamera|bak)|kamera.*orbit/.test(t)){await action('scene_camera',{camera:'orbit',auto_orbit:true});return 'Orbit kamera aktif.';}
   if(/(?:grid|ızgara|izgara).*(?:diz|yerleştir|yerlestir)/.test(t)){await action('scene_arrange',{layout:'grid'});return 'Nesneler grid düzene geçti.';}
   if(/(?:çevre|cevre|orbit).*(?:diz|yerleştir|yerlestir)/.test(t)){await action('scene_arrange',{layout:'orbit'});return 'Nesneler orbit düzene geçti.';}
   if(/(?:sırala|sirala|çizgi|cizgi).*(?:diz|yerleştir|yerlestir)?/.test(t)){await action('scene_arrange',{layout:'line'});return 'Nesneler çizgi halinde dizildi.';}
   if(/(?:tarama|scan).*(?:başlat|baslat|aç|ac)/.test(t)){await action('scene_animation',{animation:'scan'});return 'Sahne taraması başladı.';}
   if(/(?:tarama|scan).*(?:durdur|kapat)/.test(t)){await action('scene_animation',{animation:'idle'});return 'Sahne taraması durdu.';}
   if(/(?:hepsini|sahneyi).*(?:patlat|ayır|ayir|parçala|parcala)/.test(t)){await action('scene_animation',{animation:'explode'});return 'Sahne exploded view moduna geçti.';}
   if(/(?:hepsini|sahneyi).*(?:birleştir|birlestir|topla)/.test(t)){await action('scene_animation',{animation:'assemble'});return 'Sahne tekrar birleştirildi.';}
   if(/(?:sahneyi temizle|hepsini sil)/.test(t)){await action('scene_clear');return 'Scene Lab temizlendi.';}

   if(selected){
    const patch:Record<string,unknown>={object_id:selected.id};
    if(color)patch.color=color;
    if(/(?:sola|sola al|sola taşı|sola tasi)/.test(t))patch.x=(selected.position?.[0]||0)-.6;
    if(/(?:sağa|saga|sağa al|saga al|sağa taşı|saga tasi)/.test(t))patch.x=(selected.position?.[0]||0)+.6;
    if(/(?:yukarı|yukari|kaldır|kaldir)/.test(t))patch.y=(selected.position?.[1]||0)+.5;
    if(/(?:aşağı|asagi|indir)/.test(t)&&!/kaydet|download/.test(t))patch.y=(selected.position?.[1]||0)-.5;
    if(/(?:öne|one|yaklaştır|yaklastir)/.test(t))patch.z=(selected.position?.[2]||0)+.6;
    if(/(?:arkaya|geriye|uzaklaştır|uzaklastir)/.test(t))patch.z=(selected.position?.[2]||0)-.6;
    if(/büyüt|buyut|daha büyük|daha buyuk/.test(t))patch.scale=Math.min(3,selected.scale*1.2);
    if(/küçült|kucult|daha küçük|daha kucuk/.test(t))patch.scale=Math.max(.2,selected.scale/1.2);
    if(/(?:patlat|ayır|ayir|parçala|parcala|parçalarına ayır|parcalarina ayir)/.test(t))patch.explode=1;
    if(/(?:birleştir|birlestir|toparla)/.test(t))patch.explode=0;
    if(/(?:hızlandır|hizlandir|daha hızlı|daha hizli)/.test(t))patch.spin=Math.min(4,(selected.spin||.5)*1.35);
    if(/(?:yavaşlat|yavaslat|daha yavaş|daha yavas)/.test(t))patch.spin=Math.max(-4,(selected.spin||.5)/1.35);
    if(/(?:bunu|nesneyi|seçileni|secileni).*(?:sil|kaldır|kaldir)/.test(t)){await action('scene_remove',{object_id:selected.id});return 'Seçili nesne sahneden kaldırıldı.';}
    if(Object.keys(patch).length>1){await action('scene_update',patch);return 'Seçili sahne nesnesi güncellendi.';}
   }

   const addKind=/(?:ekle|koy|yerleştir|yerlestir)/.test(t)?(/drone/.test(t)?'drone':/araba|araç|arac|vehicle/.test(t)?'vehicle':/dünya|dunya|globe/.test(t)?'globe':/network|ağ|ag/.test(t)?'network':/logo/.test(t)?'logo':/kule|tower/.test(t)?'tower':/enerji|core/.test(t)?'energy':''):'';
   if(addKind){await action('scene_add',{kind:addKind,label:addKind.toUpperCase(),color:color||'#ff3047'});return 'Yeni '+addKind+' nesnesi sahneye eklendi.';}
  }

  const createHolo=/(?:hologram|enerji küresi|enerji kuresi|dünya küresi|dunya kuresi|drone|araç|arac|logo).*(?:yap|oluştur|olustur|göster|goster|tasarla)|(?:ortaya|ortada).*(?:küre|kure|hologram|drone|dünya|dunya|araç|arac|logo)/.test(t);
  if(createHolo){
   let kind='energy';if(/dünya|dunya/.test(t))kind='globe';else if(/ağ|ag|network|node/.test(t))kind='network';else if(/drone/.test(t))kind='drone';else if(/araba|araç|arac|vehicle/.test(t))kind='vehicle';else if(/logo/.test(t))kind='logo';else if(/küre|kure|sphere/.test(t)&&!/enerji/.test(t))kind='sphere';
   const extra:Record<string,unknown>={kind,label:kind==='globe'?'EARTH':kind==='logo'?'ULTRON':kind.toUpperCase()};if(color)extra.color=color;
   await action('hologram_create',extra);return 'Hologram Center Stage üzerinde oluşturuldu.';
  }

  const controlHolo=u.stage.mode==='hologram_lab'&&/(?:bunu|hologram|küre|kure|sahne)/.test(t);
  if(controlHolo){
   const patch:Record<string,unknown>={};
   if(color)patch.color=color;
   if(/büyüt|buyut|daha büyük|daha buyuk/.test(t))patch.scale=Math.min(2.5,current.scale*1.2);
   if(/küçült|kucult|daha küçük|daha kucuk/.test(t))patch.scale=Math.max(.25,current.scale/1.2);
   if(/hızlandır|hizlandir|daha hızlı|daha hizli/.test(t))patch.speed=Math.min(5,current.speed*1.3);
   if(/yavaşlat|yavaslat|daha yavaş|daha yavas/.test(t))patch.speed=Math.max(.05,current.speed/1.3);
   if(/wireframe|tel kafes/.test(t))patch.wireframe=!/kapat|çıkar|cikar|solid/.test(t);
   if(/pulse|nabız|nabiz/.test(t))patch.pulse=!/kapat|durdur/.test(t);
   const ring=t.match(/(\d+)\s*(?:halka|ring)/);if(ring)patch.rings=Math.max(0,Math.min(12,Number(ring[1])));
   else if(/halka.*(?:ekle|artır|artir)/.test(t))patch.rings=Math.min(12,current.rings+2);
   if(Object.keys(patch).length){await action('hologram_update',patch);return 'Hologram güncellendi.';}
  }
  return '';
 };
 const send=async(text=input)=>{if(!text.trim()||busy)return;setInput('');setCommand('');if(model==='native'){if(u.native)u.native.send(text);return;}u.add('user',text);
  try{const stageReply=await stageIntent(text);if(stageReply){u.add('assistant',stageReply);return;}}catch(e){notify((e as Error).message);return;}
  setBusy(true);setLocalState('THINKING');const ctl=new AbortController();abort.current=ctl;
  try{const r=await request('/api/merged/invoke',{text,mode,...(model?{model}:{})},ctl.signal);u.add('assistant',r.text||JSON.stringify(r));setLocalState('IDLE');}catch(e){notify((e as Error).message);}finally{setBusy(false);abort.current=null;}};
 const state:CoreState=localState!=='IDLE'?localState:u.state!=='IDLE'?u.state:u.taskState!=='IDLE'?u.taskState:u.nativeState;
 const stop=()=>{abort.current?.abort();u.native?.action('interrupt');};
 useEffect(()=>{const key=(e:KeyboardEvent)=>{if(e.key==='Escape'){stop();setModal('');}};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[u.native]);
 const review=async(path:string,id:string)=>{try{await request(path,{id});u.setPending(null);u.setPatch(null);}catch(e){notify((e as Error).message);}};
 const run=async(path:string,body?:unknown)=>{try{setExtra(JSON.stringify(await request(path,body),null,2));}catch(e){notify((e as Error).message);}};
 const open=(name:string)=>{setModal(name);setExtra('');if(name==='Eklentiler'){u.native?.action('plugins');void run('/api/skills');}if(name==='Araçlar')void run('/api/tools');if(name==='Kontroller')void run('/api/voice/wake');};
 const holo=()=>{void request('/api/stage/command',{operation:'hologram_create',kind:u.stage?.hologram?.kind||'energy'}).catch(e=>notify((e as Error).message));};
 const ready=(value:unknown)=>u.connected?(value?'ONLINE':'N/A'):'OFFLINE';
 const chipsLeft=[['SYSTEM',u.connected?'ONLINE':'OFFLINE'],['MEMORY',ready(u.memory)],['TASK ENGINE',ready(u.health?.components?.task_engine)],['VISION',ready(u.ai?.vision)],['AUDIO',u.native?(u.muted?'MUTED':u.nativeState):'N/A']];
 const chipsRight=[['AI CORE',ready(u.health?.components?.brain)],['NEURAL LINK',ready(u.ai?.connected)],['TOOLS',u.connected?`${u.tools.filter(t=>t.status==='READY').length} READY`:'N/A'],['PLUGINS',u.plugins?`${u.plugins.length} LOADED`:'N/A'],['MONITOR',u.system?'LIVE':'N/A']];
 const disabledSend=busy||!u.connected&&model!=='native';
 const footer=[['Web Tarayıcı',Globe,()=>open('Browser')],['Dosya İşlemleri',Files,()=>open('Dosyalar')],['Terminal',Terminal,()=>open('Terminal')],['Ekran Yakalama',Scan,()=>{open('Vizyon');void run('/api/actions/screenshot',{});}],['OCR',ScanText,()=>{open('Vizyon');void run('/api/merged/tool',{name:'screen_ocr',arguments:{}});}],['Planlayıcı',Calendar,()=>open('Görevler')],['Kod Asistanı',Code,()=>{setMode('coding');open('Kod Asistanı');}],['Sistem Monitörü',Activity,()=>open('Sistem Monitörü')]] as const;
 return <div className="viewport"><div className={'ultron-app '+(compact?'compact':'')} style={{transform:`translate(-50%,-50%) scale(${scale})`}}>
 <header className="main-header metal-frame"><Brand/><nav>
 <button className={!modal?'selected':''} onClick={()=>setModal('')}><Home/>Ana Ekran</button>
 <button onClick={()=>open('Ayarlar')}><Settings/>Ayarlar</button><button onClick={()=>open('Kontroller')}><Gamepad2/>Kontroller</button>
 <button onClick={holo}><Box/>Hologram Çalışma Alanı</button><button onClick={()=>open('Dosyalar')}><Folder/>Dosyalar</button><button onClick={()=>open('Araçlar')}><Wrench/>Araçlar</button><button onClick={()=>open('Eklentiler')}><Puzzle/>Eklentiler</button>
 </nav><time>{clock.toLocaleTimeString('tr-TR')}<small>{clock.toLocaleDateString('tr-TR',{day:'2-digit',month:'short',year:'numeric'})}<br/>{clock.toLocaleDateString('tr-TR',{weekday:'long'})}</small></time><button className="power" aria-label="ULTRON'u kapat" disabled={!u.native} onClick={()=>u.native?.action('shutdown')}><Power/></button></header>
 <main className="main-grid"><SystemRail system={u.system} history={u.history} health={u.health} connected={u.connected}/>
 <section className="reactor-panel metal-frame"><CenterStage stage={u.stage} state={state} amplitude={u.amplitude} notify={notify}/>{u.stage.mode==='core_idle'&&<><div className="subsystems left">{chipsLeft.map(([label,value])=><div key={label} className={value==='OFFLINE'||value==='N/A'?'unavailable':''}><i/>{label}<b>{value}</b></div>)}</div><div className="subsystems right">{chipsRight.map(([label,value])=><div key={label} className={value==='OFFLINE'||value==='N/A'?'unavailable':''}><i/>{label}<b>{value}</b></div>)}</div></>}{!u.connected&&<div className="offline" role="status">ULTRON BACKEND OFFLINE</div>}</section>
 <aside className="right-panels"><Panel title="KONUŞMA / AKTİVİTE" icon={<MessageSquare/>} className="chat-panel" extra={<button disabled={busy} onClick={()=>u.setMessages([])}><Trash2/>Temizle</button>}><div className="messages" ref={messages}>{!u.messages.length&&<p className="chat-empty">{u.connected?'ULTRON bağlantısı kuruldu. Bir komut yaz veya sor.':'Backend bağlantısı bekleniyor…'}</p>}{u.messages.map(m=><article className={'message '+m.role} key={m.id}><time>{new Date(m.time).toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'})}</time><p><b>{m.role==='user'?'You':'ULTRON'}:</b> {m.text}</p></article>)}{busy&&<p className="muted">Yanıt hazırlanıyor…</p>}</div><form className="composer" onSubmit={e=>{e.preventDefault();void send();}}><input aria-label="Mesaj" value={input} onChange={e=>setInput(e.target.value)} placeholder="Bir komut yaz veya sor…"/><button aria-label="Gönder" disabled={disabledSend||!input.trim()}><Send/></button></form></Panel>
 <FileDrop notify={notify} ask={send} nativeFile={u.native?()=>u.native?.action('file'):undefined}/>
 <Panel title="KOMUT" icon={<Command/>} className="command-panel"><form onSubmit={e=>{e.preventDefault();void send(command);}}><button type="button" className="mic-circle" aria-label="Mikrofon" disabled={!u.native} onClick={()=>u.native?.action('mute')}>{u.muted?<MicOff/>:<Mic/>}</button><input aria-label="Komut" value={command} onChange={e=>setCommand(e.target.value)} placeholder="Komut yaz…"/><button aria-label="Komutu gönder" disabled={disabledSend||!command.trim()}><Send/></button></form><button className="interrupt" onClick={stop}><Square/>KONUŞMAYI DURDUR <span>[ESC]</span></button><button className={'voice-status '+(u.native&&!u.muted?'active':'')} disabled={!u.native} onClick={()=>u.native?.action('mute')}><Mic/>{u.native?(u.muted?'MİKROFON KAPALI':state==='THINKING'?'İŞLENİYOR':'MİKROFON AKTİF'):'MİKROFON N/A'}</button></Panel></aside></main>
 <footer className="bottom-toolbar metal-frame">{footer.map(([name,Icon,action])=><button key={name} onClick={action}><Icon/>{name}</button>)}<div className="view-buttons"><button aria-label="Panel yoğunluğunu değiştir" aria-pressed={compact} onClick={()=>setCompact(!compact)}><PanelsTopLeft/></button><button aria-label="Çalışma alanlarını aç" onClick={()=>open('Araçlar')}><Grid2X2/></button></div></footer>
 {modal&&<div className="modal-shade"><section className="work-dialog metal-frame" role="dialog" aria-modal="true" aria-label={modal}><header><h2>{modal}</h2><button aria-label="Paneli kapat" onClick={()=>setModal('')}><X/></button></header><div className="dialog-content">
 {['Ayarlar','Kod Asistanı'].includes(modal)&&<><ModelPanel ai={u.ai} model={model} setModel={setModel} native={u.native}/><label>Yanıt modu<select aria-label="Yanıt modu" value={mode} onChange={e=>setMode(e.target.value)}><option value="general">Genel</option><option value="coding">Kod</option><option value="fast">Hızlı</option><option value="agent">Araç kullanan agent</option></select></label><button onClick={()=>open('Hafıza')}>Hafıza</button><button onClick={()=>open('Bildirimler')}>Bildirimler</button></>}
 {modal==='Kontroller'&&<><div className="control-buttons"><button disabled={!u.native} onClick={()=>u.native?.action('mute')}>{u.muted?'Mikrofonu aç':'Mikrofonu kapat'}</button><button disabled={!u.native} onClick={()=>u.native?.action('audio')}>Ses aygıtları</button><button disabled={!u.native} onClick={()=>u.native?.action('camera')}>Kamera</button><button disabled={!u.native} onClick={()=>u.native?.action('controls')}>Wake / bas konuş kontrolleri</button></div><h3>Telefon Kontrolü</h3><p className="muted">{(()=>{const phone=u.devicePresence.find((d:any)=>d.device==='phone');return phone?.online?'Telefon ULTRON: ONLINE'+(phone?.state?.view?' • '+phone.state.view.toUpperCase():''):'Telefon ULTRON: OFFLINE';})()}</p><div className="control-buttons"><button disabled={!u.native} onClick={()=>u.native?.action('phone:ping')}>Bağlantı sinyali</button><button disabled={!u.native} onClick={()=>u.native?.action('phone:vibrate')}>Telefonu titreştir</button><button disabled={!u.native} onClick={()=>u.native?.action('phone:refresh')}>Telefon ULTRON'u yenile</button><button disabled={!u.native} onClick={()=>u.native?.action('phone:focus_chat')}>Sohbeti aç</button><button disabled={!u.native} onClick={()=>u.native?.action('phone:open_memory')}>Hafızayı aç</button><button disabled={!u.native} onClick={()=>u.native?.action('phone:open_remote')}>Uzaktan kontrolü aç</button><button disabled={!u.native} onClick={()=>u.native?.action('phone:scroll_top')}>Sayfanın başına git</button></div><p className="muted">Bu panel telefonun ULTRON web arayüzünü yönetir. iOS sisteminin kendi izinleri ayrı kalır.</p></>}
 {modal==='Araçlar'&&<><div className="tool-grid">{['Browser','Dosyalar','Terminal','Vizyon','Görevler','Hafıza','Ayarlar','Kod Asistanı'].map(n=><button key={n} onClick={()=>open(n)}>{n}</button>)}</div><h3>Center Stage</h3><div className="control-buttons"><button onClick={()=>void request('/api/stage/command',{operation:'hologram_create',kind:'energy'})}>Enerji hologramı</button><button onClick={()=>void request('/api/stage/command',{operation:'hologram_create',kind:'globe'})}>Dünya hologramı</button><button onClick={()=>void request('/api/stage/command',{operation:'video_create',template:'ultron_intro',duration:6,title:'ULTRON'})}>ULTRON intro render</button><button onClick={()=>void request('/api/stage/command',{operation:'reset'})}>Core'a dön</button><button onClick={()=>setHologram(true)}>Gelişmiş Hologram Lab</button></div></>}
 {modal==='Eklentiler'&&<><h3>Yerel eklenti kayıtları</h3><pre>{u.plugins?JSON.stringify(u.plugins,null,2):'Native eklenti kaydı N/A'}</pre><h3>Backend becerileri</h3></>}
 {modal==='Sistem Monitörü'&&<pre>{JSON.stringify(u.system??{status:'N/A'},null,2)}</pre>}
 {modal==='Bildirimler'&&<pre>{u.notifications.length?JSON.stringify(u.notifications,null,2):'Bildirim yok.'}</pre>}
 {['Dosyalar','Terminal','Browser','Vizyon','Görevler','Otomasyon','Hafıza','Ayarlar'].includes(modal)&&<ToolPanel key={modal} tab={modal} native={u.native} notify={notify} ask={send}/>}
 {extra&&<pre className="tool-output">{extra}</pre>}
 </div></section></div>}
 {(u.pending||u.patch)&&<div className="modal-shade approval-shade"><section className="work-dialog metal-frame" role="dialog" aria-label="İşlem onayı"><header><h2><ShieldCheck/> İşlem onayı gerekiyor</h2></header><div className="dialog-content"><pre>{JSON.stringify(u.pending??u.patch,null,2)}</pre><p>Yalnız inceleyip kabul ettiğiniz işlemi onaylayın.</p><button onClick={()=>review(u.pending?'/api/task/reject':'/api/codegen/reject',(u.pending??u.patch)!.id)}>Reddet</button><button onClick={()=>review(u.pending?'/api/task/approve':'/api/codegen/apply',(u.pending??u.patch)!.id)}>İnceledim, onayla</button></div></section></div>}
 {u.notice&&<div className="toast" role="alert">{u.notice}<button aria-label="Uyarıyı kapat" onClick={()=>u.setNotice('')}>×</button></div>}
 {hologram&&<Suspense fallback={<div className="modal-shade">Hologram yükleniyor…</div>}><HologramLab accent="#ff3047" onClose={()=>setHologram(false)} onAsk={send}/></Suspense>}
 </div></div>;
}
