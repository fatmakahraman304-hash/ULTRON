import {Activity,Camera,Cloud,Code,FileText,Globe2,MessageSquare,Monitor,Radio,Settings,ShieldCheck,Terminal,Wifi} from 'lucide-react';
import {useEffect,useState,type CSSProperties,type ReactNode} from 'react';
import {EarthWatch} from './EarthWatch';
import {cloudConnection} from './connectionStatus';
import type {AIStatus,SystemSnapshot} from '../lib/types';
import type {CoreState,EarthState,Native,StageState} from './runtime';

type Props={system:SystemSnapshot|null;ai:AIStatus|null;health:any;connected:boolean;native:Native|null;devicePresence:any[];notifications:any[];stage:StageState;taskState:CoreState;onBack:()=>void;onOpen:(name:string)=>void;notify:(message:string)=>void;mapRequest?:{id:number;operation:string;args:Record<string,unknown>};composer?:ReactNode};
const amount=(v:unknown,suffix='')=>typeof v==='number'&&Number.isFinite(v)?`${v.toFixed(1)}${suffix}`:'Kullanılamıyor';
function safeEvent(value:unknown){return String(value??'').replace(/(api[_ -]?key|token|password|secret|authorization)\s*[:=]\s*[^\s,;]+/gi,'$1=[gizlendi]').replace(/\b(Bearer|Basic)\s+[^\s,;]+/gi,'$1 [gizlendi]').replace(/\b(?:AIza[0-9A-Za-z_-]{20,}|sk-[A-Za-z0-9_-]{16,})\b/g,'[gizlendi]').replace(/[\r\n\t]+/g,' ').slice(0,240);}
function Device({icon:Icon,title,status,detail,online=false}:{icon:typeof Monitor;title:string;status:string;detail:string;online?:boolean}){return <div className="cc-device"><Icon aria-hidden="true"/><div><b>{title}</b><small>{detail}</small></div><span className={online?'online':''}><i/>{status}</span></div>;}
export default function ControlCenter({system,ai,health,connected,native,devicePresence,notifications,stage,taskState,onBack,onOpen,notify,mapRequest,composer}:Props){
 const [earth,setEarth]=useState<EarthState>({...stage.earth,grid:true});
 const mapCommand=(operation:string,extra:Record<string,unknown>={})=>{
  if(operation==='earth_control'){setEarth(previous=>({...previous,...extra} as EarthState));return;}
  if(operation==='earth_focus'){
   const lat=Number(extra.lat),lon=Number(extra.lon);if(!Number.isFinite(lat)||!Number.isFinite(lon)){notify('Koordinat geçersiz.');return;}
   const place=String(extra.place||extra.label||'HEDEF');setEarth(previous=>({...previous,focus_lat:Math.max(-90,Math.min(90,lat)),focus_lon:((lon+180)%360+360)%360-180,focus_label:place,auto_rotate:place.toUpperCase()==='GLOBAL'}));return;
  }
  if(operation==='earth_marker_add'){
   const lat=Number(extra.lat),lon=Number(extra.lon);if(!Number.isFinite(lat)||!Number.isFinite(lon))return;
   setEarth(previous=>({...previous,markers:[...previous.markers.slice(-19),{id:`local-${Date.now()}`,lat:Math.max(-90,Math.min(90,lat)),lon:((lon+180)%360+360)%360-180,label:String(extra.label||'PIN').slice(0,40),color:'#35caff'}]}));
  }
  if(operation==='earth_marker_clear')setEarth(previous=>({...previous,markers:[]}));
 };
 useEffect(()=>{if(mapRequest)mapCommand(mapRequest.operation,mapRequest.args);},[mapRequest]);
 const phone=devicePresence.find((d:any)=>String(d.device||'').toLowerCase()==='phone'),cloud=cloudConnection(health);
 const source=system?.platform?(system.platform==='Windows'?'Windows laptop':`${system.platform} servis ortamı`):'Telemetri kaynağı';
 const metrics=[{name:'CPU',value:system?.cpu?.percent,detail:system?.cpu?.freq_mhz?amount(system.cpu.freq_mhz,' MHz'):'Sensör bekleniyor'},{name:'RAM',value:system?.ram?.percent,detail:system?.ram?`${amount(system.ram.used_gb)} / ${amount(system.ram.total_gb)} GB`:'Sensör bekleniyor'},{name:'DİSK',value:system?.disk?.percent,detail:system?.disk?`${amount(system.disk.used_gb)} / ${amount(system.disk.total_gb)} GB`:'Sensör bekleniyor'},{name:'GPU',value:system?.gpu?.util,detail:system?.gpu?.name||'Sensör kullanılamıyor'}];
 const temperature=Object.values(system?.temps??{})[0];
 return <section className="control-center-view" aria-label="GÖLGE kontrol merkezi">
  <header className="cc-header"><div><small>GÖLGE / KONTROL MERKEZİ</small><h1>Her şey, tek bir bakışta.</h1><p>{connected?`${source} · gerçek zamanlı sistem verileri`:'Güvenli servis bağlantısı bekleniyor'}</p></div><button className="cc-back" onClick={onBack}><MessageSquare/>Normal sohbete dön</button></header>
  <div className="cc-grid">
   <aside className="cc-column cc-left">
    <section className="cc-card"><header><Activity/><h2>SİSTEM DURUMU</h2><span className={connected?'cc-live':''}>{connected?'CANLI':'BEKLENİYOR'}</span></header>
     <div className="cc-metrics">{metrics.map(({name,value,detail})=>{const known=typeof value==='number'&&Number.isFinite(value);return <div className="cc-metric" key={name}><div className={'cc-gauge '+(!known?'unavailable':'')} style={{'--metric':known?`${Math.max(0,Math.min(100,value))*3.6}deg`:'0deg'} as CSSProperties}><span><strong>{known?Math.round(value):'—'}<em>{known?'%':''}</em></strong><b>{name}</b></span></div><small>{detail}</small>{!known&&<span className="cc-unavailable">Kullanılamıyor</span>}</div>})}</div>
     <div className="cc-extra"><span>İşlemci sıcaklığı<b>{amount(temperature,' °C')}</b></span><span>GPU sıcaklığı<b>{amount(system?.gpu?.temp_c,' °C')}</b></span><span>Fan hızı<b>Kullanılamıyor</b></span><span>İşletim sistemi<b>{system?.platform||'Bekleniyor'}</b></span><span>Ağ<b>{system?.net?`↓ ${amount(system.net.down_mbps)} / ↑ ${amount(system.net.up_mbps)} Mbps`:'Kullanılamıyor'}</b></span></div>
    </section>
    <section className="cc-card"><header><Wifi/><h2>BAĞLI CİHAZLAR</h2></header>
     <Device icon={Monitor} title={source} status={system&&connected?'Bağlı':'Bekleniyor'} detail={system?'Gerçek telemetri akışı':'Yetkili masaüstü servisi gerekli'} online={Boolean(system&&connected)}/>
     <Device icon={MessageSquare} title="iPhone" status={phone?.online===true?'Çevrimiçi':phone?.online===false?'Çevrimdışı':'Bilinmiyor'} detail={phone?.state?.view?String(phone.state.view):'Heartbeat kaydı yok'} online={phone?.online===true}/>
     <Device icon={Cloud} title="GÖLGE bulut" status={cloud.text} detail={cloud.detail} online={cloud.online}/>
    </section>
    <section className="cc-card"><header><Radio/><h2>ZEKA VE SES</h2></header><div className="cc-model"><span>Yerel model</span><b>{ai?.connected&&ai.models?.length?(ai.primary||ai.models[0]):'Bağlı model yok'}</b></div><div className="cc-model"><span>Ses köprüsü</span><b>{native?taskState:'Bu oturumda yok'}</b></div><div className="cc-source"><ShieldCheck/><span>Telemetri kaynağı: {source}. Sensör değerleri tahmin edilmez.</span></div></section>
   </aside>
   <section className="cc-center">
    <section className="cc-map-card"><header><Globe2/><h2>DÜNYA GÖRÜNÜMÜ</h2><span className="cc-map-kind">3D</span><button disabled title="Canlı uydu haritası için lisanslı harita sağlayıcısı yapılandırılmamış">Uydu · yapılandırılmadı</button></header>
     <EarthWatch config={earth} showCoreButton={false} showMapButton={false} onCommand={mapCommand}/>
     <div className="cc-map-footer"><span><i/>STATİK YÜZEY HARİTASI</span><span>{earth.focus_label} · {earth.focus_lat.toFixed(2)}°, {earth.focus_lon.toFixed(2)}°</span></div>
     <p className="cc-map-note">Fareyle döndür · tekerlekle yakınlaş · konum seç. Canlı uydu, hava durumu ve uçuş sağlayıcısı yapılandırılmadı.</p>
    </section>
    {composer}
   </section>
   <aside className="cc-column cc-right">
    <section className="cc-card cc-events"><header><Terminal/><h2>TERMİNAL / OLAYLAR</h2><span>{notifications.length}</span></header><div className="cc-terminal-body">
     {notifications.length?notifications.slice(-15).reverse().map((event:any,index:number)=><article key={`${event.ts||index}-${index}`}><time>{Number.isFinite(Number(event.ts))?new Date(Number(event.ts)*1000).toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'}):'—'}</time><p>{safeEvent(event.text||event.message||event.kind||'Durum olayı')}</p></article>):<div className="cc-terminal-empty"><Terminal/><b>Olay akışı bekleniyor</b><p>{connected?'Bu oturumda henüz bir görev olayı yok.':'Yerel servis bağlandığında gerçek görev ve bağlantı olayları burada görünür.'}</p></div>}
     </div><div className="cc-terminal-footer"><i className={connected?'online':''}/>{connected?'Olay kanalına bağlı':'Servis bağlantısı bekleniyor'}<span>DENETLENEN AKIŞ</span></div>
    </section>
    <section className="cc-card cc-camera"><header><Camera/><h2>İZİNLİ KAMERA</h2></header><div className="cc-camera-preview"><Camera/><span>{native?'Kamera kapalı':'Yerel kamera köprüsü bağlı değil'}</span><small>Yalnızca açık izinle etkinleşir</small></div><button disabled={!native} onClick={()=>native?.action('camera')}><Camera/>Kamera izin penceresini aç</button></section>
    <section className="cc-card cc-actions"><header><Activity/><h2>HIZLI İŞLEMLER</h2></header><div className="cc-action-grid">
     <button onClick={()=>mapCommand('earth_focus',{place:'GLOBAL',lat:20,lon:0})}><Globe2/><span>Harita</span></button>
     <button onClick={()=>onOpen('Sistem Monitörü')}><Activity/><span>Analiz</span></button>
     <button onClick={()=>onOpen('Kod Asistanı')}><Code/><span>Kod</span></button>
     <button onClick={()=>onOpen('Dosyalar')}><FileText/><span>Dosyalar</span></button>
     <button onClick={()=>onOpen('Terminal')}><Terminal/><span>Görev aracı</span></button>
     <button onClick={()=>onOpen('Ayarlar')}><Settings/><span>Ayarlar</span></button>
    </div></section>
   </aside>
  </div>
 </section>;
}
