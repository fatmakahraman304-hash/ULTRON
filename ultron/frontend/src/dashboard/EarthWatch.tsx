import {lazy,Suspense,useEffect,useRef,useState,type MutableRefObject} from 'react';
import * as THREE from 'three';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {Globe2,LocateFixed,RotateCcw,Search} from 'lucide-react';
import {request,type EarthState} from './runtime';
import type {EarthSearch,PlaceHit} from './useEarthActions';
import type {MapLayer} from './EarthMap';
import earthDay from '../assets/earth/day.webp';
import earthClouds from '../assets/earth/clouds.webp';
import earthLights from '../assets/earth/lights.webp';
import {cartesianToEarth,earthToCartesian,solarPositionUTC} from './earthMath';
const EarthMap=lazy(()=>import('./EarthMap'));
export type EarthView={position:number[];orientation:number[];focus:string};
export type SceneTransition='stable'|'enter'|'exit';
type Props={config:EarthState;onCommand:(op:string,args?:Record<string,unknown>)=>unknown;showCoreButton?:boolean;showMapButton?:boolean;viewMemory?:MutableRefObject<EarthView|null>;transition?:SceneTransition;search?:EarthSearch|null;onChoose?:(hit:PlaceHit)=>unknown};
const point=(lat:number,lon:number,r=2.25)=>{const p=earthToCartesian(lat,lon,r);return new THREE.Vector3(p.x,p.y,p.z)};
const MODES=[['GLOBAL','Dünya'],['SATELLITE','Uydu'],['MAP','Harita'],['TERRAIN','3D arazi'],['NIGHT','Gece'],['WEATHER','Hava'],['FLIGHTS','Uçuşlar'],['LOCATIONS','Konumlar']] as const;
function disposeObject(root:THREE.Object3D){root.traverse(o=>{const m=o as THREE.Mesh;m.geometry?.dispose();const materials=Array.isArray(m.material)?m.material:[m.material];for(const mat of materials){if(!mat)continue;const typed=mat as THREE.MeshBasicMaterial;typed.map?.dispose();mat.dispose();}})}
export function EarthWatch({config,onCommand,showCoreButton=true,showMapButton=true,viewMemory,transition='stable',search,onChoose}:Props){
 const host=useRef<HTMLDivElement>(null),latest=useRef(config),phase=useRef({value:transition,at:performance.now()}),apply=useRef<()=>void>(()=>{}),localView=useRef<EarthView|null>(null);
 const [webglError,setWebglError]=useState(false),[textureStatus,setTextureStatus]=useState('loading'),[picked,setPicked]=useState<{lat:number;lon:number}|null>(null),[query,setQuery]=useState(''),[layers,setLayers]=useState<Record<string,MapLayer>>({}),[data,setData]=useState<any>(null),[dataStatus,setDataStatus]=useState(''),[iss,setIss]=useState<any>(null);
 const observations=useRef<any>({});observations.current={data,iss};
 latest.current=config;
 useEffect(()=>{phase.current={value:transition,at:performance.now()};},[transition]);
 useEffect(()=>{apply.current();},[config]);
 useEffect(()=>{apply.current();},[data,iss]);
 const layer=config.layer||'GLOBAL',raster=layer==='MAP'||layer==='SATELLITE';
 useEffect(()=>{const ctl=new AbortController();request('/api/world/layers',undefined,ctl.signal).then(setLayers).catch(()=>{});return()=>ctl.abort()},[]);
 useEffect(()=>{
  if(!config.live_iss){setIss(null);return;}
  const ctl=new AbortController();let busy=false;
  const read=async()=>{if(busy||document.hidden)return;busy=true;try{const r=await request('/api/world/iss',undefined,ctl.signal);if(!ctl.signal.aborted)setIss(r)}catch{if(!ctl.signal.aborted)setIss(null)}finally{busy=false}};
  void read();const timer=setInterval(()=>void read(),10000);return()=>{ctl.abort();clearInterval(timer)};
 },[config.live_iss]);
 useEffect(()=>{
  if(layer!=='WEATHER'&&layer!=='FLIGHTS'){setData(null);setDataStatus('');return;}
  const ctl=new AbortController();let busy=false;
  const read=async()=>{if(busy||document.hidden)return;busy=true;setData(null);setDataStatus('Kaynak sorgulanıyor…');
   try{const r=await request(`/api/world/${layer==='WEATHER'?'weather':'flights'}?lat=${config.focus_lat}&lon=${config.focus_lon}`,undefined,ctl.signal);if(!ctl.signal.aborted){setData(r);setDataStatus('Kaynak yanıtı alındı')}}
   catch{if(!ctl.signal.aborted){setData(null);setDataStatus('Veri kaynağı kullanılamıyor; canlı veri gösterilmiyor.')}}finally{busy=false;}};
  void read();const timer=setInterval(()=>void read(),layer==='WEATHER'?600000:45000);return()=>{ctl.abort();clearInterval(timer)};
 },[layer,config.focus_lat,config.focus_lon]);
 useEffect(()=>{
  const el=host.current;if(!el||raster)return;let dead=false,raf=0,visible=true,running=false,last=0,time=0,focusKey='',flying=false;
  let renderer:THREE.WebGLRenderer;
  try{renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'})}catch{setWebglError(true);return;}
  setWebglError(false);setTextureStatus('loading');
  const gl=renderer.getContext(),debug=gl.getExtension('WEBGL_debug_renderer_info');
  const gpu=debug?String(gl.getParameter(debug.UNMASKED_RENDERER_WEBGL)):'WebGL';
  const low=/swiftshader|llvmpipe|software|intel.*(?:hd|uhd)/i.test(gpu)||navigator.hardwareConcurrency<5;
  el.dataset.renderer=gpu;el.dataset.quality=low?'balanced':'standard';
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,low?1.15:1.6));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.setClearColor(0x01050c,0);el.appendChild(renderer.domElement);
  const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(42,1,.05,100);camera.position.set(0,0,7.4);
  const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.enablePan=false;controls.minDistance=6;controls.maxDistance=15;
  const root=new THREE.Group();scene.add(root);
  const memory=viewMemory||localView,previous=memory.current;
  if(previous){camera.position.fromArray(previous.position);root.quaternion.fromArray(previous.orientation);focusKey=previous.focus;}
  const zero=new THREE.DataTexture(new Uint8Array([2,12,25,255]),1,1);zero.needsUpdate=true;
  const textures=new Set<THREE.Texture>([zero]);
  const uniforms={day:{value:zero as THREE.Texture},lights:{value:zero as THREE.Texture},sun:{value:new THREE.Vector3(1,0,0)},night:{value:0},reveal:{value:1}};
  const surface=new THREE.ShaderMaterial({transparent:true,uniforms,
   vertexShader:`varying vec2 vUv;varying vec3 vN;void main(){vUv=uv;vN=normalize(mat3(modelMatrix)*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
   fragmentShader:`uniform sampler2D day;uniform sampler2D lights;uniform vec3 sun;uniform float night;uniform float reveal;varying vec2 vUv;varying vec3 vN;
    void main(){float d=dot(normalize(vN),normalize(sun));float lit=smoothstep(-.1,.18,d);vec3 albedo=texture2D(day,vUv).rgb;vec3 city=texture2D(lights,vUv).rgb;
     vec3 color=albedo*(.065+lit*.92)*(1.-night*.2)+city*(1.-smoothstep(-.2,.1,d))*.9;
     float edge=pow(1.-max(d,0.),4.)*lit*.05;color+=vec3(.1,.35,.65)*edge;
     gl_FragColor=vec4(color,reveal);
     #include <tonemapping_fragment>
     #include <colorspace_fragment>
    }`});
  const earth=new THREE.Mesh(new THREE.SphereGeometry(2.25,low?72:112,low?48:72),surface);root.add(earth);
  const loader=new THREE.TextureLoader();
  const load=(url:string,done:(texture:THREE.Texture)=>void,required=false)=>loader.load(url,tex=>{if(dead){tex.dispose();return;}tex.colorSpace=THREE.SRGBColorSpace;tex.anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());textures.add(tex);done(tex);if(required)setTextureStatus('loaded')},undefined,()=>{if(!dead&&required)setTextureStatus('failed')});
  load(earthDay,tex=>uniforms.day.value=tex,true);load(earthLights,tex=>uniforms.lights.value=tex);
  const atmosphereMat=new THREE.ShaderMaterial({transparent:true,blending:THREE.AdditiveBlending,depthWrite:false,uniforms:{reveal:uniforms.reveal},
   vertexShader:`varying vec3 vN;varying vec3 vP;void main(){vec4 p=modelViewMatrix*vec4(position,1.);vN=normalize(normalMatrix*normal);vP=p.xyz;gl_Position=projectionMatrix*p;}`,
   fragmentShader:`uniform float reveal;varying vec3 vN;varying vec3 vP;void main(){float rim=pow(1.-abs(dot(normalize(vN),normalize(-vP))),4.);gl_FragColor=vec4(.08,.48,1.,rim*.85*reveal);}`});
  const atmosphere=new THREE.Mesh(new THREE.SphereGeometry(2.3,64,40),atmosphereMat);root.add(atmosphere);
  const cloudMat=new THREE.MeshPhongMaterial({transparent:true,opacity:.36,depthWrite:false});
  const clouds=new THREE.Mesh(new THREE.SphereGeometry(2.276,64,40),cloudMat);root.add(clouds);load(earthClouds,tex=>{cloudMat.map=tex;cloudMat.needsUpdate=true});
  const sun=new THREE.DirectionalLight(0xffffff,2);scene.add(sun);scene.add(new THREE.AmbientLight(0x315579,.08));
  const grid=new THREE.Group(),markers=new THREE.Group(),planes=new THREE.Group();root.add(grid,markers,planes);
  for(let lat=-60;lat<=60;lat+=30){const points=[];for(let lon=-180;lon<=180;lon+=4)points.push(point(lat,lon,2.26));grid.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),new THREE.LineBasicMaterial({color:0x58c6fc,transparent:true,opacity:.14})))}
  for(let lon=-150;lon<=180;lon+=30){const points=[];for(let lat=-89;lat<=89;lat+=3)points.push(point(lat,lon,2.26));grid.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),new THREE.LineBasicMaterial({color:0x58c6fc,transparent:true,opacity:.11})))}
  const starPos=new Float32Array(1100*3);for(let i=0;i<1100;i++){const y=1-2*(i+.5)/1100,a=i*2.399963,r=18+(i%17);starPos.set([Math.cos(a)*Math.sqrt(1-y*y)*r,y*r,Math.sin(a)*Math.sqrt(1-y*y)*r],i*3)}
  const starGeo=new THREE.BufferGeometry();starGeo.setAttribute('position',new THREE.BufferAttribute(starPos,3));const starMat=new THREE.PointsMaterial({color:0xbad9f7,size:.028,transparent:true,depthWrite:false});const stars=new THREE.Points(starGeo,starMat);scene.add(stars);
  const marker=(lat:number,lon:number,label:string,color:string)=>{
   const group=new THREE.Group();group.position.copy(point(lat,lon,2.29));group.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),group.position.clone().normalize());
   group.add(new THREE.Mesh(new THREE.RingGeometry(.035,.06,24),new THREE.MeshBasicMaterial({color,side:THREE.DoubleSide,transparent:true,opacity:.9})));
   const canvas=document.createElement('canvas');canvas.width=400;canvas.height=56;const ctx=canvas.getContext('2d')!;ctx.fillStyle='#04111ddd';ctx.fillRect(0,0,400,56);ctx.font='500 22px Arial';ctx.textAlign='center';ctx.fillStyle=color;ctx.fillText(label.slice(0,32),200,36);
   const tex=new THREE.CanvasTexture(canvas),sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:tex,depthTest:true,transparent:true,sizeAttenuation:false}));sprite.scale.set(.28,.04,1);sprite.position.y=.17;group.add(sprite);markers.add(group);
  };
  let markerKey='',observationKey='',wantedDistance=camera.position.length(),requestedDistance=latest.current.camera_distance??7.4,focusStarted=0,focusStartDistance=camera.position.length();
  const focusStartRotation=root.quaternion.clone();
  const update=()=>{
   const c=latest.current,newFocus=`${c.focus_lat}:${c.focus_lon}:${c.night}:${c.focus_revision||0}`;
   atmosphere.visible=c.atmosphere;clouds.visible=c.clouds;grid.visible=c.grid;stars.visible=c.stars;uniforms.night.value=c.night?1:0;
   const changedFocus=newFocus!==focusKey;
   if(changedFocus){
    const coords=c.night?solarPositionUTC(new Date()):{lat:c.focus_lat,lon:c.focus_lon};
    const from=point(coords.lat,coords.lon,1).normalize().multiplyScalar(c.night?-1:1);
    targetRotation.setFromUnitVectors(from,camera.position.clone().normalize());focusStartRotation.copy(root.quaternion);focusStarted=performance.now();focusStartDistance=camera.position.length();flying=true;focusKey=newFocus;
    el.dataset.focusLat=String(c.focus_lat);el.dataset.focusLon=String(c.focus_lon);el.dataset.focusRevision=String(c.focus_revision||0);
   }
   if(changedFocus||requestedDistance!==(c.camera_distance??7.4))wantedDistance=Math.max(6,Math.min(15,c.camera_distance??7.4));
   requestedDistance=c.camera_distance??7.4;
   const newMarkers=JSON.stringify([c.focus_label,c.markers,c.layer]);
   if(markerKey!==newMarkers){disposeObject(markers);markers.clear();markerKey=newMarkers;
    if(c.focus_label!=='GLOBAL')marker(c.focus_lat,c.focus_lon,c.focus_label,'#80edff');
    for(const p of c.markers||[])marker(p.lat,p.lon,p.label,p.color);
   }
   const observed=observations.current,newObservations=JSON.stringify([c.layer,observed.data,observed.iss]);
   if(newObservations!==observationKey){observationKey=newObservations;disposeObject(planes);planes.clear();
    const coords=c.layer==='FLIGHTS'?(observed.data?.aircraft||[]):[];
    for(const ac of coords.slice(0,120)){
     if(!Number.isFinite(ac.lat)||!Number.isFinite(ac.lon)||Math.abs(ac.lat)>90||Math.abs(ac.lon)>180)continue;
     const mesh=new THREE.Mesh(new THREE.ConeGeometry(.025,.09,3),new THREE.MeshBasicMaterial({color:0xffdd8a}));mesh.position.copy(point(ac.lat,ac.lon,2.3));mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),mesh.position.clone().normalize());planes.add(mesh);
    }
    if(observed.iss){const p=observed.iss;const mesh=new THREE.Mesh(new THREE.OctahedronGeometry(.045),new THREE.MeshBasicMaterial({color:0xffcf65}));mesh.position.copy(point(p.lat,p.lon,2.48));planes.add(mesh)}
   }
  };
  const targetRotation=root.quaternion.clone();apply.current=update;update();
  const userStart=()=>{flying=false;};const userEnd=()=>{wantedDistance=camera.position.length()};controls.addEventListener('start',userStart);controls.addEventListener('end',userEnd);
  let down:{x:number;y:number}|null=null;
  const pointerDown=(e:PointerEvent)=>down={x:e.clientX,y:e.clientY};
  const pointerUp=(e:PointerEvent)=>{if(!down||Math.hypot(e.clientX-down.x,e.clientY-down.y)>6){down=null;return;}down=null;const r=renderer.domElement.getBoundingClientRect(),ray=new THREE.Raycaster();ray.setFromCamera(new THREE.Vector2((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1),camera);const hit=ray.intersectObject(earth)[0];if(hit){const local=root.worldToLocal(hit.point.clone());setPicked(cartesianToEarth(local.x,local.y,local.z))}};
  renderer.domElement.addEventListener('pointerdown',pointerDown);renderer.domElement.addEventListener('pointerup',pointerUp);
  const resize=()=>{const w=Math.max(1,el.clientWidth),h=Math.max(1,el.clientHeight);renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix()};resize();const ro=new ResizeObserver(resize);ro.observe(el);
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
  const loop=(now:number)=>{if(dead||!visible||document.hidden){running=false;return;}raf=requestAnimationFrame(loop);const dt=last?Math.min(.05,(now-last)/1000):0;last=now;time+=dt;const c=latest.current;
   const p=phase.current,progress=reduced.matches?1:Math.min(1,(now-p.at)/1300),ease=progress*progress*(3-2*progress),reveal=p.value==='exit'?1-ease:p.value==='enter'?ease:1;
   uniforms.reveal.value=reveal;root.scale.setScalar(.18+.82*reveal);starMat.opacity=reveal*.75;cloudMat.opacity=reveal*.36;el.dataset.transition=p.value;el.dataset.reveal=reveal.toFixed(3);
   const focusProgress=reduced.matches?1:Math.min(1,(now-focusStarted)/1200),focusEase=focusProgress*focusProgress*(3-2*focusProgress);
   controls.update();
   if(flying){
    const coords=c.night?solarPositionUTC(new Date()):{lat:c.focus_lat,lon:c.focus_lon};
    targetRotation.setFromUnitVectors(point(coords.lat,coords.lon,1).normalize().multiplyScalar(c.night?-1:1),camera.position.clone().normalize());
    root.quaternion.slerpQuaternions(focusStartRotation,targetRotation,focusEase);
    camera.position.setLength(THREE.MathUtils.lerp(focusStartDistance,wantedDistance,focusEase));
    if(focusProgress>=1)flying=false;
   }else{
    if(c.auto_rotate&&!reduced.matches)root.rotateY(dt*(c.rotation_speed??.08));
    camera.position.setLength(THREE.MathUtils.lerp(camera.position.length(),wantedDistance,reduced.matches?1:1-Math.exp(-dt*4)));
   }
   el.dataset.cameraDistance=camera.position.length().toFixed(3);
   const solar=solarPositionUTC(new Date());uniforms.sun.value.copy(point(solar.lat,solar.lon,1)).applyQuaternion(root.quaternion).normalize();sun.position.copy(uniforms.sun.value).multiplyScalar(10);
   if(!c.sun_sync){uniforms.sun.value.set(.7,.35,1).normalize();sun.position.copy(uniforms.sun.value).multiplyScalar(10)}
   if(!reduced.matches)clouds.rotation.y+=dt*.009;
   renderer.render(scene,camera);el.dataset.focusFacing=point(c.focus_lat,c.focus_lon,1).applyQuaternion(root.quaternion).normalize().dot(camera.position.clone().normalize()).toFixed(4);el.dataset.geometries=String(renderer.info.memory.geometries);el.dataset.textures=String(renderer.info.memory.textures);el.dataset.frameMs=(dt*1000).toFixed(1);el.dataset.elapsed=time.toFixed(2);
  };
  const start=()=>{if(dead||running||!visible||document.hidden)return;running=true;last=0;raf=requestAnimationFrame(loop)};
  const visibility=()=>{if(document.hidden){cancelAnimationFrame(raf);running=false}else start()};document.addEventListener('visibilitychange',visibility);
  const io=new IntersectionObserver(entries=>{visible=Boolean(entries[0]?.isIntersecting);if(visible)start();else{cancelAnimationFrame(raf);running=false}});io.observe(el);start();
  return()=>{memory.current={position:camera.position.toArray(),orientation:root.quaternion.toArray(),focus:focusKey};dead=true;apply.current=()=>{};cancelAnimationFrame(raf);ro.disconnect();io.disconnect();document.removeEventListener('visibilitychange',visibility);renderer.domElement.removeEventListener('pointerdown',pointerDown);renderer.domElement.removeEventListener('pointerup',pointerUp);controls.dispose();disposeObject(scene);textures.forEach(t=>t.dispose());renderer.dispose();renderer.forceContextLoss();renderer.domElement.remove()};
 },[raster]);
 return <div className={'earth-watch-shell earth-engine-v7 '+(raster?'earth-raster':'')}>
  {raster?<Suspense fallback={<div className="earth-render-status">Harita motoru hazırlanıyor…</div>}>
   {layers[layer]?.available?<EarthMap config={config} layer={layers[layer]} onCommand={onCommand}/>:<div className="earth-render-status">{layers[layer]?.reason||'Harita kaynağı doğrulanıyor…'}</div>}
  </Suspense>:<div className="earth-watch-webgl" ref={host}/>}
  {!raster&&(webglError||textureStatus!=='loaded')&&<div className="earth-render-status" role="status">{webglError?'3D Dünya bu tarayıcıda kullanılamıyor.':textureStatus==='failed'?'Yüzey dokusu yüklenemedi.':'Yüzey dokusu yükleniyor…'}</div>}
  <div className="earth-watch-brand"><Globe2/><div><b>DÜNYA</b><small>{config.focus_label} · {raster?layer==='MAP'?'SOKAK HARİTASI':'LİSANSLI UYDU':'3D KÜRE'}</small></div></div>
  <div className="earth-layer-tabs" aria-label="Dünya katmanları">{MODES.map(([key,label])=><button key={key} aria-pressed={key==='NIGHT'?config.night:layer===key} className={(layer===key?'active ':'')+(key==='TERRAIN'||key==='SATELLITE'&&!layers.SATELLITE?.available?'unavailable':'')} title={key==='SATELLITE'?layers.SATELLITE?.reason:key==='TERRAIN'?'Yükseklik / bina verisi yapılandırılmadı':label} onClick={()=>onCommand(key==='NIGHT'?'earth_control':'earth_layer',key==='NIGHT'?{night:!config.night}:{layer:key})}>{label}{(key==='TERRAIN'||key==='SATELLITE'&&!layers.SATELLITE?.available)&&<small>YOK</small>}</button>)}</div>
  <form className="earth-place-search" onSubmit={e=>{e.preventDefault();if(query.trim())void onCommand('earth_search',{query})}}><Search/><input aria-label="Dünya konum ara" placeholder="Ülke, şehir veya yer adı…" value={query} onChange={e=>setQuery(e.target.value)}/><button>Ara</button></form>
  {search&&<div className="earth-search-results"><strong>{search.query} · {search.source}</strong><p>Hangi konum? Kaynaktaki sonuçlardan seç.</p>{search.hits.map((hit,i)=><button key={i} onClick={()=>onChoose?.(hit)}>{hit.label}<small>{hit.lat.toFixed(4)}°, {hit.lon.toFixed(4)}°</small></button>)}</div>}
  {(layer==='WEATHER'||layer==='FLIGHTS')&&<div className="earth-data-panel" role="status"><b>{layer==='WEATHER'?'HAVA DURUMU':'UÇUŞ VERİSİ'}</b><small>{dataStatus}</small>{data&&<><p>{data.source} · {data.updated||new Date(data.retrieved_at*1000).toISOString()}</p>{layer==='WEATHER'?<p>{data.current?.temperature_2m??'—'} °C · Rüzgâr {data.current?.wind_speed_10m??'—'} km/sa · {data.forecast_not_observation?'TAHMİN':'Sağlayıcı verisi'}</p>:<><p>{data.count} bildirilen uçak · yalnızca sağlayıcı kapsaması</p>{(data.aircraft||[]).slice(0,5).map((a:any)=><p key={a.hex}>{a.flight}: {a.lat.toFixed(3)}°, {a.lon.toFixed(3)}°</p>)}</>}</>}</div>}
  {layer==='LOCATIONS'&&<div className="earth-data-panel"><b>KAYITLI KONUMLAR</b>{config.markers.length?config.markers.map(m=><button key={m.id} onClick={()=>onCommand('earth_focus',{place:m.label,lat:m.lat,lon:m.lon})}>{m.label}</button>):<p>Bu sahnede kaydedilmiş konum yok.</p>}</div>}
  <div className="earth-watch-controls">
   <button className={config.auto_rotate?'active':''} onClick={()=>onCommand('earth_control',{auto_rotate:!config.auto_rotate})}>DÖNDÜR</button>
   <button className={config.clouds?'active':''} onClick={()=>onCommand('earth_control',{clouds:!config.clouds})}>BULUT</button>
   <button className={config.grid?'active':''} onClick={()=>onCommand('earth_control',{grid:!config.grid})}>IZGARA</button>
   <button className={config.atmosphere?'active':''} onClick={()=>onCommand('earth_control',{atmosphere:!config.atmosphere})}>ATMOSFER</button>
   <button className={config.sun_sync?'active':''} onClick={()=>onCommand('earth_control',{sun_sync:!config.sun_sync})}>UTC GÜNEŞ</button>
   <button className={config.live_iss?'active':''} onClick={()=>onCommand('earth_control',{live_iss:!config.live_iss})}>ISS {config.live_iss?(iss?'VERİ ALINDI':'VERİ YOK'):'KAPALI'}</button>
   <button onClick={()=>onCommand('earth_zoom',{factor:.77})}>YAKINLAŞ</button><button onClick={()=>onCommand('earth_zoom',{factor:1.3})}>UZAKLAŞ</button>
   <button onClick={()=>onCommand('earth_focus',{lat:20,lon:0,place:'GLOBAL',camera_distance:7.4})}>GLOBAL</button>
   <button onClick={()=>onCommand('earth_search',{query:'Türkiye'})}>TÜRKİYE</button><button onClick={()=>onCommand('earth_search',{query:'Kıbrıs'})}>KIBRIS</button>
   {showCoreButton&&<button onClick={()=>onCommand('reset')}><RotateCcw/> CORE</button>}
  </div>
  {picked&&<div className="earth-watch-pick"><LocateFixed/><span>{picked.lat.toFixed(4)}°, {picked.lon.toFixed(4)}°</span><button onClick={()=>onCommand('earth_focus',{lat:picked.lat,lon:picked.lon,place:'SEÇİLEN KONUM'})}>ODAKLAN</button><button onClick={()=>onCommand('earth_marker_add',{lat:picked.lat,lon:picked.lon,label:'KONUM',color:'#35caff'})}>KONUM EKLE</button></div>}
  <div className="earth-source-label">{raster?<>{layers[layer]?.source} · {layer==='MAP'?<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a>:layers[layer]?.attribution}</>:'Paketli yüzey görüntüsü · canlı uydu değildir · Yakın plan: Harita'} · {config.focus_lat.toFixed(4)}°, {config.focus_lon.toFixed(4)}°</div>
 </div>;
}
