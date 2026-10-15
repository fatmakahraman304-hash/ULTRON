import {Activity,Camera,Cloud,Code,FileText,Globe2,MessageSquare,Monitor,Radio,Terminal,Wifi} from 'lucide-react';
import {useState} from 'react';
import {EarthWatch} from './EarthWatch';
import type {AIStatus,SystemSnapshot} from '../lib/types';
import type {CoreState,EarthState,Native,StageState} from './runtime';

type Props={
 system:SystemSnapshot|null;ai:AIStatus|null;health:any;connected:boolean;native:Native|null;
 devicePresence:any[];notifications:any[];stage:StageState;taskState:CoreState;
 onBack:()=>void;onOpen:(name:string)=>void;notify:(message:string)=>void;
};
const percent=(v:unknown)=>typeof v==='number'&&Number.isFinite(v)?`${v.toFixed(0)}%`:'Kullanılamıyor';
const amount=(v:unknown,suffix='')=>typeof v==='number'&&Number.isFinite(v)?`${v.toFixed(1)}${suffix}`:'Kullanılamıyor';
function safeEvent(value:unknown){
 return String(value??'').replace(/(api[_ -]?key|token|password|secret|authorization)\s*[:=]\s*[^\s,;]+/gi,'$1=[gizlendi]').replace(/\b(Bearer|Basic)\s+[^\s,;]+/gi,'$1 [gizlendi]').replace(/\b(?:AIza[0-9A-Za-z_-]{20,}|sk-[A-Za-z0-9_-]{16,})\b/g,'[gizlendi]').replace(/[\r\n\t]+/g,' ').slice(0,240);
}
function Device({icon:Icon,title,status,detail}:{icon:typeof Monitor;title:string;status:string;detail:string}){
 return <div className="cc-device"><Icon aria-hidden="true"/><div><b>{title}</b><small>{detail}</small></div><span className={status==='Çevrimiçi'?'online':''}>{status}</span></div>;
}
export default function ControlCenter({system,ai,health,connected,native,devicePresence,notifications,stage,taskState,onBack,onOpen,notify}:Props){
 const [earth,setEarth]=useState<EarthState>(stage.earth);
 const mapCommand=(operation:string,extra:Record<string,unknown>={})=>{
  if(operation==='earth_control'){setEarth(previous=>({...previous,...extra} as EarthState));return;}
  if(operation==='earth_focus'){
   const lat=Number(extra.lat),lon=Number(extra.lon);if(!Number.isFinite(lat)||!Number.isFinite(lon)){notify('Koordinat geçersiz.');return;}
   const place=String(extra.place||extra.label||'HEDEF');
   setEarth(previous=>({...previous,focus_lat:Math.max(-90,Math.min(90,lat)),focus_lon:((lon+180)%360+360)%360-180,focus_label:place,auto_rotate:place.toUpperCase()==='GLOBAL'}));return;
  }
  if(operation==='earth_marker_add'){
   const lat=Number(extra.lat),lon=Number(extra.lon);if(!Number.isFinite(lat)||!Number.isFinite(lon)){notify('Koordinat geçersiz.');return;}
   const marker={id:`local-${Date.now()}`,lat:Math.max(-90,Math.min(90,lat)),lon:((lon+180)%360+360)%360-180,label:String(extra.label||'PIN').slice(0,40),color:String(extra.color||'#35ffe4')};
   setEarth(previous=>({...previous,markers:[...previous.markers.slice(-19),marker]}));
  }
  if(operation==='earth_marker_clear')setEarth(previous=>({...previous,markers:[]}));
 };
 const phone=devicePresence.find((d:any)=>String(d.device||'').toLowerCase()==='phone');
 const desktop=devicePresence.find((d:any)=>['desktop','laptop','windows'].includes(String(d.device||'').toLowerCase()));
 const temperatures=Object.entries(system?.temps??{}).slice(0,3);
 const metrics=[
  ['CPU',percent(system?.cpu?.percent),system?.cpu?.freq_mhz?`${amount(system.cpu.freq_mhz,' MHz')}`:'Frekans kullanılamıyor'],
  ['RAM',percent(system?.ram?.percent),system?.ram?`${amount(system.ram.used_gb,' / ')}${amount(system.ram.total_gb,' GB')}`:'Kapasite kullanılamıyor'],
  ['Disk',percent(system?.disk?.percent),system?.disk?`${amount(system.disk.used_gb,' / ')}${amount(system.disk.total_gb,' GB')}`:'Kapasite kullanılamıyor'],
  ['GPU',system?.gpu?percent(system.gpu.util):'Kullanılamıyor',system?.gpu?`${system.gpu.name} · ${amount(system.gpu.mem_used_mb,' / ')}${amount(system.gpu.mem_total_mb,' MB')}`:'GPU sensörü yok'],
  ['Ağ',system?.net?`↓ ${amount(system.net.down_mbps,' Mbps')}`:'Kullanılamıyor',system?.net?`↑ ${amount(system.net.up_mbps,' Mbps')}`:'Ağ sensörü yok']
 ] as const;
 return <section className="control-center-view" aria-label="GÖLGE kontrol merkezi">
  <header className="cc-header"><div><small>GÖLGE / LAPTOP</small><h1>Kontrol Merkezi</h1><p>Canlı telemetri, bağlı cihazlar ve görev durumu</p></div><button className="cc-back" onClick={onBack}><MessageSquare/> Normal sohbete dön</button></header>
  <div className="cc-grid">
   <aside className="cc-column cc-left">
    <section className="cc-card"><header><Activity/><h2>Sistem durumu</h2><span className={connected?'cc-live':''}>{connected?'GÜNCEL':'BAĞLI DEĞİL'}</span></header>
     <div className="cc-metrics">{metrics.map(([name,value,detail])=><div className="cc-metric" key={name}><div><b>{name}</b><strong>{value}</strong></div><small>{detail}</small>{value.endsWith('%')&&<i><span style={{width:value}}/></i>}</div>)}</div>
     <div className="cc-extra"><span>İşletim sistemi <b>{system?.os||'Kullanılamıyor'}</b></span><span>Çalışma süresi <b>{typeof system?.uptime_s==='number'?`${Math.floor(system.uptime_s/3600)} sa ${Math.floor(system.uptime_s%3600/60)} dk`:'Kullanılamıyor'}</b></span>
      {system?.gpu?.temp_c!=null&&<span>GPU sıcaklığı <b>{amount(system.gpu.temp_c,' °C')}</b></span>}
      {temperatures.length?temperatures.map(([key,value])=><span key={key}>{key} sıcaklığı <b>{amount(value,' °C')}</b></span>):<span>İşlemci sıcaklığı <b>Kullanılamıyor</b></span>}
      <span>Fan hızı <b>Kullanılamıyor</b></span>
     </div>
    </section>
    <section className="cc-card"><header><Radio/><h2>Model ve bağlantı</h2></header>
     <div className="cc-model"><span>Yerel model</span><b>{ai?.connected?(ai.primary||ai.models?.[0]||'Bağlı; model adı yok'):'Bağlı değil'}</b></div>
     <div className="cc-model"><span>Bulut servisi</span><b>{connected&&health?'Bağlantı var':'Durum doğrulanamadı'}</b></div>
     <div className="cc-model"><span>Ses durumu</span><b>{native?taskState:'Bu cihazda yerel ses köprüsü yok'}</b></div>
    </section>
   </aside>
   <section className="cc-center">
    <section className="cc-map-card"><header><Globe2/><div><h2>Dünya görünümü</h2><small>3D küre · kaynaklı veri katmanları</small></div></header>
     <EarthWatch config={earth} showCoreButton={false} showMapButton={false} onCommand={mapCommand}/>
     <p className="cc-map-note">Küre ve koordinat seçimi etkileşimlidir. Bu geçici harita görünümü sohbet sahnesini değiştirmez. ISS katmanı yalnızca API yanıtı doğrulanırsa LIVE olur; hava durumu ve uçuş verisi bu arayüzde yapılandırılmamıştır.</p>
    </section>
    <section className="cc-card cc-actions"><header><Activity/><h2>Hızlı işlemler</h2></header>
     <div className="cc-action-grid">
      <button onClick={()=>onOpen('Sistem Monitörü')}><Activity/>Sistem analizi</button>
      <button onClick={()=>onOpen('Kod Asistanı')}><Code/>Kod görevleri</button>
      <button onClick={()=>onOpen('Dosyalar')}><FileText/>Dosyalar</button>
      <button onClick={()=>onOpen('Terminal')}><Terminal/>İzinli terminal aracı</button>
      <button disabled={!native} title={native?'Kamera erişimi yerel izin penceresini kullanır':'Yerel kamera köprüsü bağlı değil'} onClick={()=>native?.action('camera')}><Camera/>Kamerayı aç</button>
     </div>
    </section>
   </section>
   <aside className="cc-column cc-right">
    <section className="cc-card"><header><Wifi/><h2>Bağlı cihazlar</h2></header>
     <Device icon={Monitor} title="Laptop" status={native||desktop?.online?'Çevrimiçi':desktop?.online===false?'Çevrimdışı':'Durum bilinmiyor'} detail={system?.platform||system?.os||'Yerel telemetri yok'}/>
     <Device icon={MessageSquare} title="iPhone" status={phone?.online===true?'Çevrimiçi':phone?.online===false?'Çevrimdışı':'Durum bilinmiyor'} detail={phone?.state?.view?String(phone.state.view):'Heartbeat kaydı yok'}/>
     <Device icon={Cloud} title="GÖLGE bulut" status={connected&&health?'Çevrimiçi':'Doğrulanamadı'} detail={health?.version?`Servis ${String(health.version)}`:'Servis sağlık kaydı yok'}/>
    </section>
    <section className="cc-card cc-events"><header><Terminal/><h2>Durum olayları</h2><span>{notifications.length}</span></header>
     {notifications.length?notifications.slice(-12).reverse().map((event:any,index:number)=><article key={`${event.ts||event.time||index}-${index}`}><time>{Number.isFinite(Number(event.ts))?new Date(Number(event.ts)*1000).toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'}):'—'}</time><p>{safeEvent(event.text||event.message||event.kind||'Durum olayı')}</p></article>):<p className="cc-empty">Henüz yayınlanmış durum olayı yok.</p>}
     <small>Bu liste gerçek uygulama olaylarından gelir; parola ve token benzeri değerler gizlenir. Shell erişimi bu panelden açılmaz.</small>
    </section>
   </aside>
  </div>
 </section>;
}
