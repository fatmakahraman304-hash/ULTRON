import {useEffect,useRef,useState} from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type {EarthState} from './runtime';
export type MapLayer={available:boolean;url?:string;attribution?:string;max_zoom?:number;source?:string;reason?:string};
/** Raster street/optional licensed imagery only. No fabricated buildings/terrain. */
export default function EarthMap({config,layer,onCommand}:{config:EarthState;layer:MapLayer;onCommand:(op:string,args?:Record<string,unknown>)=>unknown}){
 const host=useRef<HTMLDivElement>(null),map=useRef<L.Map|null>(null),marker=useRef<L.CircleMarker|null>(null),[status,setStatus]=useState('Döşemeler yükleniyor…');
 const latest=useRef(onCommand),current=useRef(config);latest.current=onCommand;current.current=config;
 useEffect(()=>{
  if(!host.current||!layer.available||!layer.url)return;
  const m=L.map(host.current,{attributionControl:true,zoomControl:true,preferCanvas:true}).setView([config.focus_lat,config.focus_lon],config.map_zoom??5);map.current=m;
  // Keep required attribution as text; operator configuration cannot inject HTML.
  const text=document.createElement('span');text.textContent=layer.attribution||'';
  if(layer.source?.startsWith('OpenStreetMap')){const link=document.createElement('a');link.href='https://www.openstreetmap.org/copyright';link.textContent=layer.attribution||'© OpenStreetMap contributors';link.target='_blank';link.rel='noopener noreferrer';text.replaceChildren(link)}
  const tiles=L.tileLayer(layer.url,{maxZoom:layer.max_zoom??18,attribution:text.innerHTML,crossOrigin:'anonymous',referrerPolicy:'strict-origin-when-cross-origin',keepBuffer:1,updateWhenIdle:true});
  let failed=false;
  tiles.on('loading',()=>{failed=false;setStatus('Döşemeler yükleniyor…')});
  tiles.on('tileerror',()=>{failed=true;setStatus('Harita kaynağına erişilemiyor; görüntü doğrulanamadı.')});
  tiles.on('load',()=>{if(!failed)setStatus(layer.source||'Harita döşemeleri yüklendi')});tiles.addTo(m);
  const pin=L.circleMarker([config.focus_lat,config.focus_lon],{radius:6,color:'#9aeaff',fillColor:'#20b7ff',fillOpacity:.8}).addTo(m);
  const label=document.createElement('span');label.textContent=config.focus_label;
  pin.bindTooltip(label,{permanent:true,direction:'top'});marker.current=pin;
  const select=(e:L.LeafletMouseEvent)=>{void latest.current('earth_focus',{lat:e.latlng.lat,lon:e.latlng.lng,place:'SEÇİLEN KONUM',layer:config.layer,map_zoom:m.getZoom()});};m.on('click',select);
  m.on('moveend',()=>{const c=current.current,center=m.getCenter();if(Math.abs(center.lat-c.focus_lat)>.0005||Math.abs(center.lng-c.focus_lon)>.0005||m.getZoom()!==(c.map_zoom??5))void latest.current('earth_focus',{lat:center.lat,lon:center.lng,place:c.focus_label,layer:c.layer,map_zoom:m.getZoom()})});
  const ro=new ResizeObserver(()=>m.invalidateSize());ro.observe(host.current);
  return()=>{ro.disconnect();tiles.off();m.off();m.remove();map.current=null;};
 },[layer.url]);
 useEffect(()=>{const m=map.current;if(m){m.flyTo([config.focus_lat,config.focus_lon],config.map_zoom??5,{duration:window.matchMedia('(prefers-reduced-motion: reduce)').matches?0:1.2});marker.current?.setLatLng([config.focus_lat,config.focus_lon]);const label=document.createElement('span');label.textContent=config.focus_label;marker.current?.setTooltipContent(label)}},[config.focus_lat,config.focus_lon,config.map_zoom,config.focus_label]);
 return <div className="earth-map-wrap"><div ref={host} className="earth-raster-map" aria-label={config.layer==='SATELLITE'?'Lisanslı uydu haritası':'OpenStreetMap sokak haritası'}/><div className="earth-tile-status" role="status">{status}</div></div>;
}
