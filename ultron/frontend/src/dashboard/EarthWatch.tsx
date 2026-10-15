import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {Globe2,LocateFixed,RotateCcw,Satellite} from 'lucide-react';
import {request,type EarthState} from './runtime';
import {cartesianToEarth,earthToCartesian,solarPositionUTC} from './earthMath';

function earthVector(lat:number,lon:number,r=2.25){
 const p=earthToCartesian(lat,lon,r);return new THREE.Vector3(p.x,p.y,p.z);
}
function vectorEarth(v:THREE.Vector3){return cartesianToEarth(v.x,v.y,v.z);}
function fallbackEarthTexture(){
 const canvas=document.createElement('canvas');canvas.width=2048;canvas.height=1024;const ctx=canvas.getContext('2d')!;
 const ocean=ctx.createLinearGradient(0,0,0,canvas.height);ocean.addColorStop(0,'#164c78');ocean.addColorStop(.48,'#0b416e');ocean.addColorStop(1,'#062e52');ctx.fillStyle=ocean;ctx.fillRect(0,0,canvas.width,canvas.height);
 const xy=(lon:number,lat:number)=>[(lon+180)/360*canvas.width,(90-lat)/180*canvas.height] as const;
 const poly=(points:number[][],fill:string)=>{ctx.beginPath();points.forEach((p,i)=>{const [x,y]=xy(p[0],p[1]);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.closePath();ctx.fillStyle=fill;ctx.fill();ctx.strokeStyle='#c8d6a244';ctx.lineWidth=1;ctx.stroke();};
 const land='#6e8750',dry='#8b8b58';
 poly([[-168,71],[-140,66],[-126,52],[-118,34],[-105,24],[-82,25],[-66,45],[-80,58],[-110,72]],land);
 poly([[-82,12],[-67,7],[-51,-5],[-48,-25],[-59,-48],[-72,-55],[-79,-28]],land);
 poly([[-18,35],[2,37],[15,31],[34,31],[51,13],[43,-13],[31,-34],[12,-35],[-3,-18],[-17,12]],dry);
 poly([[-10,36],[5,55],[30,70],[66,74],[98,61],[124,51],[146,55],[171,68],[166,45],[132,23],[112,7],[79,8],[55,26],[34,34],[20,45]],land);
 poly([[112,-11],[154,-10],[153,-39],[132,-44],[115,-30]],dry);
 poly([[-73,60],[-28,83],[-17,68],[-45,58]],'#89936f');
 poly([[45,-13],[50,-25],[49,-13]],land);
 ctx.globalAlpha=.16;ctx.strokeStyle='#dcecff';ctx.lineWidth=1;for(let lat=-60;lat<=60;lat+=30){const [,y]=xy(0,lat);ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(canvas.width,y);ctx.stroke();}for(let lon=-150;lon<=150;lon+=30){const [x]=xy(lon,0);ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,canvas.height);ctx.stroke();}ctx.globalAlpha=1;
 const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;texture.wrapS=THREE.RepeatWrapping;return texture;
}
function earthLabel(text:string,color='#ff334d'){
 const canvas=document.createElement('canvas');canvas.width=320;canvas.height=72;const ctx=canvas.getContext('2d')!;
 ctx.fillStyle='rgba(2,6,12,.80)';ctx.fillRect(2,2,316,68);ctx.strokeStyle=color;ctx.lineWidth=2;ctx.strokeRect(2,2,316,68);
 ctx.font='600 24px Rajdhani,Arial';ctx.fillStyle='#f4f7fa';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(text.slice(0,28),160,36);
 const tex=new THREE.CanvasTexture(canvas);tex.colorSpace=THREE.SRGBColorSpace;const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:tex,transparent:true,depthTest:false}));sprite.scale.set(1.35,.3,1);return sprite;
}
export function EarthWatch({config,onCommand,showCoreButton=true,showMapButton=true}:{config:EarthState;onCommand:(operation:string,extra?:Record<string,unknown>)=>Promise<unknown>|void;showCoreButton?:boolean;showMapButton?:boolean}){
 const host=useRef<HTMLDivElement>(null),[picked,setPicked]=useState<{lat:number;lon:number}|null>(null),[issOk,setIssOk]=useState(false);
 // Renderer rebuilds for layer changes; preserve the user's actual zoom/orbit and Earth orientation.
 const savedView=useRef<{position:number[];target:number[];orientation:number[];focus:string}|null>(null);
 const key=JSON.stringify(config);
 useEffect(()=>{const el=host.current;if(!el)return;let dead=false,raf=0,issTimer:ReturnType<typeof setInterval>|undefined;
  const focusKey=String(config.focus_lat)+':'+String(config.focus_lon);
  const previousView=savedView.current;
  const scene=new THREE.Scene();scene.background=new THREE.Color(config.night?0x000207:0x01050b);
  const camera=new THREE.PerspectiveCamera(42,1,.1,100);camera.position.set(0,.25,7.4);
  const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance',preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.setClearColor(config.night?0x000207:0x01050b,1);el.appendChild(renderer.domElement);
  const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.055;controls.enablePan=false;controls.minDistance=3.05;controls.maxDistance=15;
  if(previousView){camera.position.fromArray(previousView.position);controls.target.fromArray(previousView.target);controls.update();}
  const root=new THREE.Group();scene.add(root);
  const map=fallbackEarthTexture(),earthMat=new THREE.MeshStandardMaterial({map,roughness:.78,metalness:.02,color:config.night?0x7080a0:0xffffff});
  const earth=new THREE.Mesh(new THREE.SphereGeometry(2.25,96,64),earthMat);root.add(earth);
  const loader=new THREE.TextureLoader();loader.setCrossOrigin('anonymous');loader.load('https://threejs.org/examples/textures/planets/earth_atmos_2048.jpg',tex=>{if(dead){tex.dispose();return;}tex.colorSpace=THREE.SRGBColorSpace;earthMat.map?.dispose();earthMat.map=tex;earthMat.needsUpdate=true;},()=>{},()=>{});
  if(config.atmosphere){const atm=new THREE.Mesh(new THREE.SphereGeometry(2.34,72,48),new THREE.MeshBasicMaterial({color:0x3aa8ff,transparent:true,opacity:config.night ? .10 : .075,side:THREE.BackSide,blending:THREE.AdditiveBlending,depthWrite:false}));root.add(atm);}
  if(config.clouds){loader.load('https://threejs.org/examples/textures/planets/earth_clouds_1024.png',tex=>{if(dead){tex.dispose();return;}tex.colorSpace=THREE.SRGBColorSpace;const clouds=new THREE.Mesh(new THREE.SphereGeometry(2.285,72,48),new THREE.MeshPhongMaterial({map:tex,transparent:true,opacity:.42,depthWrite:false,blending:THREE.NormalBlending}));clouds.userData.clouds=true;root.add(clouds);},()=>{},()=>{});}
  const hemi=new THREE.HemisphereLight(config.night?0x24436f:0xc7e6ff,config.night?0x010205:0x07101b,config.night ? .25 : .72);scene.add(hemi);
  const sun=new THREE.DirectionalLight(0xffffff,config.night ? .72 : 2.25);sun.position.set(6,3,5);scene.add(sun);
  let sunCalculationAt=0,solarVector=earthVector(0,0,1);
  if(config.stars){const count=1800,pos=new Float32Array(count*3);for(let i=0;i<count;i++){const p=new THREE.Vector3().randomDirection().multiplyScalar(14+Math.random()*24);pos.set(p.toArray(),i*3);}const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.BufferAttribute(pos,3));scene.add(new THREE.Points(geo,new THREE.PointsMaterial({color:0xdceeff,size:.025,transparent:true,opacity:.8,depthWrite:false})));}
  if(config.grid){for(let lat=-60;lat<=60;lat+=30){const pts:THREE.Vector3[]=[];for(let lon=-180;lon<=180;lon+=4)pts.push(earthVector(lat,lon,2.267));root.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineBasicMaterial({color:0x63d8ff,transparent:true,opacity:.18})));}for(let lon=-150;lon<=180;lon+=30){const pts:THREE.Vector3[]=[];for(let lat=-88;lat<=88;lat+=3)pts.push(earthVector(lat,lon,2.267));root.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineBasicMaterial({color:0x63d8ff,transparent:true,opacity:.14})));}}
  const addMarker=(lat:number,lon:number,label:string,color:string,radius=2.3)=>{const group=new THREE.Group(),p=earthVector(lat,lon,radius),n=p.clone().normalize();group.position.copy(p);group.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),n);const pin=new THREE.Mesh(new THREE.ConeGeometry(.055,.24,10),new THREE.MeshStandardMaterial({color,emissive:color,emissiveIntensity:.55}));pin.position.y=.12;group.add(pin);const ring=new THREE.Mesh(new THREE.RingGeometry(.075,.105,28),new THREE.MeshBasicMaterial({color,transparent:true,opacity:.9,side:THREE.DoubleSide,depthWrite:false}));ring.rotation.x=-Math.PI/2;group.add(ring);const sprite=earthLabel(label,color);sprite.position.set(0,.32,0);group.add(sprite);root.add(group);return group;};
  for(const marker of config.markers||[])addMarker(marker.lat,marker.lon,marker.label,marker.color||'#ff334d');
  if(config.focus_label&&config.focus_label!=='GLOBAL')addMarker(config.focus_lat,config.focus_lon,config.focus_label,'#35ffe4',2.315);
  const focus=earthVector(config.focus_lat,config.focus_lon,1).normalize(),front=new THREE.Vector3(0,0,1);
  const focusRotation=new THREE.Quaternion().setFromUnitVectors(focus,front);
  if(previousView)root.quaternion.fromArray(previousView.orientation);else root.quaternion.copy(focusRotation);
  let flyingTo=Boolean(previousView&&previousView.focus!==focusKey);
  let issGroup:THREE.Group|undefined,issRequest:AbortController|undefined,issBusy=false;
  if(config.live_iss){
   issGroup=addMarker(0,0,'ISS TRACKING','#ffd43b',2.48);
   // Never draw a guessed ISS coordinate; hide the marker until a valid response arrives.
   issGroup.visible=false;
   const updateIss=async()=>{
    if(dead||issBusy)return;issBusy=true;
    const controller=new AbortController();issRequest=controller;
    const timeout=setTimeout(()=>controller.abort(),8000);
    try{
     const res=await fetch('https://api.wheretheiss.at/v1/satellites/25544',{cache:'no-store',signal:controller.signal});
     if(!res.ok)throw Error(String(res.status));
     const data=await res.json(),lat=Number(data.latitude),lon=Number(data.longitude);
     if(!Number.isFinite(lat)||!Number.isFinite(lon)||lat<-90||lat>90||lon<-180||lon>180)throw Error('invalid ISS coordinates');
     if(dead||!issGroup)return;
     const p=earthVector(lat,lon,2.48);issGroup.position.copy(p);
     issGroup.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),p.clone().normalize());
     issGroup.visible=true;setIssOk(true);
    }catch{if(!dead){if(issGroup)issGroup.visible=false;setIssOk(false);}}
    finally{clearTimeout(timeout);issBusy=false;if(issRequest===controller)issRequest=undefined;}
   };
   void updateIss();issTimer=setInterval(()=>void updateIss(),5000);
  }
  const ray=new THREE.Raycaster(),mouse=new THREE.Vector2();let pointerStart:{x:number;y:number}|null=null;
  const pointerDown=(e:PointerEvent)=>{pointerStart=e.button===0?{x:e.clientX,y:e.clientY}:null;};
  const pointerUp=(e:PointerEvent)=>{const start=pointerStart;pointerStart=null;if(!start||e.button!==0||Math.hypot(e.clientX-start.x,e.clientY-start.y)>6)return;
   const rect=renderer.domElement.getBoundingClientRect();mouse.x=((e.clientX-rect.left)/rect.width)*2-1;mouse.y=-((e.clientY-rect.top)/rect.height)*2+1;
   ray.setFromCamera(mouse,camera);const hit=ray.intersectObject(earth,false)[0];if(!hit)return;
   const local=root.worldToLocal(hit.point.clone());const ll=vectorEarth(local);setPicked({lat:+ll.lat.toFixed(4),lon:+ll.lon.toFixed(4)});
  };
  const pointerCancel=()=>{pointerStart=null;};
  renderer.domElement.addEventListener('pointerdown',pointerDown);
  renderer.domElement.addEventListener('pointerup',pointerUp);
  renderer.domElement.addEventListener('pointercancel',pointerCancel);
  renderer.domElement.addEventListener('pointerleave',pointerCancel);
  let last=performance.now();const resize=()=>{const w=Math.max(1,el.clientWidth),h=Math.max(1,el.clientHeight);renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();};resize();const ro=new ResizeObserver(resize);ro.observe(el);
  const loop=(now:number)=>{if(dead)return;const dt=Math.min(.05,(now-last)/1000);last=now;
   if(flyingTo){root.quaternion.slerp(focusRotation,1-Math.exp(-dt*4));if(root.quaternion.angleTo(focusRotation)<.003){root.quaternion.copy(focusRotation);flyingTo=false;}}
   else if(config.auto_rotate)root.rotateY(dt*Number(config.rotation_speed??.08));
   if(config.sun_sync){
    if(!sunCalculationAt||now-sunCalculationAt>60_000){
     const subsolar=solarPositionUTC(new Date());solarVector=earthVector(subsolar.lat,subsolar.lon,1);sunCalculationAt=now;
    }
    sun.position.copy(solarVector).applyQuaternion(root.quaternion).multiplyScalar(9);
   }
   const clouds=root.children.find(x=>x.userData.clouds);if(clouds)clouds.rotation.y+=dt*.012;
   controls.update();renderer.render(scene,camera);raf=requestAnimationFrame(loop);
  };raf=requestAnimationFrame(loop);
  return()=>{savedView.current={position:camera.position.toArray(),target:controls.target.toArray(),orientation:root.quaternion.toArray(),focus:focusKey};
   dead=true;cancelAnimationFrame(raf);if(issTimer)clearInterval(issTimer);issRequest?.abort();ro.disconnect();
   renderer.domElement.removeEventListener('pointerdown',pointerDown);renderer.domElement.removeEventListener('pointerup',pointerUp);
   renderer.domElement.removeEventListener('pointercancel',pointerCancel);renderer.domElement.removeEventListener('pointerleave',pointerCancel);
   controls.dispose();scene.traverse(o=>{const m=o as THREE.Mesh;if(m.geometry)m.geometry.dispose();const mats=(m as any).material?(Array.isArray((m as any).material)?(m as any).material:[(m as any).material]):[];for(const mat of mats){if(mat.map)mat.map.dispose();mat.dispose?.();}});renderer.dispose();renderer.domElement.remove();};
 },[key]);
 return <div className="earth-watch-shell"><div className="earth-watch-webgl" ref={host}/><div className="earth-watch-brand"><Globe2/><div><b>EARTH WATCH</b><small>{config.focus_label||'GLOBAL'} · 3D GLOBAL VIEW</small></div></div><div className="earth-watch-controls"><button className={config.auto_rotate?'active':''} onClick={()=>onCommand('earth_control',{auto_rotate:!config.auto_rotate})}>{config.auto_rotate?'ROTATION ON':'ROTATION OFF'}</button><button className={config.clouds?'active':''} onClick={()=>onCommand('earth_control',{clouds:!config.clouds})}>CLOUDS</button><button className={config.sun_sync?'active':''} onClick={()=>onCommand('earth_control',{sun_sync:!config.sun_sync})}>UTC SUN {config.sun_sync?'ON':'OFF'}</button><button className={config.atmosphere?'active':''} onClick={()=>onCommand('earth_control',{atmosphere:!config.atmosphere})}>ATMOSPHERE</button><button className={config.grid?'active':''} onClick={()=>onCommand('earth_control',{grid:!config.grid})}>LAT/LON GRID</button><button className={config.night?'active':''} onClick={()=>onCommand('earth_control',{night:!config.night})}>NIGHT</button><button className={config.live_iss?'active':''} onClick={()=>onCommand('earth_control',{live_iss:!config.live_iss})}><Satellite/> ISS {config.live_iss?(issOk?'LIVE':'WAIT'):'OFF'}</button><button onClick={()=>onCommand('earth_focus',{lat:20,lon:0,place:'GLOBAL'})}>GLOBAL</button><button onClick={()=>onCommand('earth_focus',{lat:39,lon:35,place:'TÜRKİYE'})}>TÜRKİYE</button><button onClick={()=>onCommand('earth_focus',{lat:35.13,lon:33.43,place:'KIBRIS'})}>KIBRIS</button>{showMapButton&&<button onClick={()=>onCommand('world_map')}><Globe2/> 2D HARİTA / LIVE</button>}{showCoreButton&&<button onClick={()=>onCommand('reset')}><RotateCcw/> CORE</button>}</div>{picked&&<div className="earth-watch-pick"><LocateFixed/><span>{picked.lat.toFixed(4)}°, {picked.lon.toFixed(4)}°</span><button onClick={()=>onCommand('earth_focus',{lat:picked.lat,lon:picked.lon,place:'SELECTED'})}>FOCUS</button><button onClick={()=>onCommand('earth_marker_add',{lat:picked.lat,lon:picked.lon,label:'PIN',color:'#ff3347'})}>PIN HERE</button></div>}</div>;
}
