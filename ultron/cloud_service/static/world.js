// ULTRON WORLD: truthful real-source 2D map and 3D globe, no fake live data.
const $=id=>document.getElementById(id);
const allowedCoordinate=(v,min,max,defaultValue)=>{const n=Number(v);return Number.isFinite(n)&&n>=min&&n<=max?n:defaultValue;};
const params=new URLSearchParams(location.search);
let center={
  lat:allowedCoordinate(params.get('lat'),-85,85,35.13),
  lon:allowedCoordinate(params.get('lon'),-180,180,33.43)
};
const status=(message,error=false)=>{const el=$('layerStatus');el.textContent=message;el.className=error?'err':'pill';};
const detail=(text)=>{$('detailText').textContent=text;};
let map, L=window.L, marker, globeState=null, currentMode='2d', flightsLayer=null, quakesLayer=null;
let flightsEnabled=false,quakesEnabled=false,weatherEnabled=true;
let refreshBusy=false, searchBusy=false, lastWeather='';
let favorites=[];
try{const raw=JSON.parse(localStorage.getItem('ultron-world-favorites')||'[]');favorites=Array.isArray(raw)?raw.filter(x=>Number.isFinite(x.lat)&&Number.isFinite(x.lon)).slice(0,15):[]}catch{}
const btn=(id,fn)=>{$(id).addEventListener('click',fn);};
const asAPI=(path,qs='')=>fetch('/api/world/'+path+qs,{credentials:'same-origin'}).then(async res=>{
 const json=await res.json().catch(()=>({error:'invalid_server_response'}));
 if(!res.ok)throw Error(json.error||'HTTP '+res.status);
 return json;
});
function setLocation(lat,lon,zoom=13){
 center={lat:allowedCoordinate(lat,-85,85,center.lat),lon:allowedCoordinate(lon,-180,180,center.lon)};
 $('position').textContent=center.lat.toFixed(4)+'° • '+center.lon.toFixed(4)+'°';
 if(map){map.setView([center.lat,center.lon],zoom);if(marker)marker.setLatLng([center.lat,center.lon])}
 if(globeState)globeState.focus(center.lat,center.lon);
 if(weatherEnabled)loadWeather().catch(()=>{});
 if(flightsEnabled)loadFlights().catch(()=>{});
}
function centerChanged(){
 const p=map.getCenter();center={lat:p.lat,lon:p.lng};
 $('position').textContent=center.lat.toFixed(4)+'° • '+center.lon.toFixed(4)+'°';
}
if(L){
 map=L.map('map',{zoomControl:false,preferCanvas:true,worldCopyJump:true}).setView([center.lat,center.lon],7);
 L.control.zoom({position:'bottomright'}).addTo(map);
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
   attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
   maxZoom:19,detectRetina:false,updateWhenIdle:true
 }).addTo(map);
 marker=L.circleMarker([center.lat,center.lon],{radius:7,color:'#ff3047',fillColor:'#ff3047',fillOpacity:.7}).addTo(map);
 flightsLayer=L.layerGroup().addTo(map);quakesLayer=L.layerGroup().addTo(map);
 map.on('click',e=>{setLocation(e.latlng.lat,e.latlng.lng,map.getZoom());detail('Seçili koordinat: '+center.lat.toFixed(5)+', '+center.lon.toFixed(5))});
 map.on('moveend',centerChanged);
}else{
 detail('2D harita kütüphanesi yüklenemedi. İnterneti kontrol edip yeniden aç.');
 status('Harita yüklenemedi',true);
}
btn('flyToCyprus',()=>setLocation(35.13,33.43,10));
btn('flyToTurkey',()=>setLocation(39.0,35.0,6));
btn('refresh',()=>{refreshLayers().catch(()=>{})});
btn('airQuality',async()=>{
 $('airQuality').disabled=true;status('Gerçek hava kalitesi ölçümleri alınıyor…');
 try{
  const data=await asAPI('air-quality','?lat='+center.lat+'&lon='+center.lon);
  const c=data.current||{};
  const lines=['US AQI: '+safeText(c.us_aqi),'PM2.5: '+safeText(c.pm2_5)+' μg/m³','PM10: '+safeText(c.pm10)+' μg/m³','Ozon: '+safeText(c.ozone)+' μg/m³','UV: '+safeText(c.uv_index)];
  const root=$('weatherCard');const label=document.createElement('b');label.textContent='☷ HAVA KALİTESİ • '+data.updated;root.append(label);
  for(const item of lines){const div=document.createElement('div');div.textContent=item;root.append(div)}
  status('Open-Meteo Air Quality • veri, konuma ve saatine bağlı');
 }catch{status('Hava kalitesi verisi alınamadı; tahmini rakam gösterilmiyor',true)}
 finally{$('airQuality').disabled=false}
});
btn('rainRadar',()=>external('https://www.rainviewer.com/weather-radar-map-live.html'));
btn('windMap',()=>external('https://earth.nullschool.net/'));
btn('ships',()=>external('https://www.marinetraffic.com/en/ais/home/centerx:'+center.lon+'/centery:'+center.lat+'/zoom:8'));
btn('weather',()=>{
 weatherEnabled=!weatherEnabled;$('weather').classList.toggle('active',weatherEnabled);
 $('weatherCard').replaceChildren();
 if(weatherEnabled)loadWeather().catch(()=>{});
});
btn('flights',()=>{
 flightsEnabled=!flightsEnabled;$('flights').classList.toggle('active',flightsEnabled);
 if(!flightsEnabled)flightsLayer?.clearLayers();else loadFlights().catch(()=>{});
});
btn('quakes',()=>{
 quakesEnabled=!quakesEnabled;$('quakes').classList.toggle('active',quakesEnabled);
 if(!quakesEnabled)quakesLayer?.clearLayers();else loadQuakes().catch(()=>{});
});
btn('findMe',()=>{
 if(!navigator.geolocation){status('Konum izni bu tarayıcıda yok',true);return}
 status('Konum izni bekleniyor…');
 navigator.geolocation.getCurrentPosition(
  p=>{setLocation(p.coords.latitude,p.coords.longitude,15);status('Konum, senin izninle açıldı')},
  e=>status('Konum alınamadı: '+(e.code===1?'izin verilmedi':'konum kullanılamıyor'),true),
  {enableHighAccuracy:false,timeout:10000,maximumAge:60000}
 );
});
btn('favorite',()=>{
 const label=prompt('Bu konuma bir isim ver:', 'Kayıtlı konum');
 if(label===null)return;
 favorites=[{lat:center.lat,lon:center.lon,label:String(label).trim().slice(0,60)||'Konum'},...favorites].slice(0,15);
 try{localStorage.setItem('ultron-world-favorites',JSON.stringify(favorites))}catch{}
 status('Favori bu tarayıcıya kaydedildi');
});
btn('myFavorites',()=>{
 const root=$('searchResults');root.replaceChildren();root.classList.remove('hidden');
 if(!favorites.length){const msg=document.createElement('p');msg.textContent='Henüz kayıtlı favori yok.';root.append(msg)}
 favorites.forEach(f=>{
  const b=document.createElement('button');b.textContent=f.label+' • '+f.lat.toFixed(3)+', '+f.lon.toFixed(3);
  b.onclick=()=>{setLocation(f.lat,f.lon,16);root.classList.add('hidden')};root.append(b);
 });
});
function external(url){
 const tab=window.open(url,'_blank','noopener,noreferrer');
 if(!tab)status('Yeni pencere engellendi; tarayıcı izinlerini kontrol et',true);
}
btn('satellite',()=>external('https://www.google.com/maps/@'+center.lat+','+center.lon+',17z/data=!3m1!1e3'));
btn('streetview',()=>external('https://www.google.com/maps/@?api=1&map_action=pano&viewpoint='+center.lat+','+center.lon));
btn('directions',()=>external('https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=;'+encodeURIComponent(center.lat+','+center.lon)));
btn('traffic',()=>external('https://www.google.com/maps/@'+center.lat+','+center.lon+',13z/data=!5m1!1e1'));
$('searchForm').addEventListener('submit',async event=>{
 event.preventDefault();if(searchBusy)return;
 const q=$('searchInput').value.trim();if(q.length<3)return;
 searchBusy=true;status('Gerçek adres sonuçları aranıyor…');
 const root=$('searchResults');root.replaceChildren();root.classList.remove('hidden');
 try{
  const data=await asAPI('search','?q='+encodeURIComponent(q));
  if(!data.results.length){const p=document.createElement('p');p.textContent='Adres bulunamadı.';root.append(p)}
  for(const place of data.results){
   const b=document.createElement('button');b.textContent=place.label||place.lat+', '+place.lon;
   b.onclick=()=>{setLocation(place.lat,place.lon,Math.max(map?.getZoom()||13,15));root.classList.add('hidden');detail('Adres: '+place.label)};
   root.append(b);
  }
  status(data.results.length+' gerçek adres sonucu • '+data.source);
 }catch(err){status('Adres araması kullanılamıyor: '+err.message,true)}
 finally{searchBusy=false}
});
async function loadWeather(){
 if(!weatherEnabled)return;
 const at={...center};status('Hava durumu sorgulanıyor…');
 try{
  const d=await asAPI('weather','?lat='+at.lat+'&lon='+at.lon);
  if(!weatherEnabled||at.lat!==center.lat||at.lon!==center.lon)return;
  const c=d.current;
  const lines=[
   'Sıcaklık: '+safeText(c.temperature_2m)+' °C',
   'Hissedilen: '+safeText(c.apparent_temperature)+' °C',
   'Rüzgâr: '+safeText(c.wind_speed_10m)+' km/sa • yön '+safeText(c.wind_direction_10m)+'°',
   'Yağış: '+safeText(c.precipitation)+' mm'+(d.forecast_not_observation?' (gelecek 1 saat tahmini)':'')+' • nem %'+safeText(c.relative_humidity_2m),
   'Bulut: %'+safeText(c.cloud_cover)+' • basınç '+safeText(c.surface_pressure)+' hPa',
  ];
  $('weatherCard').replaceChildren();
  const title=document.createElement('b');title.textContent='☁ CANLI HAVA • '+String(d.updated||'');$('weatherCard').append(title);
  for(const line of lines){const div=document.createElement('div');div.textContent=line;$('weatherCard').append(div)}
  const days=d.daily||{};
  if(Array.isArray(days.sunrise)&&days.sunrise[0]){const div=document.createElement('div');div.textContent='Gün doğumu: '+String(days.sunrise[0]).slice(11)+' • Gün batımı: '+String(days.sunset?.[0]||'').slice(11)+' • UV max: '+safeText(days.uv_index_max?.[0]);$('weatherCard').append(div)}
  const hourly=(d.hourly?.precipitation_probability||[]).slice(0,6);
  if(hourly.length){const div=document.createElement('div');div.textContent='Gelecek saatlerde yağış olasılığı: '+hourly.map(v=>'%'+v).join(' • ');$('weatherCard').append(div)}
  lastWeather='Hava: '+safeText(c.temperature_2m)+' °C';status(lastWeather+' • '+String(d.source||'Sağlayıcı bilinmiyor')+(d.forecast_not_observation?' • saatlik tahmin':''));
 }catch(e){status('Hava verisine ulaşılamadı; eski tahmin gösterilmiyor',true)}
}
const safeText=(v)=>v===null||v===undefined?'Bilinmiyor':String(v);
async function loadFlights(){
 if(!flightsEnabled||!map)return;
 try{
  const d=await asAPI('flights','?lat='+center.lat+'&lon='+center.lon+'&dist=100');
  if(!flightsEnabled)return;
  flightsLayer.clearLayers();
  for(const plane of d.aircraft){
   if(!Number.isFinite(plane.lat)||!Number.isFinite(plane.lon))continue;
   const icon=L.divIcon({className:'',html:'<div class="flight-icon">✈</div>',iconSize:[28,28],iconAnchor:[14,14]});
   const m=L.marker([plane.lat,plane.lon],{icon});
   const box=document.createElement('div');
   for(const [name,value] of [
    ['Çağrı kodu',plane.flight],['İrtifa',plane.alt_ft===null?'Bilinmiyor':plane.alt_ft+' ft'],
    ['Hız',plane.speed_kt===null?'Bilinmiyor':plane.speed_kt+' kt'],
    ['Yön',plane.heading===null?'Bilinmiyor':plane.heading+'°']
   ]){const p=document.createElement('p');p.textContent=name+': '+safeText(value);box.append(p)}
   m.bindPopup(box);flightsLayer.addLayer(m);
  }
  $('updated').textContent=d.count+' raporlanan uçak • adsb.lol';
  status(d.count+' uçak raporlandı. Kapsama eksik olabilir.');
 }catch(e){flightsLayer?.clearLayers();status('Uçak verisi kullanılamıyor; sahte uçak gösterilmiyor',true)}
}
async function loadQuakes(){
 if(!quakesEnabled||!map)return;
 try{
  const d=await asAPI('earthquakes');
  if(!quakesEnabled)return;
  quakesLayer.clearLayers();
  for(const q of d.events){
   if(!Number.isFinite(q.lat)||!Number.isFinite(q.lon))continue;
   const circle=L.circleMarker([q.lat,q.lon],{radius:Math.min(16,4+Math.max(0,q.magnitude)*1.6),color:'#ff5c57',weight:1,fillColor:'#e72f35',fillOpacity:.45});
   const p=document.createElement('p');p.textContent='M '+q.magnitude+' • '+q.place;circle.bindPopup(p);
   quakesLayer.addLayer(circle);
  }
  status(d.count+' deprem kaydı • USGS, son 24 saat');
 }catch(e){quakesLayer?.clearLayers();status('Deprem kaynağına ulaşılamadı; sahte olay gösterilmiyor',true)}
}
async function refreshLayers(){
 if(refreshBusy)return;refreshBusy=true;
 try{
  const work=[];
  if(weatherEnabled)work.push(loadWeather());
  if(flightsEnabled)work.push(loadFlights());
  if(quakesEnabled)work.push(loadQuakes());
  await Promise.allSettled(work);
 }finally{refreshBusy=false}
}
btn('mode2d',()=>{
 currentMode='2d';$('mode2d').classList.add('active');$('mode3d').classList.remove('active');
 $('globe').classList.add('hidden');$('map').classList.remove('hidden');map?.invalidateSize();
 status('2D sokak haritası • yakınlaştırma z19; bina bilgisi bölgeye göre değişebilir.');
});
btn('mode3d',async()=>{
 currentMode='3d';$('mode3d').classList.add('active');$('mode2d').classList.remove('active');
 $('map').classList.add('hidden');$('globe').classList.remove('hidden');
 status('Gerçek WebGL 3D küre yükleniyor…');
 try{if(!globeState)globeState=await startGlobe($('globe'));globeState.focus(center.lat,center.lon);status('3D küre • döndürmek için sürükle. Bina seviyesi için 2D’ye dön.')}
 catch(e){status('3D küre bu tarayıcıda açılamadı. 2D harita kullanılabilir.',true);$('mode2d').click()}
});
async function startGlobe(host){
 const THREE=await import('https://esm.sh/three@0.177.0');
 if(!host)return null;
 const scene=new THREE.Scene();
 const camera=new THREE.PerspectiveCamera(42,1,.1,100);camera.position.set(0,0,7);
 const renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'});
 renderer.setPixelRatio(Math.min(1.5,devicePixelRatio||1));host.append(renderer.domElement);
 const sphere=new THREE.Mesh(new THREE.SphereGeometry(2.4,64,40),new THREE.MeshPhongMaterial({color:0xb2b8c3}));
 scene.add(sphere);scene.add(new THREE.AmbientLight(0x8ab6ed,1.05));
 const sun=new THREE.DirectionalLight(0xffffff,2.5);sun.position.set(4,2,6);scene.add(sun);
 new THREE.TextureLoader().load('https://threejs.org/examples/textures/planets/earth_atmos_2048.jpg',
  tex=>{tex.colorSpace=THREE.SRGBColorSpace;sphere.material.map=tex;sphere.material.color.setHex(0xffffff);sphere.material.needsUpdate=true},
  undefined,()=>status('3D doku sağlayıcısı erişilemedi; küre gösteriliyor',true));
 const geometry=new THREE.SphereGeometry(2.48,64,32);
 const atmosphere=new THREE.Mesh(geometry,new THREE.MeshBasicMaterial({color:0x256eb8,transparent:true,opacity:.08,side:THREE.BackSide}));atmosphere.scale.setScalar(1.02);scene.add(atmosphere);
 let grabbed=false,lastX=0,lastY=0,disposed=false,raf=0;
 const down=e=>{grabbed=true;lastX=e.clientX;lastY=e.clientY;host.setPointerCapture?.(e.pointerId)};
 const move=e=>{if(!grabbed)return;sphere.rotation.y+=(e.clientX-lastX)*.008;sphere.rotation.x=Math.max(-1.3,Math.min(1.3,sphere.rotation.x+(e.clientY-lastY)*.006));lastX=e.clientX;lastY=e.clientY};
 const up=()=>{grabbed=false};
 host.addEventListener('pointerdown',down);host.addEventListener('pointermove',move);host.addEventListener('pointerup',up);host.addEventListener('pointercancel',up);
 const wheel=e=>{e.preventDefault();camera.position.z=Math.min(12,Math.max(3.2,camera.position.z+Math.sign(e.deltaY)*.45))};
 host.addEventListener('wheel',wheel,{passive:false});
 const resize=()=>{const w=Math.max(1,host.clientWidth),h=Math.max(1,host.clientHeight);renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix()};
 const ro=new ResizeObserver(resize);ro.observe(host);resize();
 function frame(){if(disposed)return;raf=requestAnimationFrame(frame);if(document.hidden||currentMode!=='3d')return;renderer.render(scene,camera)}frame();
 return {focus(lat,lon){sphere.rotation.set(-lat*Math.PI/180,(lon*Math.PI/180),0);},dispose(){disposed=true;cancelAnimationFrame(raf);ro.disconnect();renderer.dispose();host.replaceChildren()}};
}
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&currentMode==='2d')map?.invalidateSize()});
setInterval(()=>{if(!document.hidden&&currentMode==='2d'&&flightsEnabled)loadFlights().catch(()=>{})},45000);
setInterval(()=>{if(!document.hidden&&weatherEnabled)loadWeather().catch(()=>{})},600000);
if(map){setLocation(center.lat,center.lon,Math.max(5,Number(params.get('zoom'))||9));refreshLayers().catch(()=>{})}
