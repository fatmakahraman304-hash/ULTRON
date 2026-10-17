import {useRef,useState} from 'react';
import {request,type EarthState,type StageState} from './runtime';
import type {MapLayer} from './EarthMap';
import {formatWeatherReply} from './weatherReply';
export type PlaceHit={lat:number;lon:number;label:string;kind?:string};
export type EarthSearch={query:string;source:string;hits:PlaceHit[]};
/** One session controller shared by chat, voice, CORE and control center. */
export function useEarthActions(stage:StageState,isMobile:boolean,onNavigate?:(operation:string)=>void){
 const [search,setSearch]=useState<EarthSearch|null>(null),sequence=useRef(0);
 const stageCommand=async(operation:string,args:Record<string,unknown>={})=>{const result=await request('/api/stage/command',{operation,...args});onNavigate?.(operation);return result;};
 const choose=async(hit:PlaceHit)=>{
  const city=/city|town|village|suburb|district|locality/.test(hit.kind||'');
  const result=await stageCommand('earth_focus',{lat:hit.lat,lon:hit.lon,place:hit.label,camera_distance:6.8,layer:city?'MAP':'GLOBAL',map_zoom:city?13:7});setSearch(null);return result;
 };
 const command=async(operation:string,args:Record<string,unknown>={}):Promise<string>=>{
  if(isMobile)return 'Dünya ve CORE görünümleri laptop ekranında kullanılabilir. Bu cihazda sohbet açık kaldı.';
  if(operation==='earth_invalid')return 'Koordinat geçersiz. Enlem −90…90, boylam −180…180 aralığında olmalı.';
  if(operation==='earth_search'){
   const id=++sequence.current,query=String(args.query||'').slice(0,100);
   try{
    const r=await request('/api/world/search?q='+encodeURIComponent(query),undefined,AbortSignal.timeout(12000));
    if(id!==sequence.current)return 'Önceki konum araması yeni komut nedeniyle kullanılmadı.';
    const hits=(r.results||[]).filter((x:PlaceHit)=>Number.isFinite(x.lat)&&Number.isFinite(x.lon)&&Math.abs(x.lat)<=90&&Math.abs(x.lon)<=180).slice(0,5);
    if(!hits.length)return 'Konum kaynağında eşleşme bulunamadı. Daha açık bir yer adı veya koordinat yazabilirsin.';
    if(hits.length===1){await choose(hits[0]);return `${hits[0].label} için ${r.source} koordinatları alındı; kamera geçişi başlatıldı.`;}
    await stageCommand('earth_open');setSearch({query,source:r.source,hits});return `${query} için birden fazla konum bulundu. Dünya üzerindeki sonuç listesinden doğru konumu seç.`;
   }catch{return 'Konum servisine erişilemedi. Koordinat uydurmadım; mevcut görünüm korundu.';}
  }
  ++sequence.current;setSearch(null);
  if(operation==='earth_layer'){
   const layer=String(args.layer||'GLOBAL');
   if(layer==='TERRAIN')return '3D arazi ve bina verisi yapılandırılmadı. Küresel Dünya kullanılabilir.';
   if(layer==='SATELLITE'||layer==='MAP'){
    const layers=await request('/api/world/layers') as Record<string,MapLayer>;
    if(!layers[layer]?.available)return layers[layer]?.reason||'Bu harita kaynağı kullanılamıyor.';
   }
   await stageCommand('earth_control',{layer,...(layer==='GLOBAL'?{camera_distance:7.4}:{})});
   if(layer==='WEATHER'){
    try{
     const {focus_lat:lat,focus_lon:lon,focus_label:place}=stage.earth;
     const data=await request(`/api/world/weather?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`,undefined,AbortSignal.timeout(12000));
     return formatWeatherReply(data,place);
    }catch{return 'Hava durumu görünümü açıldı ancak sağlayıcıdan veri alınamadı. Canlı hava sonucu doğrulanmadı.';}
   }
   return layer==='FLIGHTS'?'Uçuş verisi sorgulanıyor; yalnızca sağlayıcıdan alınan uçuşlar gösterilir.':layer==='MAP'?'Sokak haritası açılıyor; uydu fotoğrafı değildir.':layer==='SATELLITE'?'Yapılandırılmış lisanslı uydu döşemeleri yükleniyor.':'Dünya görünümü seçildi.';
  }
  if(operation==='earth_zoom'){
   const factor=Number(args.factor),earth:EarthState=stage.earth;
   const raster=earth.layer==='MAP'||earth.layer==='SATELLITE';
   if(!raster&&(earth.camera_distance??7.4)*factor<6)return 'Küresel doku ayrıntı sınırına ulaşıldı. Sokak ayrıntıları için “Haritayı aç” diyebilirsin.';
   await stageCommand('earth_control',{...(raster?{map_zoom:Math.max(1,Math.min(19,(earth.map_zoom??5)+(factor<1?1:-1)))}:{camera_distance:Math.max(6,Math.min(15,(earth.camera_distance??7.4)*factor))})});return 'Kamera yakınlığı güncellendi.';
  }
  await stageCommand(operation,args);
  return operation==='reset'?'CORE görünümüne geçiliyor.':operation==='earth_open'?'Dünya görüntüsü açılıyor.':'Dünya görünümü güncellendi.';
 };
 return {command,search,choose};
}
