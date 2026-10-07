import {useEffect,useMemo,useRef,useState} from 'react';
import * as THREE from 'three';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {TransformControls} from 'three/examples/jsm/controls/TransformControls.js';
import {GLTFExporter} from 'three/examples/jsm/exporters/GLTFExporter.js';
import {Download,Maximize2,Play,RotateCcw,Sparkles,Video} from 'lucide-react';
import UltronCore from './core/UltronCore';
import {request,type CoreState,type HologramConfig,type SceneObject,type SceneState,type StageState} from './runtime';

type Props={stage:StageState;state:CoreState;amplitude:number;notify:(text:string)=>void};

function colorOf(value:string){
 try{return new THREE.Color(value||'#ff3047');}catch{return new THREE.Color('#ff3047');}
}

function HologramStage({config,customModel}:{config:HologramConfig;customModel:ArrayBuffer|null}){
 const host=useRef<HTMLDivElement>(null);
 useEffect(()=>{
  const el=host.current;if(!el)return;
  const scene=new THREE.Scene();
  scene.fog=new THREE.FogExp2(0x020407,.055);
  const camera=new THREE.PerspectiveCamera(42,1,.1,100);camera.position.set(0,.25,7.6);
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'high-performance',preserveDrawingBuffer:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setClearColor(0x000000,0);
  el.appendChild(renderer.domElement);
  const root=new THREE.Group();scene.add(root);
  const color=colorOf(config.color),mat=new THREE.MeshBasicMaterial({color,transparent:true,opacity:config.opacity,wireframe:config.wireframe});
  const dim=new THREE.MeshBasicMaterial({color,transparent:true,opacity:Math.max(.12,config.opacity*.38),wireframe:true});
  const add=(g:THREE.BufferGeometry,m:THREE.Material=mat,x=0,y=0,z=0)=>{const mesh=new THREE.Mesh(g,m);mesh.position.set(x,y,z);root.add(mesh);return mesh;};
  const torus=(r:number,t=.012,rx=0,ry=0,rz=0)=>{const m=add(new THREE.TorusGeometry(r,t,8,128));m.rotation.set(rx,ry,rz);return m;};

  let dead=false;
  const kind=config.kind||'energy';
  if(customModel){
   const loader=new GLTFLoader();
   loader.parse(customModel.slice(0),'',gltf=>{
    if(dead)return;
    const model=gltf.scene;
    model.traverse(obj=>{
     const mesh=obj as THREE.Mesh;
     if(mesh.isMesh){
      mesh.material=new THREE.MeshBasicMaterial({
       color,transparent:true,opacity:config.opacity,
       wireframe:config.wireframe
      });
     }
    });
    const box=new THREE.Box3().setFromObject(model),size=new THREE.Vector3(),center=new THREE.Vector3();
    box.getSize(size);box.getCenter(center);
    model.position.sub(center);
    const max=Math.max(size.x,size.y,size.z,0.001);
    model.scale.setScalar(3.2/max);
    root.add(model);
   },err=>console.warn('Center Stage GLB:',err));
  }else if(kind==='globe'){
   add(new THREE.SphereGeometry(1.65,40,26),dim);
   for(let i=-3;i<=3;i++){const r=Math.sqrt(Math.max(.2,1-(i/4)**2))*1.65;const ring=torus(r,.009,Math.PI/2);ring.position.y=i*.38;}
   for(let i=0;i<8;i++)torus(1.65,.009,0,(i*Math.PI)/8,0);
  }else if(kind==='network'){
   const pts:THREE.Vector3[]=[];for(let i=0;i<32;i++){const p=new THREE.Vector3().randomDirection().multiplyScalar(1.6);pts.push(p);add(new THREE.SphereGeometry(.045,10,8),mat,p.x,p.y,p.z);}
   const pos:number[]=[];for(let i=0;i<pts.length;i++)for(let j=i+1;j<pts.length;j++)if(pts[i].distanceTo(pts[j])<1.15)pos.push(...pts[i].toArray(),...pts[j].toArray());
   const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));root.add(new THREE.LineSegments(geo,new THREE.LineBasicMaterial({color,transparent:true,opacity:.42})));
  }else if(kind==='drone'){
   const body=add(new THREE.OctahedronGeometry(.62,1));body.scale.set(1.5,.42,1);
   for(const x of [-1.25,1.25])for(const z of [-.75,.75]){const arm=add(new THREE.BoxGeometry(1.2,.06,.06),dim,x*.48,0,z*.48);arm.rotation.y=Math.atan2(z,x);torus(.42,.014,Math.PI/2,0,0).position.set(x,0,z);}
  }else if(kind==='vehicle'){
   const body=add(new THREE.BoxGeometry(2.7,.55,1.25),dim,0,0,0);body.rotation.x=.04;
   add(new THREE.BoxGeometry(1.3,.5,1.05),dim,-.15,.48,0);
   for(const x of [-.88,.88])for(const z of [-.68,.68]){const wheel=add(new THREE.TorusGeometry(.32,.08,8,40),mat,x,-.35,z);wheel.rotation.y=Math.PI/2;}
  }else if(kind==='logo'){
   torus(1.5,.035);torus(1.1,.018,Math.PI/2,.5,.2);torus(1.1,.018,.7,Math.PI/2,.8);
   const a=add(new THREE.ConeGeometry(.72,1.8,3),dim);a.rotation.z=Math.PI;a.position.y=.1;
  }else{
   add(new THREE.IcosahedronGeometry(kind==='sphere'?1.55:1.38,kind==='sphere'?3:2),kind==='sphere'?dim:mat);
   for(let i=0;i<Math.max(0,config.rings);i++)torus(1.65+i*.09,.01+i*.001,(i%3)*.47,(i%4)*.41,i*.7);
  }

  const count=Math.max(0,Math.min(5000,config.particles|0)),positions=new Float32Array(count*3);
  for(let i=0;i<count;i++){const p=new THREE.Vector3().randomDirection().multiplyScalar(2.0+Math.random()*1.15);positions.set(p.toArray(),i*3);}
  const pg=new THREE.BufferGeometry();pg.setAttribute('position',new THREE.BufferAttribute(positions,3));
  const pm=new THREE.PointsMaterial({color,size:.026,transparent:true,opacity:.52,depthWrite:false,blending:THREE.AdditiveBlending});
  const particles=new THREE.Points(pg,pm);root.add(particles);
  scene.add(new THREE.AmbientLight(0xffffff,.6));
  const light=new THREE.PointLight(color,Math.max(2,config.glow*16),20);light.position.set(2,3,4);scene.add(light);

  let frame=0,last=performance.now();
  const resize=()=>{const w=Math.max(1,el.clientWidth),h=Math.max(1,el.clientHeight);renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();};resize();
  const ro=new ResizeObserver(resize);ro.observe(el);
  const move=(e:PointerEvent)=>{const r=renderer.domElement.getBoundingClientRect();const x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;root.rotation.y=x*1.1;root.rotation.x=-y*.65;};
  renderer.domElement.addEventListener('pointermove',move);
  const loop=(now:number)=>{if(dead)return;const dt=Math.min(.05,(now-last)/1000);last=now;const pulse=config.pulse?1+Math.sin(now*.003)*.055:1;root.scale.setScalar(config.scale*pulse);root.rotation.y+=dt*.42*config.speed;particles.rotation.y-=dt*.11*config.speed;renderer.render(scene,camera);frame=requestAnimationFrame(loop);};frame=requestAnimationFrame(loop);
  return()=>{dead=true;cancelAnimationFrame(frame);ro.disconnect();renderer.domElement.removeEventListener('pointermove',move);renderer.dispose();scene.traverse(o=>{const m=o as THREE.Mesh;if(m.geometry)m.geometry.dispose();if((m as any).material){const a=Array.isArray((m as any).material)?(m as any).material:[(m as any).material];a.forEach((x:THREE.Material)=>x.dispose());}});renderer.domElement.remove();};
 },[config.kind,config.color,config.glow,config.speed,config.rings,config.particles,config.scale,config.opacity,config.wireframe,config.pulse,customModel]);
 return <div className="stage-hologram"><div ref={host} className="stage-webgl"/><div className="stage-holo-label"><b>{config.label||'ULTRON'}</b><span>{String(config.kind||'energy').toUpperCase()} HOLOGRAM</span></div></div>;
}


function sceneAccent(theme?:string){
 return {cyan:'#35ffe4',purple:'#a855f7',amber:'#ffb020',mono:'#d7e0e8',crimson:'#ff3047'}[theme||'crimson']||'#ff3047';
}
function sceneObjectRadius(kind?:string){
 return {vehicle:1.45,drone:1.35,globe:1.2,robot:1.05,arm:1,aircraft:1.5,ship:1.45,building:1.1,satellite:1.2,network:1.1,tower:1.15,ring:1.25,portal:1.25,custom:1}[kind||'']||1;
}
function lerp(a:number,b:number,t:number){return a+(b-a)*t;}
function easeValue(t:number,mode?:string){const x=Math.max(0,Math.min(1,t));if(mode==='ease_in')return x*x;if(mode==='ease_out')return 1-(1-x)*(1-x);if(mode==='ease_in_out')return x<.5?2*x*x:1-Math.pow(-2*x+2,2)/2;return x;}
function timelineCursor(scene:SceneState,nowSec=Date.now()/1000){
 const tl=scene.timeline;if(!tl)return 0;const d=Math.max(1,Number(tl.duration)||8);
 if(!tl.playing||!tl.started_at)return Math.max(0,Math.min(d,Number(tl.cursor)||0));
 const e=Math.max(0,nowSec-Number(tl.started_at));
 return tl.loop?e%d:Math.min(d,e);
}
function sampleSceneObject(scene:SceneState,o:SceneObject,time:number){
 const frames=(scene.timeline?.keyframes||[]).filter(k=>k.object_id===o.id).sort((a,b)=>a.time-b.time);
 const base={position:[...(o.position||[0,0,0])],rotation:[...(o.rotation||[0,0,0])],scale:Number(o.scale)||1};
 if(!frames.length)return base;
 if(time<=frames[0].time)return {position:[...frames[0].position],rotation:[...frames[0].rotation],scale:frames[0].scale};
 if(time>=frames[frames.length-1].time){const k=frames[frames.length-1];return {position:[...k.position],rotation:[...k.rotation],scale:k.scale};}
 let a=frames[0],b=frames[frames.length-1];
 for(let i=0;i<frames.length-1;i++)if(time>=frames[i].time&&time<=frames[i+1].time){a=frames[i];b=frames[i+1];break;}
 const span=Math.max(.0001,b.time-a.time),t=easeValue((time-a.time)/span,b.easing||'ease_in_out');
 return {position:[0,1,2].map(i=>lerp(a.position?.[i]||0,b.position?.[i]||0,t)),rotation:[0,1,2].map(i=>lerp(a.rotation?.[i]||0,b.rotation?.[i]||0,t)),scale:lerp(a.scale||1,b.scale||1,t)};
}
function sampleCameraTrack(scene:SceneState,time:number){
 const frames=[...(scene.camera_track||[])].sort((a,b)=>a.time-b.time);
 if(!frames.length)return null;
 if(time<=frames[0].time)return {position:[...frames[0].position],target:[...frames[0].target]};
 if(time>=frames[frames.length-1].time){const k=frames[frames.length-1];return {position:[...k.position],target:[...k.target]};}
 let a=frames[0],b=frames[frames.length-1];
 for(let i=0;i<frames.length-1;i++)if(time>=frames[i].time&&time<=frames[i+1].time){a=frames[i];b=frames[i+1];break;}
 const span=Math.max(.0001,b.time-a.time),t=easeValue((time-a.time)/span,b.easing||'ease_in_out');
 return {position:[0,1,2].map(i=>lerp(a.position?.[i]||0,b.position?.[i]||0,t)),target:[0,1,2].map(i=>lerp(a.target?.[i]||0,b.target?.[i]||0,t))};
}
function makeLabelSprite(text:string,color:string){
 const canvas=document.createElement('canvas');canvas.width=320;canvas.height=72;const ctx=canvas.getContext('2d')!;
 ctx.clearRect(0,0,320,72);ctx.fillStyle='rgba(2,4,7,.78)';ctx.fillRect(2,2,316,68);ctx.strokeStyle=color;ctx.lineWidth=2;ctx.strokeRect(2,2,316,68);
 ctx.font='600 26px Consolas,monospace';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle='#f5f7fa';ctx.fillText(text.slice(0,26),160,36);
 const tex=new THREE.CanvasTexture(canvas);tex.colorSpace=THREE.SRGBColorSpace;const mat=new THREE.SpriteMaterial({map:tex,transparent:true,depthTest:false});const sprite=new THREE.Sprite(mat);sprite.scale.set(1.9,.43,1);sprite.position.set(0,1.65,0);sprite.userData.labelTexture=tex;return sprite;
}
function makeHudSprite(title:string,value:string,unit:string,color:string){
 const canvas=document.createElement('canvas');canvas.width=420;canvas.height=130;const ctx=canvas.getContext('2d')!;
 ctx.fillStyle='rgba(2,5,9,.88)';ctx.fillRect(3,3,414,124);ctx.strokeStyle=color;ctx.lineWidth=3;ctx.strokeRect(3,3,414,124);
 ctx.fillStyle=color;ctx.font='600 20px Consolas,monospace';ctx.textAlign='left';ctx.fillText(title.slice(0,30),20,34);
 ctx.fillStyle='#f5f7fa';ctx.font='700 38px Consolas,monospace';ctx.fillText((value||'—').slice(0,24),20,82);
 ctx.fillStyle='#9eabb7';ctx.font='18px Consolas,monospace';ctx.textAlign='right';ctx.fillText(unit.slice(0,12),395,82);
 ctx.strokeStyle=color+'88';ctx.beginPath();ctx.moveTo(20,101);ctx.lineTo(395,101);ctx.stroke();
 const tex=new THREE.CanvasTexture(canvas);tex.colorSpace=THREE.SRGBColorSpace;const mat=new THREE.SpriteMaterial({map:tex,transparent:true,depthTest:false});const sprite=new THREE.Sprite(mat);sprite.scale.set(2.25,.7,1);sprite.userData.labelTexture=tex;sprite.userData.hudCanvas=canvas;sprite.userData.hudTitle=title;sprite.userData.hudUnit=unit;sprite.userData.hudColor=color;return sprite;
}
function updateHudSpriteValue(sprite:THREE.Sprite,value:string){
 const canvas=sprite.userData.hudCanvas as HTMLCanvasElement|undefined;if(!canvas)return;
 const ctx=canvas.getContext('2d');if(!ctx)return;const title=String(sprite.userData.hudTitle||'DATA'),unit=String(sprite.userData.hudUnit||''),color=String(sprite.userData.hudColor||'#35ffe4');
 ctx.clearRect(0,0,canvas.width,canvas.height);ctx.fillStyle='rgba(2,5,9,.88)';ctx.fillRect(3,3,414,124);ctx.strokeStyle=color;ctx.lineWidth=3;ctx.strokeRect(3,3,414,124);
 ctx.fillStyle=color;ctx.font='600 20px Consolas,monospace';ctx.textAlign='left';ctx.fillText(title.slice(0,30),20,34);
 ctx.fillStyle='#f5f7fa';ctx.font='700 38px Consolas,monospace';ctx.fillText(value.slice(0,24),20,82);
 ctx.fillStyle='#9eabb7';ctx.font='18px Consolas,monospace';ctx.textAlign='right';ctx.fillText(unit.slice(0,12),395,82);
 ctx.strokeStyle=color+'88';ctx.beginPath();ctx.moveTo(20,101);ctx.lineTo(395,101);ctx.stroke();
 const tex=sprite.userData.labelTexture as THREE.CanvasTexture|undefined;if(tex)tex.needsUpdate=true;
}

function SceneLab({scene,transformMode,amplitude,onCommand}:{scene:SceneState;transformMode:'translate'|'rotate'|'scale';amplitude:number;onCommand:(operation:string,extra?:Record<string,unknown>)=>void|Promise<unknown>}){
 const host=useRef<HTMLDivElement>(null),amplitudeRef=useRef(amplitude);amplitudeRef.current=amplitude;
 const key=JSON.stringify(scene);
 useEffect(()=>{
  const el=host.current;if(!el)return;
  const accent=sceneAccent(scene.theme),accentColor=colorOf(accent);
  const world=new THREE.Scene();world.fog=new THREE.FogExp2(0x020407,.038);
  const camera=new THREE.PerspectiveCamera(42,1,.1,100);
  const cam=scene.camera||'isometric',pose=scene.camera_pose;
  const posePosition=Array.isArray(pose?.position)?pose!.position:[],poseTarget=Array.isArray(pose?.target)?pose!.target:[];
  if(cam==='custom'&&posePosition.length>=3)camera.position.set(posePosition[0],posePosition[1],posePosition[2]);
  else if(cam==='front')camera.position.set(0,1.2,9);
  else if(cam==='top')camera.position.set(0,9,.01);
  else if(cam==='side')camera.position.set(9,1.2,0);
  else if(cam==='close')camera.position.set(0,.8,5.2);
  else camera.position.set(6,4.2,7.2);
  const initialTarget=cam==='custom'&&poseTarget.length>=3?new THREE.Vector3(poseTarget[0],poseTarget[1],poseTarget[2]):new THREE.Vector3(0,0,0);
  camera.lookAt(initialTarget);
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'high-performance'});
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setClearColor(0x000000,0);el.appendChild(renderer.domElement);
  const orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;orbit.dampingFactor=.07;orbit.enablePan=true;orbit.minDistance=3.5;orbit.maxDistance=18;orbit.autoRotate=scene.auto_orbit||scene.camera==='orbit';orbit.autoRotateSpeed=.55;orbit.target.copy(initialTarget);
  const saveCamera=()=>{if(scene.cinematic?.enabled)return;onCommand('scene_camera_pose',{position_json:JSON.stringify(camera.position.toArray().map(v=>+v.toFixed(4))),target_json:JSON.stringify(orbit.target.toArray().map(v=>+v.toFixed(4)))});};orbit.addEventListener('end',saveCamera);
  const sceneRoot=new THREE.Group();world.add(sceneRoot);
  const particleCount=700,particlePositions=new Float32Array(particleCount*3);for(let i=0;i<particleCount;i++){const p=new THREE.Vector3().randomDirection().multiplyScalar(4+Math.random()*7);particlePositions.set(p.toArray(),i*3);}const particleGeo=new THREE.BufferGeometry();particleGeo.setAttribute('position',new THREE.BufferAttribute(particlePositions,3));const particleField=new THREE.Points(particleGeo,new THREE.PointsMaterial({color:accentColor,size:.022,transparent:true,opacity:.34,depthWrite:false,blending:THREE.AdditiveBlending}));world.add(particleField);
  if(scene.grid){
   const grid=new THREE.GridHelper(14,28,accentColor.getHex(),colorOf(accent).multiplyScalar(.22).getHex());grid.position.y=-1.55;sceneRoot.add(grid);
  }
  const renderMode=scene.render_mode||'hologram';
  const renderColor=(o:SceneObject,dim=false)=>{
   if(renderMode==='blueprint'||renderMode==='xray')return colorOf('#35ffe4');
   if(renderMode==='thermal'){let hash=0;for(const ch of String(o.id||o.kind))hash=(hash*31+ch.charCodeAt(0))>>>0;const colors=['#ff2d20','#ff7a18','#ffd43b','#ff4fc3'];return colorOf(colors[hash%colors.length]);}
   if(renderMode==='solid')return colorOf(o.color||'#d7e0e8');
   return colorOf(o.color);
  };
  const matFor=(o:SceneObject,dim=false):THREE.Material=>{
   const opacity=renderMode==='xray'?(dim?.12:.28):renderMode==='blueprint'?(dim?.25:.72):dim?Math.max(.18,o.opacity*.38):o.opacity;
   const wireframe=renderMode==='blueprint'||renderMode==='xray'?true:(renderMode==='solid'?false:o.wireframe);
   if(renderMode==='solid')return new THREE.MeshStandardMaterial({color:renderColor(o,dim),wireframe:false,transparent:o.opacity<1,opacity:o.opacity,roughness:.5,metalness:.42});
   return new THREE.MeshBasicMaterial({color:renderColor(o,dim),wireframe,transparent:true,opacity,depthTest:renderMode!=='xray',blending:renderMode==='xray'?THREE.AdditiveBlending:THREE.NormalBlending});
  };
  const addPart=(group:THREE.Group,geo:THREE.BufferGeometry,mat:THREE.Material,pos:[number,number,number],dir:[number,number,number]=pos)=>{
   const m=new THREE.Mesh(geo,mat);m.position.set(...pos);m.userData.base=[...pos];m.userData.dir=[...dir];group.add(m);return m;
  };
  const objectGroups=new Map<string,THREE.Group>(),mixers:THREE.AnimationMixer[]=[];let dead=false;const sceneGltfLoader=new GLTFLoader();
  for(const o of scene.objects||[]){
   if(o.visible===false)continue;
   const group=new THREE.Group();group.userData.objectId=o.id;group.userData.basePosition=[...(o.position||[0,0,0])];group.userData.baseRotation=[...(o.rotation||[0,0,0])];group.userData.baseScale=o.scale||1;group.position.set(o.position?.[0]||0,o.position?.[1]||0,o.position?.[2]||0);group.rotation.set(o.rotation?.[0]||0,o.rotation?.[1]||0,o.rotation?.[2]||0);group.scale.setScalar(o.scale||1);
   const mat=matFor(o),dim=matFor(o,true);
   const kind=o.kind||'energy';
   if(kind==='custom'&&o.model_id){
    const holder=new THREE.Group();group.add(holder);
    sceneGltfLoader.load('/api/stage/model/'+encodeURIComponent(o.model_id),gltf=>{if(dead)return;const model=gltf.scene;model.traverse(node=>{const mesh=node as THREE.Mesh;if(mesh.isMesh){const old=mesh.material;mesh.material=matFor(o);if(Array.isArray(old))old.forEach(m=>m.dispose());else old?.dispose?.();}});const box=new THREE.Box3().setFromObject(model),size=new THREE.Vector3(),center=new THREE.Vector3();box.getSize(size);box.getCenter(center);model.position.sub(center);const max=Math.max(size.x,size.y,size.z,.001);model.scale.setScalar(2.4/max);holder.add(model);if(gltf.animations?.length){const mixer=new THREE.AnimationMixer(model);mixer.timeScale=Math.max(0,Number(o.clip_speed??1));for(const clip of gltf.animations.slice(0,4)){const action=mixer.clipAction(clip);action.paused=Boolean(o.clip_paused);action.play();}mixers.push(mixer);}},undefined,err=>console.warn('Scene Lab GLB:',o.model_id,err));
   }else if(kind==='vehicle'){
    addPart(group,new THREE.BoxGeometry(2.5,.48,1.15),dim,[0,0,0],[0,0,0]);
    addPart(group,new THREE.BoxGeometry(1.25,.48,.95),dim,[-.15,.46,0],[0,1,0]);
    for(const x of [-.82,.82])for(const z of [-.66,.66]){const w=addPart(group,new THREE.TorusGeometry(.3,.07,8,32),mat,[x,-.34,z],[x,-.5,z]);w.rotation.y=Math.PI/2;}
   }else if(kind==='drone'){
    addPart(group,new THREE.OctahedronGeometry(.58,1),mat,[0,0,0],[0,0,0]).scale.set(1.5,.42,1);
    for(const x of [-1.18,1.18])for(const z of [-.72,.72]){const arm=addPart(group,new THREE.BoxGeometry(1.15,.055,.055),dim,[x*.48,0,z*.48],[x,0,z]);arm.rotation.y=Math.atan2(z,x);const r=addPart(group,new THREE.TorusGeometry(.38,.018,8,40),mat,[x,0,z],[x,0,z]);r.rotation.x=Math.PI/2;}
   }else if(kind==='globe'){
    addPart(group,new THREE.SphereGeometry(1.2,28,20),dim,[0,0,0],[0,0,0]);
    for(let i=0;i<5;i++){const r=addPart(group,new THREE.TorusGeometry(1.22,.012,7,80),mat,[0,0,0],[0,0,0]);r.rotation.y=i*Math.PI/5;}
   }else if(kind==='network'){
    for(let i=0;i<16;i++){const p=new THREE.Vector3().randomDirection().multiplyScalar(.35+(i%5)*.23);addPart(group,new THREE.SphereGeometry(.055,8,6),mat,[p.x,p.y,p.z],[p.x,p.y,p.z]);}
   }else if(kind==='logo'){
    addPart(group,new THREE.TorusGeometry(1.2,.035,8,80),mat,[0,0,0],[0,0,0]);const a=addPart(group,new THREE.ConeGeometry(.62,1.55,3),dim,[0,.05,0],[0,.5,0]);a.rotation.z=Math.PI;
   }else if(kind==='ring'){
    const ring=addPart(group,new THREE.TorusGeometry(1.25,.025,8,100),mat,[0,0,0],[0,0,0]);ring.rotation.x=Math.PI/2;
   }else if(kind==='tower'){
    addPart(group,new THREE.CylinderGeometry(.28,.46,2.3,8),dim,[0,0,0],[0,0,0]);for(let i=0;i<4;i++){const r=addPart(group,new THREE.TorusGeometry(.7+i*.16,.012,7,70),mat,[0,-.8+i*.55,0],[0,-.8+i*.55,0]);r.rotation.x=Math.PI/2;}
   }else if(kind==='robot'){
    addPart(group,new THREE.BoxGeometry(.82,1.0,.48),dim,[0,.25,0],[0,.4,0]);addPart(group,new THREE.BoxGeometry(.58,.46,.46),mat,[0,1.02,0],[0,1.1,0]);
    for(const x of [-.62,.62]){addPart(group,new THREE.BoxGeometry(.22,.88,.22),mat,[x,.2,0],[x,.4,0]);addPart(group,new THREE.BoxGeometry(.28,.75,.3),dim,[x*.52,-.75,0],[x*.6,-1,0]);}
    addPart(group,new THREE.BoxGeometry(.18,.06,.05),mat,[-.14,1.05,.25],[-.14,1.05,.25]);addPart(group,new THREE.BoxGeometry(.18,.06,.05),mat,[.14,1.05,.25],[.14,1.05,.25]);
   }else if(kind==='arm'){
    addPart(group,new THREE.CylinderGeometry(.48,.62,.28,18),dim,[0,-.85,0],[0,-1,0]);const shoulder=addPart(group,new THREE.SphereGeometry(.25,16,12),mat,[0,-.55,0],[0,-.55,0]);const upper=addPart(group,new THREE.BoxGeometry(.28,1.15,.28),dim,[.25,-.05,0],[.5,.05,0]);upper.rotation.z=-.42;const elbow=addPart(group,new THREE.SphereGeometry(.22,14,10),mat,[.5,.45,0],[.7,.7,0]);const fore=addPart(group,new THREE.BoxGeometry(.25,1.0,.25),dim,[.72,.82,0],[1.05,1.15,0]);fore.rotation.z=-.55;addPart(group,new THREE.BoxGeometry(.48,.16,.42),mat,[1.0,1.2,0],[1.3,1.5,0]);void shoulder;void elbow;
   }else if(kind==='satellite'){
    addPart(group,new THREE.BoxGeometry(.72,.72,.72),dim,[0,0,0],[0,0,0]);for(const x of [-1.15,1.15])addPart(group,new THREE.BoxGeometry(1.35,.06,.72),mat,[x,0,0],[x,0,0]);const dish=addPart(group,new THREE.ConeGeometry(.5,.34,28,1,true),mat,[0,.62,0],[0,.8,0]);dish.rotation.x=Math.PI;
   }else if(kind==='aircraft'){
    const fus=addPart(group,new THREE.CylinderGeometry(.18,.3,2.7,16),dim,[0,0,0],[0,0,0]);fus.rotation.z=Math.PI/2;addPart(group,new THREE.BoxGeometry(1.25,.06,3.0),mat,[0,0,0],[0,0,0]);const tail=addPart(group,new THREE.BoxGeometry(.5,.7,.06),mat,[-1.0,.28,0],[-1.3,.5,0]);tail.rotation.z=-.3;
   }else if(kind==='building'){
    addPart(group,new THREE.BoxGeometry(1.25,2.35,1.25),dim,[0,0,0],[0,0,0]);for(let y=-.8;y<=.8;y+=.4)for(let x=-.42;x<=.42;x+=.28)addPart(group,new THREE.BoxGeometry(.12,.12,.02),mat,[x,y,.64],[x,y,.8]);addPart(group,new THREE.CylinderGeometry(.04,.04,.65,8),mat,[0,1.48,0],[0,1.8,0]);
   }else if(kind==='ship'){
    const hull=addPart(group,new THREE.BoxGeometry(2.6,.48,.86),dim,[0,0,0],[0,0,0]);hull.rotation.z=.03;addPart(group,new THREE.BoxGeometry(.75,.55,.65),mat,[-.35,.48,0],[-.4,.7,0]);for(const x of [-.9,.9]){const eng=addPart(group,new THREE.TorusGeometry(.23,.06,8,28),mat,[x,-.05,-.52],[x,-.05,-.8]);eng.rotation.y=Math.PI/2;}
   }else if(kind==='radar'){
    addPart(group,new THREE.CylinderGeometry(.18,.35,1.7,12),dim,[0,-.35,0],[0,-.5,0]);const dish=addPart(group,new THREE.ConeGeometry(.78,.34,32,1,true),mat,[0,.68,0],[0,.95,0]);dish.rotation.z=-.35;addPart(group,new THREE.SphereGeometry(.12,12,8),mat,[.22,.84,0],[.4,1.05,0]);
   }else if(kind==='portal'){
    for(let i=0;i<4;i++){const r=addPart(group,new THREE.TorusGeometry(.72+i*.18,.018+i*.004,8,96),i%2?dim:mat,[0,0,0],[0,0,0]);r.rotation.set(i*.35,i*.42,i*.2);}
   }else if(kind==='cube'){
    addPart(group,new THREE.BoxGeometry(1.45,1.45,1.45),dim,[0,0,0],[0,0,0]);for(const a of [-.9,.9]){const r=addPart(group,new THREE.TorusGeometry(.9,.012,8,80),mat,[0,0,0],[0,0,0]);r.rotation.x=a;}
   }else{
    addPart(group,new THREE.IcosahedronGeometry(kind==='sphere'?1.05:.9,kind==='sphere'?2:1),kind==='sphere'?dim:mat,[0,0,0],[0,0,0]);
    for(let i=0;i<3;i++){const r=addPart(group,new THREE.TorusGeometry(1.12+i*.16,.012,7,80),mat,[0,0,0],[0,0,0]);r.rotation.set(i*.55,i*.7,i);}
   }
   if(scene.show_labels!==false){const label=makeLabelSprite(o.label||o.kind,o.color||accent);label.userData.objectId=o.id;group.add(label);}
   group.traverse(ch=>{ch.userData.objectId=o.id;});
   if((scene.selected_ids?.length?scene.selected_ids:[scene.selected_id]).includes(o.id)){const helper=new THREE.BoxHelper(group,colorOf(o.id===scene.selected_id?'#ffffff':'#35ffe4'));helper.userData.selection=true;group.add(helper);}
   sceneRoot.add(group);objectGroups.set(o.id,group);
  }
  // Parent-child Scene Graph: child transforms become local to their parent.
  for(const o of scene.objects||[]){if(!o.parent_id)continue;const child=objectGroups.get(o.id),parent=objectGroups.get(o.parent_id);if(child&&parent&&child!==parent)parent.add(child);}
  if(scene.target_id){const target=objectGroups.get(scene.target_id);if(target){const reticle=new THREE.Group();reticle.userData.selection=true;for(let i=0;i<3;i++){const r=new THREE.Mesh(new THREE.TorusGeometry(1.35+i*.16,.018,7,80),new THREE.MeshBasicMaterial({color:i===1?0xffffff:0xff3047,transparent:true,opacity:.75,depthTest:false}));r.rotation.set(i*.55,i*.32,i*.8);reticle.add(r);}const crossGeo=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-1.8,0,0),new THREE.Vector3(1.8,0,0),new THREE.Vector3(0,-1.8,0),new THREE.Vector3(0,1.8,0)]);reticle.add(new THREE.LineSegments(crossGeo,new THREE.LineBasicMaterial({color:0xff3047,transparent:true,opacity:.58,depthTest:false})));reticle.userData.targetReticle=true;target.add(reticle);}}
  const collisionHelpers=new Map<string,THREE.Mesh>();
  if(scene.collision_overlay){
   for(const o of scene.objects||[]){const group=objectGroups.get(o.id);if(!group||o.visible===false)continue;const helper=new THREE.Mesh(new THREE.SphereGeometry(sceneObjectRadius(o.kind),18,12),new THREE.MeshBasicMaterial({color:0xff233f,wireframe:true,transparent:true,opacity:.32,depthTest:false}));helper.visible=false;helper.userData.selection=true;helper.userData.collisionHelper=true;group.add(helper);collisionHelpers.set(o.id,helper);}
  }
  let globalHudIndex=0;
  for(const card of scene.hud||[]){
   const sprite=makeHudSprite(card.title||'DATA',card.value||'',card.unit||'',card.color||accent);sprite.userData.hudCard=true;
   const parent=card.object_id?objectGroups.get(card.object_id):undefined;
   if(parent){sprite.position.set(0,2.2+(parent.children.filter(x=>x.userData.hudCard).length*.7),0);parent.add(sprite);}
   else{sprite.position.set(-3.8,2.5-globalHudIndex*.75,0);sceneRoot.add(sprite);globalHudIndex++;}
  }
  const linkLines=new Map<string,{line:THREE.Line,source:string,target:string}>();
  for(const link of scene.links||[]){
   if(!objectGroups.has(link.source)||!objectGroups.has(link.target))continue;
   const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute([0,0,0,0,0,0],3));
   const line=new THREE.Line(geo,new THREE.LineDashedMaterial({color:colorOf(link.color||accent),dashSize:.12,gapSize:.07,transparent:true,opacity:.48}));
   line.computeLineDistances();sceneRoot.add(line);linkLines.set(link.id,{line,source:link.source,target:link.target});
  }
  const measurementLines=new Map<string,{line:THREE.Line,label:THREE.Sprite,source:string,target:string,last:string}>();
  for(const measurement of scene.measurements||[]){
   if(!objectGroups.has(measurement.source)||!objectGroups.has(measurement.target))continue;
   const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute([0,0,0,0,0,0],3));
   const color=measurement.color||'#ffd43b',line=new THREE.Line(geo,new THREE.LineDashedMaterial({color:colorOf(color),dashSize:.08,gapSize:.05,transparent:true,opacity:.88}));
   line.computeLineDistances();const label=makeHudSprite(measurement.label||'DIST','0.00','m',color);label.scale.set(1.45,.45,1);label.userData.measurement=true;sceneRoot.add(line);sceneRoot.add(label);
   measurementLines.set(measurement.id,{line,label,source:measurement.source,target:measurement.target,last:''});
  }
  if(scene.show_trails!==false&&scene.selected_id){
   const selectedObj=(scene.objects||[]).find(o=>o.id===scene.selected_id);
   if(selectedObj){
    const frames=(scene.timeline?.keyframes||[]).filter(k=>k.object_id===selectedObj.id).sort((a,b)=>a.time-b.time);
    let points:THREE.Vector3[]=[];
    if(frames.length>=2)points=frames.map(k=>new THREE.Vector3(k.position?.[0]||0,k.position?.[1]||0,k.position?.[2]||0));
    else if(selectedObj.motion?.type==='orbit'){const base=selectedObj.position||[0,0,0],rad=Number(selectedObj.motion.radius)||1.5;for(let i=0;i<=64;i++){const a=i/64*Math.PI*2;points.push(new THREE.Vector3((base[0]||0)+Math.cos(a)*rad,base[1]||0,(base[2]||0)+Math.sin(a)*rad));}}
    else if((selectedObj.path?.points?.length||0)>=2){points=(selectedObj.path?.points||[]).map(p=>new THREE.Vector3(p?.[0]||0,p?.[1]||0,p?.[2]||0));}
    else if(selectedObj.motion?.type==='patrol'){const base=selectedObj.position||[0,0,0],amp=Number(selectedObj.motion.amplitude)||1.4;points=[new THREE.Vector3((base[0]||0)-amp*2,base[1]||0,base[2]||0),new THREE.Vector3((base[0]||0)+amp*2,base[1]||0,base[2]||0)];}
    if(points.length>=2){const geo=new THREE.BufferGeometry().setFromPoints(points),line=new THREE.Line(geo,new THREE.LineDashedMaterial({color:accentColor,dashSize:.15,gapSize:.08,transparent:true,opacity:.58}));line.computeLineDistances();sceneRoot.add(line);}
   }
  }
  const transform=new TransformControls(camera,renderer.domElement);transform.setMode(transformMode);transform.setSize(.72);
  const snap=Math.max(0,Number(scene.snap)||0);transform.setTranslationSnap(snap||null);transform.setScaleSnap(snap||null);transform.setRotationSnap(snap?THREE.MathUtils.degToRad(15):null);
  const selectedData=(scene.objects||[]).find(o=>o.id===scene.selected_id),selected=scene.selected_id?objectGroups.get(scene.selected_id):undefined;
  if(selected&&!selectedData?.locked)transform.attach(selected);
  transform.addEventListener('dragging-changed',(event:any)=>{orbit.enabled=!event.value;});
  transform.addEventListener('mouseUp',()=>{
   const obj=transform.object as THREE.Object3D|undefined;if(!obj)return;const id=String(obj.userData.objectId||scene.selected_id||'');if(!id)return;
   const avgScale=(obj.scale.x+obj.scale.y+obj.scale.z)/3;
   onCommand('scene_update',{object_id:id,x:+obj.position.x.toFixed(3),y:+obj.position.y.toFixed(3),z:+obj.position.z.toFixed(3),rx:+obj.rotation.x.toFixed(3),ry:+obj.rotation.y.toFixed(3),rz:+obj.rotation.z.toFixed(3),scale:+avgScale.toFixed(3)});
  });
  world.add(transform.getHelper());
  const scan=new THREE.Mesh(new THREE.RingGeometry(.8,3.6,64),new THREE.MeshBasicMaterial({color:accentColor,wireframe:true,transparent:true,opacity:.16,side:THREE.DoubleSide}));scan.rotation.x=Math.PI/2;scan.visible=scene.animation==='scan';sceneRoot.add(scan);
  world.add(new THREE.AmbientLight(0xffffff,.7));const light=new THREE.PointLight(accentColor,14,30);light.position.set(3,5,5);world.add(light);
  let raf=0,last=performance.now(),lastTriggerCheck=0;const triggerLocalFire=new Map<string,number>();
  const resize=()=>{const w=Math.max(1,el.clientWidth),h=Math.max(1,el.clientHeight);renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();};resize();const ro=new ResizeObserver(resize);ro.observe(el);
  const ray=new THREE.Raycaster(),mouse=new THREE.Vector2();
  const click=(e:PointerEvent)=>{const r=renderer.domElement.getBoundingClientRect();mouse.x=((e.clientX-r.left)/r.width)*2-1;mouse.y=-((e.clientY-r.top)/r.height)*2+1;ray.setFromCamera(mouse,camera);const hits=ray.intersectObjects([...objectGroups.values()],true);const hit=hits.find(h=>!h.object.userData.selection);if(hit){let obj:THREE.Object3D|null=hit.object;while(obj&&!obj.userData.objectId)obj=obj.parent;const id=obj?.userData.objectId;if(id)onCommand(e.shiftKey?'scene_multi_select':'scene_select',e.shiftKey?{object_id:id,selection_mode:'toggle'}:{object_id:id});}};
  renderer.domElement.addEventListener('pointerdown',click);
  const exportGlb=()=>{const clean=sceneRoot.clone(true),remove:THREE.Object3D[]=[];clean.traverse(node=>{if(node instanceof THREE.Sprite||node.userData.selection||node.userData.hudCard)remove.push(node);});for(const node of remove)node.removeFromParent();const exporter=new GLTFExporter();exporter.parse(clean,result=>{if(!(result instanceof ArrayBuffer))return;const blob=new Blob([result],{type:'model/gltf-binary'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=(scene.project_name||'ultron-scene').replace(/[^a-zA-Z0-9_-]+/g,'_')+'.glb';a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);},err=>console.warn('Scene GLB export:',err),{binary:true,trs:true,onlyVisible:true,maxTextureSize:2048});};
  window.addEventListener('ultron-scene-export-glb',exportGlb as EventListener);
  const loop=(now:number)=>{if(dead)return;const dt=Math.min(.05,(now-last)/1000);last=now;const seconds=now/1000,tlTime=timelineCursor(scene,Date.now()/1000);
   for(const mixer of mixers)mixer.update(dt);
   for(const o of scene.objects||[]){const g=objectGroups.get(o.id);if(!g)continue;const sampled=sampleSceneObject(scene,o,tlTime),motion=o.motion||{type:'none',speed:1,radius:1.5,amplitude:.5,axis:'y'};let px=sampled.position[0]||0,py=sampled.position[1]||0,pz=sampled.position[2]||0;const ms=Number(motion.speed)||1,amp=Number(motion.amplitude)||.5,rad=Number(motion.radius)||1.5;
    if(motion.type==='orbit'){px+=Math.cos(seconds*ms)*rad;pz+=Math.sin(seconds*ms)*rad;}
    else if(motion.type==='bob'){py+=Math.sin(seconds*ms*2)*amp;}
    else if(motion.type==='patrol'){px+=Math.sin(seconds*ms)*amp*2;}
    const path=o.path;if(path?.started_at&&(path.points?.length||0)>=2){
     const pts=path.points||[],speed=Math.max(.05,Number(path.speed)||1),elapsed=Math.max(0,Date.now()/1000-Number(path.started_at));
     const lengths:number[]=[];let total=0;for(let i=0;i<pts.length-1;i++){const a=pts[i],b=pts[i+1],d=Math.hypot((b?.[0]||0)-(a?.[0]||0),(b?.[1]||0)-(a?.[1]||0),(b?.[2]||0)-(a?.[2]||0));lengths.push(d);total+=d;}
     if(total>.0001){let travel=elapsed*speed;if(path.loop)travel%=total;else travel=Math.min(total,travel);let seg=0;while(seg<lengths.length-1&&travel>lengths[seg]){travel-=lengths[seg];seg++;}const a=pts[seg]||pts[0],b=pts[Math.min(seg+1,pts.length-1)]||a,span=Math.max(.0001,lengths[seg]||1),q=Math.max(0,Math.min(1,travel/span));px=lerp(a?.[0]||0,b?.[0]||0,q);py=lerp(a?.[1]||0,b?.[1]||0,q);pz=lerp(a?.[2]||0,b?.[2]||0,q);}
    }
    const physics=o.physics;if(physics&&physics.mode&&physics.mode!=='off'&&physics.started_at){
     const pt=Math.max(0,Date.now()/1000-Number(physics.started_at)),v=physics.velocity||[0,0,0],vx=Number(v[0])||0,vy=Number(v[1])||0,vz=Number(v[2])||0,gForce=Math.max(0,Number(physics.gravity)||0),floor=Number(physics.floor??-1.3),bounce=Math.max(0,Math.min(1,Number(physics.bounce)||0));
     if(physics.mode==='drop'||physics.mode==='launch'){px+=vx*pt;pz+=vz*pt;const ballistic=py+vy*pt-.5*gForce*pt*pt;if(ballistic>=floor)py=ballistic;else{const settle=Math.exp(-pt*.28),height=Math.max(.03,bounce*1.25*settle);py=floor+Math.abs(Math.sin(pt*(3.5+gForce*.12)))*height;}}
     else if(physics.mode==='zero_g'){px+=vx*pt;py+=vy*pt;pz+=vz*pt;}
     else if(physics.mode==='float'){px+=Math.cos(pt*.65)*.18;py+=Math.sin(pt*1.4)*.45;pz+=Math.sin(pt*.48)*.15;}
    }
    g.position.set(px,py,pz);g.rotation.set(sampled.rotation[0]||0,(sampled.rotation[1]||0)+seconds*(o.spin||0),sampled.rotation[2]||0);const pulse=motion.type==='pulse'?1+Math.sin(seconds*ms*3)*Math.min(.35,amp*.18):1,audioBoost=scene.audio_reactive!==false?1+Math.min(.1,Math.max(0,amplitudeRef.current)*.12):1;g.scale.setScalar((sampled.scale||1)*pulse*audioBoost);
    const ex=Math.max(0,Number(scene.explode||0)+Number(o.explode||0));g.traverse(ch=>{if(!(ch instanceof THREE.Mesh)||!ch.userData.base)return;const b=ch.userData.base as number[],d=ch.userData.dir as number[];ch.position.set(b[0]+d[0]*ex*.35,b[1]+d[1]*ex*.35,b[2]+d[2]*ex*.35);});
   }
   sceneRoot.updateMatrixWorld(true);const worldA=new THREE.Vector3(),worldB=new THREE.Vector3();
   for(const o of scene.objects||[]){const constraint=o.constraint,g=objectGroups.get(o.id);if(!g||!constraint||constraint.type==='none'||!constraint.target_id)continue;const target=objectGroups.get(constraint.target_id);if(!target)continue;
    const targetWorld=new THREE.Vector3();target.getWorldPosition(targetWorld);const offset=constraint.offset||[0,0,0],speed=Math.max(.05,Number(constraint.speed)||1),distance=Math.max(.2,Number(constraint.distance)||2);
    if(constraint.type==='look_at'){g.lookAt(targetWorld);}
    else{
     let desired=targetWorld.clone();
     if(constraint.type==='orbit_target'){const a=seconds*speed;desired.add(new THREE.Vector3(Math.cos(a)*distance,Number(offset[1])||0,Math.sin(a)*distance));}
     else desired.add(new THREE.Vector3(Number(offset[0])||0,Number(offset[1])||0,Number(offset[2])||distance));
     if(constraint.type==='follow'){const current=g.userData.constraintWorld instanceof THREE.Vector3?(g.userData.constraintWorld as THREE.Vector3):g.getWorldPosition(new THREE.Vector3());current.lerp(desired,1-Math.exp(-dt*speed*3));g.userData.constraintWorld=current.clone();desired=current;}
     const parent=g.parent;if(parent){const local=parent.worldToLocal(desired.clone());g.position.copy(local);}else g.position.copy(desired);
     g.updateMatrixWorld(true);g.lookAt(targetWorld);
    }
   }
   sceneRoot.updateMatrixWorld(true);
   if((scene.triggers?.length||0)>0&&now-lastTriggerCheck>=120){lastTriggerCheck=now;const wall=Date.now()/1000;
    for(const trigger of scene.triggers||[]){if(!trigger.enabled||(trigger.once&&trigger.fired))continue;const lastLocal=triggerLocalFire.get(trigger.id)||0,lastRemote=Number(trigger.last_fired_at||0),cooldown=Math.max(.1,Number(trigger.cooldown)||2);if(wall-Math.max(lastLocal,lastRemote)<cooldown)continue;
     let matched=false;
     if(trigger.condition_type==='timer')matched=wall-Number(trigger.armed_at||wall)>=Math.max(0,Number(trigger.delay)||0);
     else{const a=trigger.source_id?objectGroups.get(trigger.source_id):undefined,b=trigger.target_id?objectGroups.get(trigger.target_id):undefined;if(a&&b){const ap=new THREE.Vector3(),bp=new THREE.Vector3(),as=new THREE.Vector3(),bs=new THREE.Vector3();a.getWorldPosition(ap);b.getWorldPosition(bp);const distance=ap.distanceTo(bp),threshold=Math.max(.05,Number(trigger.threshold)||2);if(trigger.condition_type==='distance_lt')matched=distance<threshold;else if(trigger.condition_type==='distance_gt')matched=distance>threshold;else if(trigger.condition_type==='collision'){a.getWorldScale(as);b.getWorldScale(bs);const ao=(scene.objects||[]).find(x=>x.id===trigger.source_id),bo=(scene.objects||[]).find(x=>x.id===trigger.target_id),ar=sceneObjectRadius(ao?.kind)*Math.max(Math.abs(as.x),Math.abs(as.y),Math.abs(as.z)),br=sceneObjectRadius(bo?.kind)*Math.max(Math.abs(bs.x),Math.abs(bs.y),Math.abs(bs.z));matched=distance<(ar+br)*.72;}}}
     if(!matched)continue;triggerLocalFire.set(trigger.id,wall);Promise.resolve(onCommand('scene_trigger_fire',{trigger_id:trigger.id})).then(()=>{if(trigger.action_operation) return onCommand(trigger.action_operation,trigger.action_args||{});}).catch(()=>{});
    }
   }
   const targetGroup=scene.target_id?objectGroups.get(scene.target_id):undefined;if(targetGroup){const reticle=targetGroup.children.find(x=>x.userData.targetReticle);if(reticle){reticle.rotation.x+=dt*.38;reticle.rotation.y+=dt*.62;reticle.rotation.z-=dt*.31;const pulse=1+Math.sin(seconds*4)*.08;reticle.scale.setScalar(pulse);}}
   for(const item of linkLines.values()){const a=objectGroups.get(item.source),b=objectGroups.get(item.target);if(!a||!b)continue;a.getWorldPosition(worldA);b.getWorldPosition(worldB);const pa=sceneRoot.worldToLocal(worldA.clone()),pb=sceneRoot.worldToLocal(worldB.clone()),attr=item.line.geometry.getAttribute('position') as THREE.BufferAttribute;attr.setXYZ(0,pa.x,pa.y,pa.z);attr.setXYZ(1,pb.x,pb.y,pb.z);attr.needsUpdate=true;item.line.computeLineDistances();}
   for(const item of measurementLines.values()){const a=objectGroups.get(item.source),b=objectGroups.get(item.target);if(!a||!b)continue;a.getWorldPosition(worldA);b.getWorldPosition(worldB);const distance=worldA.distanceTo(worldB),pa=sceneRoot.worldToLocal(worldA.clone()),pb=sceneRoot.worldToLocal(worldB.clone()),attr=item.line.geometry.getAttribute('position') as THREE.BufferAttribute;attr.setXYZ(0,pa.x,pa.y,pa.z);attr.setXYZ(1,pb.x,pb.y,pb.z);attr.needsUpdate=true;item.line.computeLineDistances();item.label.position.copy(pa.clone().add(pb).multiplyScalar(.5)).add(new THREE.Vector3(0,.28,0));const formatted=distance.toFixed(2);if(formatted!==item.last){item.last=formatted;updateHudSpriteValue(item.label,formatted);}}
   if(scene.collision_overlay){for(const helper of collisionHelpers.values())helper.visible=false;const visible=(scene.objects||[]).filter(o=>o.visible!==false);for(let i=0;i<visible.length;i++){const aData=visible[i],a=objectGroups.get(aData.id);if(!a)continue;const ap=new THREE.Vector3(),as=new THREE.Vector3();a.getWorldPosition(ap);a.getWorldScale(as);const ar=sceneObjectRadius(aData.kind)*Math.max(Math.abs(as.x),Math.abs(as.y),Math.abs(as.z));for(let j=i+1;j<visible.length;j++){const bData=visible[j],b=objectGroups.get(bData.id);if(!b)continue;const bp=new THREE.Vector3(),bs=new THREE.Vector3();b.getWorldPosition(bp);b.getWorldScale(bs);const br=sceneObjectRadius(bData.kind)*Math.max(Math.abs(bs.x),Math.abs(bs.y),Math.abs(bs.z));if(ap.distanceTo(bp)<(ar+br)*.72){const ah=collisionHelpers.get(aData.id),bh=collisionHelpers.get(bData.id);if(ah)ah.visible=true;if(bh)bh.visible=true;}}}}
   const focus=scene.focus_id?objectGroups.get(scene.focus_id):undefined;if(focus&&!scene.cinematic?.enabled&&!scene.timeline?.playing)orbit.target.lerp(focus.position,.08);
   const cin=scene.cinematic,cameraTrackActive=!cin?.enabled&&Boolean(scene.timeline?.playing)&&(scene.camera_track?.length||0)>0;
   if(cin?.enabled&&cin.started_at){const d=Math.max(2,Number(cin.duration)||8),elapsed=Math.max(0,Date.now()/1000-Number(cin.started_at)),p=(cin.loop?elapsed%d:Math.min(d,elapsed))/d,a=p*Math.PI*2;
    if(cin.preset==='flyby')camera.position.set(lerp(-8,8,p),2.2,5.5);
    else if(cin.preset==='topdown')camera.position.set(Math.sin(a)*2,8.5,Math.cos(a)*2);
    else if(cin.preset==='hero')camera.position.set(Math.sin(a*.5)*2.2,1.2+Math.sin(a)*.6,4.4+Math.cos(a)*.7);
    else if(cin.preset==='spiral'){const r=8-4*p;camera.position.set(Math.cos(a*2)*r,2+4*p,Math.sin(a*2)*r);}
    else camera.position.set(Math.cos(a)*7,3.4,Math.sin(a)*7);camera.lookAt(0,0,0);orbit.target.set(0,0,0);
   }else if(cameraTrackActive){
    const shot=sampleCameraTrack(scene,tlTime);if(shot){camera.position.set(shot.position[0]||0,shot.position[1]||0,shot.position[2]||0);orbit.target.set(shot.target[0]||0,shot.target[1]||0,shot.target[2]||0);camera.lookAt(orbit.target);}
   }
   particleField.rotation.y+=dt*.018;particleField.rotation.x=Math.sin(now*.00008)*.08;if(scene.audio_reactive!==false)(particleField.material as THREE.PointsMaterial).opacity=.28+Math.min(.45,Math.max(0,amplitudeRef.current)*.55);
   if(scan.visible)scan.position.y=-1.3+((now*.001)%1)*2.6;if(!cin?.enabled&&!cameraTrackActive)orbit.update();renderer.render(world,camera);raf=requestAnimationFrame(loop);};raf=requestAnimationFrame(loop);
  return()=>{dead=true;cancelAnimationFrame(raf);for(const mixer of mixers)mixer.stopAllAction();ro.disconnect();renderer.domElement.removeEventListener('pointerdown',click);window.removeEventListener('ultron-scene-export-glb',exportGlb as EventListener);transform.detach();transform.dispose();orbit.removeEventListener('end',saveCamera);orbit.dispose();renderer.dispose();world.traverse(o=>{const m=o as THREE.Mesh;if(m.geometry)m.geometry.dispose();const tex=(o as any).userData?.labelTexture;if(tex)tex.dispose();const mm=(m as any).material;if(mm)(Array.isArray(mm)?mm:[mm]).forEach((x:THREE.Material)=>x.dispose());});renderer.domElement.remove();};
 },[key,transformMode]);
 return <div className="scene-lab-webgl" ref={host}/>;
}

function SceneTimeline({scene,onCommand}:{scene:SceneState;onCommand:(operation:string,extra?:Record<string,unknown>)=>void}){
 const [,tick]=useState(0),tl=scene.timeline||{duration:8,cursor:0,playing:false,loop:true,started_at:null,keyframes:[]};
 useEffect(()=>{if(!tl.playing)return;const id=setInterval(()=>tick(v=>v+1),60);return()=>clearInterval(id);},[tl.playing,tl.started_at]);
 const cursor=timelineCursor(scene),duration=Math.max(1,Number(tl.duration)||8),selected=scene.selected_id,frames=(tl.keyframes||[]).filter(k=>!selected||k.object_id===selected);
 return <div className="scene-timeline">
  <div className="timeline-head"><b>TIMELINE</b><span>{cursor.toFixed(2)}s / {duration.toFixed(1)}s</span><button onClick={()=>onCommand(tl.playing?'timeline_pause':'timeline_play')}>{tl.playing?'PAUSE':'PLAY'}</button><button disabled={!selected} onClick={()=>onCommand('timeline_capture',{time:cursor})}>+ KEY</button><button onClick={()=>onCommand('timeline_capture_all',{time:cursor,selection_mode:(scene.selected_ids?.length||0)>1?'selected':'all'})}>KEY ALL</button><button onClick={()=>onCommand('camera_keyframe_capture',{time:cursor})}>+ CAM KEY</button><button disabled={!selected} onClick={()=>onCommand('timeline_preset',{preset:'showcase',duration})}>SHOWCASE</button><button disabled={!selected} onClick={()=>onCommand('timeline_preset',{preset:'launch',duration})}>LAUNCH</button><button onClick={()=>onCommand('timeline_shift',{delta_time:-.5,selection_mode:'all'})}>← .5s</button><button onClick={()=>onCommand('timeline_shift',{delta_time:.5,selection_mode:'all'})}>.5s →</button><button onClick={()=>onCommand('camera_track_clear')}>CAM CLEAR</button><button onClick={()=>onCommand('timeline_clear')}>CLEAR</button></div>
  <div className="timeline-track"><input type="range" min="0" max={duration} step=".05" value={cursor} onChange={e=>onCommand('timeline_seek',{time:+e.target.value})}/><i className="timeline-playhead" style={{left:(cursor/duration*100)+'%'}}/>{frames.map(k=><button className="timeline-key" key={k.id} title={k.time.toFixed(2)+'s'} style={{left:(k.time/duration*100)+'%'}} onDoubleClick={()=>onCommand('timeline_remove_keyframe',{keyframe_id:k.id})}/>)}{(scene.camera_track||[]).map(k=><button className="timeline-camera-key" key={k.id} title={'CAM '+k.time.toFixed(2)+'s'} style={{left:(k.time/duration*100)+'%'}} onDoubleClick={()=>onCommand('camera_keyframe_remove',{keyframe_id:k.id})}/>)}</div>
 </div>;
}

function drawVideoFrame(ctx:CanvasRenderingContext2D,w:number,h:number,p:number,stage:StageState){
 const video=stage.video,color=colorOf(stage.hologram.color),theme='#'+color.getHexString(),title=video.title||'ULTRON',template=video.template||'ultron_intro';
 ctx.fillStyle='#020407';ctx.fillRect(0,0,w,h);
 const g=ctx.createRadialGradient(w*.5,h*.48,10,w*.5,h*.48,w*.48);g.addColorStop(0,theme+'55');g.addColorStop(.45,theme+'13');g.addColorStop(1,'#00000000');ctx.fillStyle=g;ctx.fillRect(0,0,w,h);
 ctx.save();ctx.translate(w/2,h/2);ctx.strokeStyle=theme;ctx.shadowColor=theme;ctx.shadowBlur=16;ctx.globalAlpha=.9;
 const spin=p*Math.PI*2*(template==='energy_core'?2.2:1);
 if(template==='hologram_capture'&&stage.video.source_scene){
  const objs=stage.scene.objects||[],sceneTime=p*Math.max(1,stage.scene.timeline?.duration||stage.video.duration||8);ctx.save();const cin=stage.scene.cinematic?.preset||'orbit';if(cin==='hero')ctx.scale(1.12+Math.sin(p*Math.PI)*.12,1.12+Math.sin(p*Math.PI)*.12);else if(cin==='flyby')ctx.translate(lerp(120,-120,p),0);else ctx.rotate(spin*.08);
  for(const [i,o] of objs.entries()){if(o.visible===false)continue;const sampled=sampleSceneObject(stage.scene,o,sceneTime),motion=o.motion||{type:'none',speed:1,radius:1.5,amplitude:.5,axis:'y'};let ox=sampled.position[0]||0,oy=sampled.position[1]||0,oz=sampled.position[2]||0;const ms=Number(motion.speed)||1,amp=Number(motion.amplitude)||.5,rad=Number(motion.radius)||1.5,time=p*Math.max(2,stage.video.duration||8);if(motion.type==='orbit'){ox+=Math.cos(time*ms)*rad;oz+=Math.sin(time*ms)*rad;}else if(motion.type==='bob')oy+=Math.sin(time*ms*2)*amp;else if(motion.type==='patrol')ox+=Math.sin(time*ms)*amp*2;const x=ox*70,y=-oz*42+oy*55,s=36*(sampled.scale||1)*(motion.type==='pulse'?1+Math.sin(time*ms*3)*.12:1);ctx.save();ctx.translate(x,y);ctx.rotate((sampled.rotation?.[1]||0)+spin*(o.spin||.3)*.15+i*.2);ctx.strokeStyle=o.color||theme;ctx.globalAlpha=o.opacity||.85;ctx.strokeRect(-s,-s*.6,s*2,s*1.2);ctx.beginPath();ctx.arc(0,0,s*.65,0,Math.PI*2);ctx.stroke();ctx.font='12px Consolas';ctx.fillStyle=o.color||theme;ctx.textAlign='center';ctx.fillText(o.label||o.kind,0,s*.95);if((o.explode||0)+(stage.scene.explode||0)>0){ctx.globalAlpha=.3;for(let q=0;q<4;q++){ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(Math.cos(q*Math.PI/2)*s*1.5,Math.sin(q*Math.PI/2)*s);ctx.stroke();}}ctx.restore();}
  ctx.restore();
 }else if(template==='hologram_capture'){
  const kind=stage.hologram.kind||'energy';ctx.save();ctx.rotate(spin*.32);ctx.lineWidth=2.2;ctx.globalAlpha=.9;
  if(kind==='globe'){
   ctx.beginPath();ctx.arc(0,0,185,0,Math.PI*2);ctx.stroke();
   for(let i=-3;i<=3;i++){const y=i*42,r=Math.sqrt(Math.max(0,185*185-y*y));ctx.beginPath();ctx.ellipse(0,y,r,r*.22,0,0,Math.PI*2);ctx.stroke();}
   for(let i=0;i<6;i++){ctx.save();ctx.rotate(i*Math.PI/6);ctx.beginPath();ctx.ellipse(0,0,65,185,0,0,Math.PI*2);ctx.stroke();ctx.restore();}
  }else if(kind==='drone'){
   ctx.strokeRect(-92,-34,184,68);for(const [x,y] of [[-165,-95],[165,-95],[-165,95],[165,95]]){ctx.beginPath();ctx.moveTo(Math.sign(x)*92,Math.sign(y)*28);ctx.lineTo(x,y);ctx.stroke();ctx.beginPath();ctx.arc(x,y,48,0,Math.PI*2);ctx.stroke();ctx.beginPath();ctx.arc(x,y,31,spin*5,spin*5+Math.PI*1.2);ctx.stroke();}
  }else if(kind==='vehicle'){
   ctx.beginPath();ctx.moveTo(-205,62);ctx.lineTo(-158,-28);ctx.lineTo(-65,-70);ctx.lineTo(74,-68);ctx.lineTo(145,-25);ctx.lineTo(214,28);ctx.lineTo(188,70);ctx.lineTo(-190,70);ctx.closePath();ctx.stroke();for(const x of [-125,125]){ctx.beginPath();ctx.arc(x,76,43,0,Math.PI*2);ctx.stroke();ctx.beginPath();ctx.arc(x,76,22,0,Math.PI*2);ctx.stroke();}}
  else if(kind==='network'){
   const nodes:Array<[number,number]>=[];for(let i=0;i<22;i++){const a=i*2.399+spin*.22,r=55+(i%6)*27;nodes.push([Math.cos(a)*r,Math.sin(a)*r]);}
   for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){const dx=nodes[i][0]-nodes[j][0],dy=nodes[i][1]-nodes[j][1];if(dx*dx+dy*dy<9500){ctx.globalAlpha=.24;ctx.beginPath();ctx.moveTo(...nodes[i]);ctx.lineTo(...nodes[j]);ctx.stroke();}}
   ctx.globalAlpha=.95;for(const [x,y] of nodes){ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.fillStyle=theme;ctx.fill();}
  }else if(kind==='logo'){
   ctx.beginPath();ctx.arc(0,0,188,0,Math.PI*2);ctx.stroke();ctx.beginPath();ctx.moveTo(0,-155);ctx.lineTo(-105,115);ctx.lineTo(0,68);ctx.lineTo(105,115);ctx.closePath();ctx.stroke();ctx.beginPath();ctx.arc(0,0,112,spin,spin+Math.PI*1.45);ctx.stroke();
  }else{
   for(let i=0;i<Math.max(3,stage.hologram.rings||4);i++){ctx.beginPath();ctx.ellipse(0,0,120+i*20,(120+i*20)*(.55+.09*Math.sin(i)),spin*(i%2?1:-1)+i*.5,0,Math.PI*2);ctx.stroke();}
   ctx.beginPath();ctx.arc(0,0,105+Math.sin(spin*2)*12,0,Math.PI*2);ctx.stroke();
  }
  ctx.restore();
 }else{
  for(let i=0;i<7;i++){ctx.beginPath();ctx.ellipse(0,0,145+i*24,(145+i*24)*(.52+.12*Math.sin(i)),spin*(i%2?1:-1)+i*.4,0,Math.PI*2);ctx.lineWidth=i%2?2:1;ctx.stroke();}
 }
 for(let i=0;i<120;i++){const a=i*.618+spin,r=50+(i%19)*13+Math.sin(p*Math.PI*2+i)*18;ctx.fillStyle=i%5===0?'#fff':theme;ctx.globalAlpha=.25+.7*((i%11)/11);ctx.fillRect(Math.cos(a)*r,Math.sin(a)*r,2+(i%3),2+(i%3));}
 ctx.globalAlpha=1;ctx.font='700 64px Segoe UI,Arial';ctx.textAlign='center';ctx.fillStyle='#f4f5f8';ctx.shadowBlur=22;const reveal=Math.min(1,p*3.5);ctx.globalAlpha=reveal;ctx.fillText(title,0,16);
 ctx.font='18px Consolas,monospace';ctx.fillStyle=theme;ctx.fillText(template.replaceAll('_',' ').toUpperCase(),0,58);
 if(template==='system_activation'){ctx.font='17px Consolas,monospace';ctx.textAlign='left';for(let i=0;i<6;i++){const y=-150+i*34;ctx.globalAlpha=Math.min(1,Math.max(0,p*8-i*.5));ctx.fillText(['NEURAL CORE','MEMORY','VISION','TOOLS','NETWORK','SYSTEM READY'][i],-250,y);}}
 if(template==='task_complete'){ctx.font='700 34px Segoe UI';ctx.fillStyle='#fff';ctx.textAlign='center';ctx.fillText(p>.45?'TASK COMPLETE':'PROCESSING',0,125);}
 ctx.restore();
 ctx.globalAlpha=.75;ctx.strokeStyle=theme;ctx.lineWidth=2;ctx.strokeRect(32,32,w-64,h-64);ctx.globalAlpha=1;
}

function VideoRenderer({stage,onReady,onError,onProgress}:{stage:StageState;onReady:(url:string,blob:Blob)=>void;onError:(s:string)=>void;onProgress:(n:number)=>void}){
 const canvas=useRef<HTMLCanvasElement>(null),started=useRef('');
 useEffect(()=>{
  const job=String(stage.job_id||'');if(stage.mode!=='video_rendering'||!job||started.current===job)return;started.current=job;
  const c=canvas.current;if(!c)return;const ctx=c.getContext('2d');if(!ctx)return;
  const capture=(c as HTMLCanvasElement & {captureStream?:(fps?:number)=>MediaStream}).captureStream;
  if(typeof capture!=='function'||typeof MediaRecorder==='undefined'){onError('Bu Chromium sürümü canvas video kaydını desteklemiyor.');return;}
  const stream=capture.call(c,30),types=['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'];const mime=types.find(t=>MediaRecorder.isTypeSupported(t))||'video/webm';
  let recorder:MediaRecorder;let cancelled=false;try{recorder=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:5_000_000});}catch(e){onError('Video encoder başlatılamadı: '+String(e));return;}
  const chunks:BlobPart[]=[];recorder.ondataavailable=e=>{if(!cancelled&&e.data.size)chunks.push(e.data);};
  recorder.onerror=()=>{if(!cancelled)onError('Video render sırasında encoder hatası oluştu.');};
  recorder.onstop=()=>{stream.getTracks().forEach(t=>t.stop());if(cancelled)return;const blob=new Blob(chunks,{type:mime});if(!blob.size){onError('Video çıktısı boş oluştu.');return;}const url=URL.createObjectURL(blob);onReady(url,blob);void request('/api/stage/video-ready',{job_id:job,mime,bytes:blob.size}).catch(e=>onError(String(e)));};
  const duration=Math.max(2,Math.min(15,Number(stage.video.duration)||6))*1000,start=performance.now();let raf=0,lastProgress=-1;
  recorder.start(250);onProgress(0);
  const frame=(now:number)=>{const elapsed=now-start,p=Math.min(1,elapsed/duration);drawVideoFrame(ctx,c.width,c.height,p,stage);const progress=Math.floor(p*100);if(progress!==lastProgress){lastProgress=progress;onProgress(progress);}if(p<1)raf=requestAnimationFrame(frame);else{cancelAnimationFrame(raf);setTimeout(()=>{if(recorder.state!=='inactive')recorder.stop();},120);}};raf=requestAnimationFrame(frame);
  return()=>{cancelled=true;cancelAnimationFrame(raf);if(recorder.state!=='inactive')try{recorder.stop()}catch{};stream.getTracks().forEach(t=>t.stop());};
 },[stage.job_id,stage.mode]);
 return <canvas ref={canvas} width={1280} height={720} className="stage-render-canvas"/>;
}

function SceneSequenceStatus({scene}:{scene:SceneState}){
 const [,tick]=useState(0),seq=scene.sequence;
 useEffect(()=>{if(!seq?.playing)return;const id=setInterval(()=>tick(v=>v+1),100);return()=>clearInterval(id);},[seq?.playing,seq?.run_id]);
 if(!seq?.steps?.length)return null;
 const elapsed=seq.playing&&seq.started_at?Math.max(0,Date.now()/1000-Number(seq.started_at)):0;
 const duration=Math.max(.01,Number(seq.duration)||0),progress=seq.playing?Math.min(100,elapsed/duration*100):0;
 const current=[...seq.steps].reverse().find(s=>elapsed>=Number(s.at))||seq.steps[0];
 return <div className={'scene-sequence-status '+(seq.playing?'playing':'')}><header><b>MISSION SEQUENCE</b><span>{seq.name||'UNTITLED'}</span></header><div className="sequence-progress"><i style={{width:progress+'%'}}/></div><footer><span>{seq.playing?'RUNNING':'READY'} · {seq.steps.length} STEPS</span><b>{current?.label||'—'}</b></footer></div>;
}

export default function CenterStage({stage,state,amplitude,notify}:Props){
 const [videoUrl,setVideoUrl]=useState(''),[videoBlob,setVideoBlob]=useState<Blob|null>(null),[renderError,setRenderError]=useState(''),[renderProgress,setRenderProgress]=useState(0),[liveRecordProgress,setLiveRecordProgress]=useState(0),[customModel,setCustomModel]=useState<ArrayBuffer|null>(null),[customModelName,setCustomModelName]=useState(''),[transformMode,setTransformMode]=useState<'translate'|'rotate'|'scale'>('translate'),[showProjects,setShowProjects]=useState(false),[projects,setProjects]=useState<Array<{id:string;name:string;updated_at:number}>>([]),[showAssets,setShowAssets]=useState(false),[assets,setAssets]=useState<Array<{id:string;name:string;bytes:number;created_at:number}>>([]),[showDiagnostics,setShowDiagnostics]=useState(false),[diagnostics,setDiagnostics]=useState<any>(stage.diagnostics_result||null),[showSnapshots,setShowSnapshots]=useState(false),[snapshots,setSnapshots]=useState<Array<{id:string;name:string;created_at:number}>>([]),[projectName,setProjectName]=useState(stage.scene.project_name||'Untitled');
 const video=useRef<HTMLVideoElement>(null),modelFile=useRef<HTMLInputElement>(null),sceneFile=useRef<HTMLInputElement>(null),sceneModelFile=useRef<HTMLInputElement>(null),lastSaveNonce=useRef(Number(stage.save_nonce||0)),lastRecordNonce=useRef(Number(stage.record_nonce||0)),lastHologramKind=useRef(stage.hologram.kind);
 useEffect(()=>()=>{if(videoUrl)URL.revokeObjectURL(videoUrl);},[videoUrl]);
 useEffect(()=>{if(stage.mode==='video_rendering'){setRenderError('');setRenderProgress(0);}},[stage.job_id,stage.mode]);
 useEffect(()=>{if(stage.scene.project_name&&stage.scene.project_name!==projectName)setProjectName(stage.scene.project_name);},[stage.scene.project_name]);
 useEffect(()=>{if(lastHologramKind.current!==stage.hologram.kind){lastHologramKind.current=stage.hologram.kind;if(customModel){setCustomModel(null);setCustomModelName('');}}},[stage.hologram.kind]);
 useEffect(()=>{if(video.current)stage.video_paused?video.current.pause():video.current.play().catch(()=>{});},[stage.video_paused,stage.revision]);
 const patch=(body:Record<string,unknown>)=>request('/api/stage/control',body).catch(e=>notify(String(e)));
 const command=(operation:string,extra:Record<string,unknown>={})=>request('/api/stage/command',{operation,...extra}).catch(e=>notify(String(e)));
 const refreshProjects=async(open=true)=>{try{const data=await request('/api/stage/command',{operation:'scene_project_list'});setProjects(Array.isArray(data?.project_result?.projects)?data.project_result.projects:[]);if(open)setShowProjects(true);}catch(err){notify(String(err));}};
 const saveProject=async()=>{try{const data=await request('/api/stage/command',{operation:'scene_project_save',project_name:projectName||'Untitled'});const saved=data?.project_result?.name||projectName;setProjectName(saved);await refreshProjects(true);}catch(err){notify(String(err));}};
 const loadProject=async(id:string)=>{try{await request('/api/stage/command',{operation:'scene_project_load',project_id:id});setShowProjects(false);}catch(err){notify(String(err));}};
 const deleteProject=async(id:string)=>{try{await request('/api/stage/command',{operation:'scene_project_delete',project_id:id});await refreshProjects(true);}catch(err){notify(String(err));}};
 const refreshAssets=async(open=true)=>{try{const data=await request('/api/stage/models');setAssets(Array.isArray(data?.models)?data.models:[]);if(open)setShowAssets(true);}catch(err){notify(String(err));}};
 const addAsset=async(asset:{id:string;name:string})=>{try{await command('scene_add',{kind:'custom',model_id:asset.id,label:asset.name.replace(/\.glb$/i,''),color:'#ff3047',wireframe:true});setShowAssets(false);}catch(err){notify(String(err));}};
 const deleteAsset=async(id:string)=>{try{await request('/api/stage/model/delete',{model_id:id});await refreshAssets(true);}catch(err){notify(String(err));}};
 const runDiagnostics=async()=>{try{const data=await request('/api/stage/command',{operation:'scene_diagnostics'});setDiagnostics(data?.diagnostics_result||null);setShowDiagnostics(true);}catch(err){notify(String(err));}};
 const refreshSnapshots=async(open=true)=>{try{const data=await request('/api/stage/command',{operation:'scene_snapshot_list'});setSnapshots(Array.isArray(data?.snapshot_result?.snapshots)?data.snapshot_result.snapshots:[]);if(open)setShowSnapshots(true);}catch(err){notify(String(err));}};
 const saveSnapshot=async()=>{try{await request('/api/stage/command',{operation:'scene_snapshot_save',snapshot_name:(projectName||'Scene')+' '+new Date().toLocaleTimeString('tr-TR')});await refreshSnapshots(true);}catch(err){notify(String(err));}};
 const restoreSnapshot=async(id:string)=>{try{await request('/api/stage/command',{operation:'scene_snapshot_restore',snapshot_id:id});setShowSnapshots(false);}catch(err){notify(String(err));}};
 const deleteSnapshot=async(id:string)=>{try{await request('/api/stage/command',{operation:'scene_snapshot_delete',snapshot_id:id});await refreshSnapshots(true);}catch(err){notify(String(err));}};
 const captureScene=()=>{const canvas=document.querySelector<HTMLCanvasElement>('.scene-lab-webgl canvas');if(!canvas){notify('Scene Lab canvas bulunamadı.');return;}try{const a=document.createElement('a');a.href=canvas.toDataURL('image/png');a.download='ultron-scene-'+new Date().toISOString().replace(/[:.]/g,'-')+'.png';a.click();}catch(err){notify('Sahne görüntüsü alınamadı: '+String(err));}};
 useEffect(()=>{const seq=stage.scene.sequence;if(stage.mode!=='scene_lab'||!seq?.playing||!seq.started_at||!seq.steps?.length)return;let cancelled=false;const timers:Array<ReturnType<typeof setTimeout>>=[];const start=Number(seq.started_at)*1000,duration=Math.max(.5,Number(seq.duration)||0)+.35;
  const schedule=(cycle:number)=>{const cycleStart=start+cycle*duration*1000;for(const step of seq.steps){const delay=Math.max(0,cycleStart+Number(step.at||0)*1000-Date.now());timers.push(setTimeout(()=>{if(cancelled)return;void request('/api/stage/command',{operation:step.operation,...(step.args||{})}).catch(err=>notify('Sequence step: '+String(err)));},delay));}
   const endDelay=Math.max(0,cycleStart+duration*1000-Date.now());timers.push(setTimeout(()=>{if(cancelled)return;if(seq.loop)schedule(cycle+1);else void request('/api/stage/command',{operation:'scene_sequence_stop'}).catch(()=>{});},endDelay));
  };schedule(0);return()=>{cancelled=true;for(const timer of timers)clearTimeout(timer);};},[stage.mode,stage.scene.sequence?.run_id,stage.scene.sequence?.playing]);
 useEffect(()=>{if(stage.mode!=='scene_lab')return;const key=(e:KeyboardEvent)=>{const target=e.target as HTMLElement|null;if(target&&['INPUT','TEXTAREA','SELECT'].includes(target.tagName))return;const id=stage.scene.selected_id;
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='a'){e.preventDefault();void command('scene_multi_select',{selection_mode:'all'});return;}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='g'&&(stage.scene.selected_ids?.length||0)>1){e.preventDefault();void command('scene_group_create',{group_name:'GROUP '+((stage.scene.groups?.length||0)+1)});return;}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='d'&&id){e.preventDefault();void command('scene_duplicate',{object_id:id});return;}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();void command(e.shiftKey?'scene_redo':'scene_undo');return;}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='y'){e.preventDefault();void command('scene_redo');return;}
  if(e.key==='Delete'&&id){e.preventDefault();void command('scene_remove',{object_id:id});return;}
  if(e.code==='Space'){e.preventDefault();void command(stage.scene.timeline?.playing?'timeline_pause':'timeline_play');return;}
  if(e.key.toLowerCase()==='w')setTransformMode('translate');else if(e.key.toLowerCase()==='e')setTransformMode('rotate');else if(e.key.toLowerCase()==='r')setTransformMode('scale');
 };window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[stage.mode,stage.scene.selected_id,stage.scene.selected_ids?.length,stage.scene.groups?.length,stage.scene.timeline?.playing]);
 const downloadVideo=()=>{if(!videoBlob||!videoUrl){notify('Bu oturumda video verisi yok. Videoyu yeniden render et.');return;}const a=document.createElement('a');a.href=videoUrl;a.download='ultron-'+(stage.video.template||'animation')+'.webm';a.click();};
 const downloadHologram=()=>{const payload={version:1,type:'ultron-center-stage',saved_at:new Date().toISOString(),hologram:stage.hologram,custom_model:customModelName||null};const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='ultron-hologram.ultron.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);};
 const downloadScene=()=>{const payload={version:3,type:'ultron-scene',saved_at:new Date().toISOString(),scene:stage.scene};const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='ultron-scene.ultron-scene.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);};
 useEffect(()=>{const nonce=Number(stage.save_nonce||0);if(!nonce||nonce===lastSaveNonce.current)return;lastSaveNonce.current=nonce;if(stage.save_kind==='video')downloadVideo();else if(stage.save_kind==='hologram')downloadHologram();else if(stage.save_kind==='scene')downloadScene();},[stage.save_nonce,stage.save_kind,videoBlob,videoUrl,stage.hologram,stage.video.template]);
 useEffect(()=>{const nonce=Number(stage.record_nonce||0);if(!nonce||nonce===lastRecordNonce.current)return;lastRecordNonce.current=nonce;const canvas=document.querySelector<HTMLCanvasElement>('.scene-lab-webgl canvas');if(!canvas){notify('Canlı Scene Lab canvas bulunamadı.');return;}const capture=(canvas as HTMLCanvasElement&{captureStream?:(fps?:number)=>MediaStream}).captureStream;if(typeof capture!=='function'||typeof MediaRecorder==='undefined'){notify('Bu Chromium sürümü canlı 3D video kaydını desteklemiyor.');return;}const stream=capture.call(canvas,30),types=['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'],mime=types.find(t=>MediaRecorder.isTypeSupported(t))||'video/webm';let recorder:MediaRecorder;try{recorder=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:7_000_000});}catch(err){stream.getTracks().forEach(t=>t.stop());notify('3D video encoder başlatılamadı: '+String(err));return;}const chunks:BlobPart[]=[],duration=Math.max(2,Math.min(30,Number(stage.record_duration)||8))*1000,start=performance.now(),job=String(stage.job_id||'');let cancelled=false;setLiveRecordProgress(1);recorder.ondataavailable=e=>{if(!cancelled&&e.data.size)chunks.push(e.data);};recorder.onerror=()=>{if(!cancelled)notify('Canlı 3D video kaydında encoder hatası oluştu.');};const timer=setInterval(()=>setLiveRecordProgress(Math.min(99,Math.round((performance.now()-start)/duration*100))),100);const stopTimer=setTimeout(()=>{if(recorder.state!=='inactive')recorder.stop();},duration);recorder.onstop=()=>{clearInterval(timer);clearTimeout(stopTimer);stream.getTracks().forEach(t=>t.stop());if(cancelled)return;const blob=new Blob(chunks,{type:mime});if(!blob.size){setLiveRecordProgress(0);notify('Canlı 3D video çıktısı boş oluştu.');return;}if(videoUrl)URL.revokeObjectURL(videoUrl);const url=URL.createObjectURL(blob);setVideoUrl(url);setVideoBlob(blob);setLiveRecordProgress(100);void request('/api/stage/video-ready',{job_id:job,mime,bytes:blob.size}).catch(err=>notify(String(err)));};recorder.start(250);return()=>{cancelled=true;clearInterval(timer);clearTimeout(stopTimer);if(recorder.state!=='inactive')try{recorder.stop()}catch{};stream.getTracks().forEach(t=>t.stop());};},[stage.record_nonce]);
 const presets=useMemo(()=>['energy','globe','network','drone','vehicle','logo','sphere'],[]);
 return <div className={'center-stage mode-'+stage.mode}>
  {stage.mode==='core_idle'&&<><UltronCore state={state} amplitude={amplitude}/><div className="core-title">ULTRON<small>NEURAL CORE</small></div></>}
  {stage.mode==='hologram_lab'&&<><HologramStage config={stage.hologram} customModel={customModel}/><div className="stage-controls">
   <div className="stage-presets">{presets.map(k=><button key={k} className={stage.hologram.kind===k&&!customModel?'active':''} onClick={()=>{setCustomModel(null);setCustomModelName('');void patch({kind:k});}}>{k.toUpperCase()}</button>)}</div>
   <label>RENK<input type="color" value={stage.hologram.color.startsWith('#')?stage.hologram.color:'#ff3047'} onChange={e=>patch({color:e.target.value})}/></label>
   <label>BOYUT<input type="range" min=".35" max="2" step=".05" value={stage.hologram.scale} onChange={e=>patch({scale:+e.target.value})}/></label>
   <label>HIZ<input type="range" min=".05" max="4" step=".05" value={stage.hologram.speed} onChange={e=>patch({speed:+e.target.value})}/></label>
   <label>HALKA<input type="range" min="0" max="10" step="1" value={stage.hologram.rings} onChange={e=>patch({rings:+e.target.value})}/></label>
   <button onClick={()=>patch({wireframe:!stage.hologram.wireframe})}>{stage.hologram.wireframe?'SOLID':'WIREFRAME'}</button>
   <button onClick={()=>modelFile.current?.click()}>MODEL AÇ</button>
   <button onClick={downloadHologram}><Download/> KAYDET</button>
   <button onClick={()=>command('video_from_stage',{duration:6,title:stage.hologram.label})}><Video/> VİDEOYA ÇEVİR</button>
   <button onClick={()=>command('reset')}><RotateCcw/> CORE</button>
  </div></>}
  {stage.mode==='scene_lab'&&<div className={'scene-lab-shell theme-'+(stage.scene.theme||'crimson')}><SceneLab scene={stage.scene} transformMode={transformMode} amplitude={amplitude} onCommand={(op,extra={})=>{void command(op,extra);}}/><div className="scene-object-list"><b>SCENE OBJECTS <em>{stage.scene.selected_ids?.length||0}/{stage.scene.objects.length}</em></b><div className="scene-select-tools"><button onClick={()=>command('scene_multi_select',{selection_mode:'all'})}>ALL</button><button onClick={()=>command('scene_multi_select',{selection_mode:'clear'})}>CLEAR</button><button disabled={(stage.scene.selected_ids?.length||0)<2} onClick={()=>command('scene_group_create',{group_name:'GROUP '+((stage.scene.groups?.length||0)+1)})}>GROUP</button></div>{(stage.scene.groups||[]).length>0&&<div className="scene-groups">{(stage.scene.groups||[]).map(g=><button key={g.id} onClick={()=>command('scene_group_select',{group_id:g.id})}>{g.name}<small>{g.members.length}</small></button>)}</div>}{stage.scene.objects.map(o=><button key={o.id} className={(stage.scene.selected_ids?.includes(o.id)||o.id===stage.scene.selected_id)?'active':''} onClick={e=>command(e.shiftKey?'scene_multi_select':'scene_select',e.shiftKey?{object_id:o.id,selection_mode:'toggle'}:{object_id:o.id})}><span>{o.parent_id?'↳ ':''}{o.visible===false?'◌ ':o.locked?'▣ ':''}{o.label}</span><small>{o.kind.toUpperCase()}</small></button>)}</div><div className="scene-toolbar">
   <button onClick={()=>command('scene_add',{kind:'energy',label:'CORE',x:0,y:0,z:0})}>+ CORE</button><button onClick={()=>command('scene_add',{kind:'vehicle',label:'VEHICLE'})}>+ VEHICLE</button><button onClick={()=>command('scene_add',{kind:'drone',label:'DRONE'})}>+ DRONE</button><button onClick={()=>command('scene_add',{kind:'globe',label:'EARTH',color:'#35ffe4'})}>+ GLOBE</button><select defaultValue="" onChange={e=>{const kind=e.target.value;e.target.value='';if(kind)void command('scene_add',{kind,label:kind.toUpperCase()});}}><option value="">+ OBJECT</option>{['robot','arm','satellite','aircraft','building','ship','radar','portal','cube','tower','network','ring'].map(k=><option key={k} value={k}>{k.toUpperCase()}</option>)}</select><button onClick={()=>sceneModelFile.current?.click()}>IMPORT GLB</button><button onClick={()=>void refreshAssets(true)}>ASSETS</button><select defaultValue="" onChange={e=>{const preset=e.target.value;e.target.value='';if(preset)void command('scene_preset',{preset});}}><option value="">PRESET</option>{['command_center','city_scan','space_ops','robotics','operations','vehicle_scan','drone_bay','planetary'].map(k=><option key={k} value={k}>{k.replaceAll('_',' ').toUpperCase()}</option>)}</select><select defaultValue="" onChange={e=>{const preset=e.target.value;e.target.value='';if(preset)void command('scene_director',{preset,duration:10});}}><option value="">DIRECTOR</option>{['showcase','analysis','battle','presentation','launch'].map(k=><option key={k} value={k}>{k.toUpperCase()}</option>)}</select><select defaultValue="" onChange={e=>{const preset=e.target.value;e.target.value='';if(preset)void command('scene_sequence_preset',{preset});}}><option value="">MISSION SEQ</option><option value="scan_reveal">SCAN REVEAL</option><option value="target_chase">TARGET CHASE</option><option value="presentation">PRESENTATION</option><option value="launch">LAUNCH</option></select><button disabled={!(stage.scene.sequence?.steps?.length)} className={stage.scene.sequence?.playing?'active':''} onClick={()=>command(stage.scene.sequence?.playing?'scene_sequence_stop':'scene_sequence_play')}>{stage.scene.sequence?.playing?'SEQ STOP':'SEQ PLAY'}</button><button disabled={!(stage.scene.sequence?.steps?.length)} onClick={()=>command('scene_sequence_clear')}>SEQ CLEAR</button>
   <button onClick={()=>command('scene_undo')}>UNDO</button><button onClick={()=>command('scene_redo')}>REDO</button><button disabled={(stage.scene.selected_ids?.length||0)<2} onClick={()=>command('scene_align',{axis:'x',align:'center'})}>ALIGN X</button><button disabled={(stage.scene.selected_ids?.length||0)<2} onClick={()=>command('scene_align',{axis:'y',align:'center'})}>ALIGN Y</button><button disabled={(stage.scene.selected_ids?.length||0)<2} onClick={()=>command('scene_align',{axis:'z',align:'center'})}>ALIGN Z</button><button disabled={(stage.scene.selected_ids?.length||0)<3} onClick={()=>command('scene_distribute',{axis:'x'})}>DISTR X</button><button disabled={(stage.scene.selected_ids?.length||0)<3} onClick={()=>command('scene_distribute',{axis:'z'})}>DISTR Z</button><button disabled={!stage.scene.selected_id} onClick={()=>command('scene_array',{count:5,layout:'line',spacing:1.3})}>ARRAY LINE</button><button disabled={!stage.scene.selected_id} onClick={()=>command('scene_array',{count:6,layout:'radial',radius:2.8})}>ARRAY RADIAL</button><button onClick={()=>command('scene_arrange',{layout:'orbit'})}>ORBIT DÜZEN</button><button onClick={()=>command('scene_arrange',{layout:'grid'})}>GRID DÜZEN</button><button onClick={()=>command('scene_auto_link',{layout:'star',color:'#35ffe4'})}>LINK STAR</button><button onClick={()=>command('scene_auto_link',{layout:'chain',color:'#ff3047'})}>LINK CHAIN</button><button onClick={()=>command('scene_clear_links')}>LINK CLEAR</button><button disabled={!(stage.scene.measurements?.length)} onClick={()=>command('scene_measure_clear')}>MEASURE CLEAR</button>
   <button onClick={()=>command('scene_camera',{camera:'isometric'})}>ISO CAM</button><button onClick={()=>command('scene_camera',{camera:'top'})}>TOP CAM</button><button onClick={()=>command('scene_camera_bookmark_save',{bookmark_name:'CAM '+((stage.scene.camera_bookmarks?.length||0)+1)})}>SAVE CAM</button>{(stage.scene.camera_bookmarks||[]).map(b=><button key={b.id} onClick={()=>command('scene_camera_bookmark_load',{bookmark_id:b.id})}>{b.name}</button>)}<button onClick={()=>command('scene_cinematic',{cinematic:'orbit',duration:10,loop:true})}>CINEMATIC</button><button onClick={()=>command('scene_cinematic',{cinematic:'off'})}>CAM STOP</button>
   <button onClick={()=>command('scene_animation',{animation:stage.scene.explode?'assemble':'explode'})}>{stage.scene.explode?'BİRLEŞTİR':'PATLAT'}</button><button onClick={()=>command('scene_animation',{animation:stage.scene.animation==='scan'?'idle':'scan'})}>SCAN</button>
   <button onClick={()=>command('scene_theme',{theme:stage.scene.theme||'crimson',grid:!stage.scene.grid})}>{stage.scene.grid?'GRID OFF':'GRID ON'}</button><button onClick={()=>command('scene_theme',{theme:stage.scene.theme||'crimson',show_labels:stage.scene.show_labels===false})}>{stage.scene.show_labels===false?'LABEL ON':'LABEL OFF'}</button><button onClick={()=>command('scene_theme',{theme:stage.scene.theme||'crimson',show_trails:stage.scene.show_trails===false})}>{stage.scene.show_trails===false?'TRAIL ON':'TRAIL OFF'}</button><button onClick={()=>command('scene_theme',{theme:stage.scene.theme||'crimson',audio_reactive:stage.scene.audio_reactive===false})}>{stage.scene.audio_reactive===false?'AUDIO FX ON':'AUDIO FX OFF'}</button>
   <select value={stage.scene.theme||'crimson'} onChange={e=>command('scene_theme',{theme:e.target.value})}><option value="crimson">CRIMSON</option><option value="cyan">CYAN</option><option value="purple">PURPLE</option><option value="amber">AMBER</option><option value="mono">MONO</option></select><select value={stage.scene.render_mode||'hologram'} onChange={e=>command('scene_render_mode',{render_mode:e.target.value})}><option value="hologram">HOLOGRAM</option><option value="blueprint">BLUEPRINT</option><option value="xray">X-RAY</option><option value="solid">SOLID</option><option value="thermal">THERMAL</option></select>{stage.scene.target_id&&<button className="active" onClick={()=>command('scene_target_clear')}>TARGET CLEAR</button>}
   <button className={stage.scene.collision_overlay?'active':''} onClick={()=>command('scene_collision_overlay',{enabled:!stage.scene.collision_overlay})}>{stage.scene.collision_overlay?'COLLISION OFF':'COLLISION ON'}</button><button onClick={()=>void runDiagnostics()}>DIAGNOSTICS</button><button onClick={captureScene}>PNG</button><button onClick={()=>window.dispatchEvent(new Event('ultron-scene-export-glb'))}>EXPORT GLB</button><button onClick={downloadScene}><Download/> SAVE FILE</button><button onClick={()=>sceneFile.current?.click()}>OPEN FILE</button><button onClick={()=>void refreshProjects(true)}>PROJECTS</button><button onClick={()=>void saveSnapshot()}>SNAP SAVE</button><button onClick={()=>void refreshSnapshots(true)}>SNAPSHOTS</button><button onClick={()=>command('scene_record',{duration:8,title:'ULTRON SCENE'})}><Video/> LIVE VIDEO</button><button onClick={()=>command('reset')}><RotateCcw/> CORE</button>
  </div>{showProjects&&<div className="scene-projects"><header><b>SCENE PROJECTS</b><button onClick={()=>setShowProjects(false)}>×</button></header><div className="scene-project-save"><input value={projectName} maxLength={80} onChange={e=>setProjectName(e.target.value)} placeholder="Proje adı"/><button onClick={()=>void saveProject()}>SAVE PROJECT</button></div><div className="scene-project-list">{projects.length?projects.map(p=><article key={p.id}><div><b>{p.name}</b><small>{new Date(p.updated_at*1000).toLocaleString('tr-TR')}</small></div><button onClick={()=>void loadProject(p.id)}>OPEN</button><button onClick={()=>void deleteProject(p.id)}>DELETE</button></article>):<p>Kayıtlı proje yok.</p>}</div></div>}{showSnapshots&&<div className="scene-snapshots"><header><b>SNAPSHOT VAULT</b><button onClick={()=>setShowSnapshots(false)}>×</button></header><div className="scene-snapshot-actions"><button onClick={()=>void saveSnapshot()}>SAVE CURRENT STATE</button></div><div className="scene-snapshot-list">{snapshots.length?snapshots.map(s=><article key={s.id}><div><b>{s.name}</b><small>{new Date(s.created_at*1000).toLocaleString('tr-TR')}</small></div><button onClick={()=>void restoreSnapshot(s.id)}>RESTORE</button><button onClick={()=>void deleteSnapshot(s.id)}>DELETE</button></article>):<p>Kayıtlı snapshot yok.</p>}</div></div>}{showAssets&&<div className="scene-assets"><header><b>ASSET LIBRARY</b><button onClick={()=>setShowAssets(false)}>×</button></header><div className="scene-asset-list">{assets.length?assets.map(a=><article key={a.id}><div><b>{a.name}</b><small>{(a.bytes/1024/1024).toFixed(1)} MB</small></div><button onClick={()=>void addAsset(a)}>ADD</button><button onClick={()=>void deleteAsset(a.id)}>DELETE</button></article>):<p>İçe aktarılmış GLB yok.</p>}</div></div>}{showDiagnostics&&diagnostics&&<div className="scene-diagnostics"><header><b>SCENE DIAGNOSTICS</b><button onClick={()=>setShowDiagnostics(false)}>×</button></header><div className="diag-grid"><span>STATUS<b>{String(diagnostics.health||'unknown').toUpperCase()}</b></span><span>OBJECTS<b>{diagnostics.objects??0}</b></span><span>GROUPS<b>{diagnostics.groups??0}</b></span><span>LINKS<b>{diagnostics.links??0}</b></span><span>KEYS<b>{diagnostics.object_keyframes??0}</b></span><span>CAM KEYS<b>{diagnostics.camera_keyframes??0}</b></span><span>ISSUES<b>{diagnostics.issues?.length??0}</b></span><span>COLLISIONS<b>{diagnostics.collisions?.length??0}</b></span></div>{(diagnostics.issues?.length||0)>0&&<div className="diag-list"><b>ISSUES</b>{diagnostics.issues.slice(0,8).map((x:any,i:number)=><p key={'i'+i}>{String(x.type||'issue')} {x.object?'· '+x.object:''}</p>)}</div>}{(diagnostics.collisions?.length||0)>0&&<div className="diag-list danger"><b>POTENTIAL COLLISIONS</b>{diagnostics.collisions.slice(0,8).map((x:any,i:number)=><p key={'c'+i}>{x.a_label} ↔ {x.b_label} · {Number(x.distance).toFixed(2)}</p>)}</div>}</div>}<SceneSequenceStatus scene={stage.scene}/>{(stage.scene.selected_ids?.length||0)>1&&<div className="scene-multi-inspector"><header><b>MULTI SELECT</b><span>{stage.scene.selected_ids?.length} OBJECTS</span></header><div><button onClick={()=>command('scene_batch_transform',{dx:-.5})}>←</button><button onClick={()=>command('scene_batch_transform',{dx:.5})}>→</button><button onClick={()=>command('scene_batch_transform',{dy:.5})}>↑</button><button onClick={()=>command('scene_batch_transform',{dy:-.5})}>↓</button></div><div><button onClick={()=>command('scene_batch_transform',{scale_factor:.9})}>- SCALE</button><button onClick={()=>command('scene_batch_transform',{scale_factor:1.1})}>+ SCALE</button><button onClick={()=>command('scene_batch_transform',{dry:.2618})}>ROTATE 15°</button></div><div><button onClick={()=>command('scene_align',{axis:'x',align:'center'})}>ALIGN X</button><button onClick={()=>command('scene_align',{axis:'y',align:'center'})}>ALIGN Y</button><button onClick={()=>command('scene_align',{axis:'z',align:'center'})}>ALIGN Z</button></div><button onClick={()=>command('scene_group_create',{group_name:'GROUP '+((stage.scene.groups?.length||0)+1)})}>CREATE GROUP</button>{stage.scene.selected_ids?.length===2&&<button onClick={()=>command('scene_measure')}>MEASURE</button>}</div>}{(()=>{const o=stage.scene.objects.find(x=>x.id===stage.scene.selected_id);if(!o)return null;const targetId=o.constraint?.target_id||stage.scene.target_id||stage.scene.objects.find(x=>x.id!==o.id)?.id||'';return <div className="scene-inspector"><input className="scene-name" key={o.id+'-'+o.label} defaultValue={o.label} onBlur={e=>{const value=e.target.value.trim();if(value&&value!==o.label)void command('scene_update',{object_id:o.id,label:value});}}/><span>{o.id} · {o.kind.toUpperCase()}</span><div className="gizmo-modes"><button className={transformMode==='translate'?'active':''} onClick={()=>setTransformMode('translate')}>TAŞI [W]</button><button className={transformMode==='rotate'?'active':''} onClick={()=>setTransformMode('rotate')}>DÖNDÜR [E]</button><button className={transformMode==='scale'?'active':''} onClick={()=>setTransformMode('scale')}>ÖLÇEK [R]</button></div><label>PARENT<select value={o.parent_id||''} onChange={e=>{const parent=e.target.value;void command(parent?'scene_parent':'scene_unparent',parent?{object_id:o.id,parent_id:parent}:{object_id:o.id});}}><option value="">ROOT</option>{stage.scene.objects.filter(x=>x.id!==o.id).map(x=><option key={x.id} value={x.id}>{x.label}</option>)}</select></label><div><button onClick={()=>command('scene_update',{object_id:o.id,x:(o.position?.[0]||0)-.5})}>←</button><button onClick={()=>command('scene_update',{object_id:o.id,x:(o.position?.[0]||0)+.5})}>→</button><button onClick={()=>command('scene_update',{object_id:o.id,y:(o.position?.[1]||0)+.5})}>↑</button><button onClick={()=>command('scene_update',{object_id:o.id,y:(o.position?.[1]||0)-.5})}>↓</button></div><label>RENK<input type="color" value={o.color?.startsWith('#')?o.color:'#ff3047'} onChange={e=>command('scene_update',{object_id:o.id,color:e.target.value})}/></label><label>BOYUT<input type="range" min=".2" max="3" step=".1" value={o.scale} onChange={e=>command('scene_update',{object_id:o.id,scale:+e.target.value})}/></label><label>OPACITY<input type="range" min=".08" max="1" step=".02" value={o.opacity||.9} onChange={e=>command('scene_update',{object_id:o.id,opacity:+e.target.value})}/></label><label>SPIN<input type="range" min="-4" max="4" step=".1" value={o.spin||0} onChange={e=>command('scene_update',{object_id:o.id,spin:+e.target.value})}/></label><label>PATLAT<input type="range" min="0" max="2" step=".1" value={o.explode||0} onChange={e=>command('scene_update',{object_id:o.id,explode:+e.target.value})}/></label>
   <div className="scene-inspector-actions"><button onClick={()=>command('scene_duplicate',{object_id:o.id})}>DUPLICATE</button><button className={stage.scene.focus_id===o.id?'active':''} onClick={()=>command('scene_focus',{object_id:stage.scene.focus_id===o.id?'':o.id})}>{stage.scene.focus_id===o.id?'UNFOCUS':'FOCUS'}</button><button onClick={()=>command('scene_update',{object_id:o.id,visible:o.visible===false})}>{o.visible===false?'SHOW':'HIDE'}</button><button onClick={()=>command('scene_update',{object_id:o.id,locked:!o.locked})}>{o.locked?'UNLOCK':'LOCK'}</button><button onClick={()=>command('scene_update',{object_id:o.id,wireframe:!o.wireframe})}>{o.wireframe?'SOLID':'WIRE'}</button><button onClick={()=>command('scene_unlink',{object_id:o.id})}>UNLINK</button><button onClick={()=>command('scene_remove',{object_id:o.id})}>DELETE</button></div>
   <div className="scene-hud-editor"><b>HUD DATA</b><button onClick={()=>command('scene_hud_add',{object_id:o.id,hud_title:'STATUS',hud_value:'ONLINE',color:o.color||'#35ffe4'})}>+ HUD</button>{(stage.scene.hud||[]).filter(h=>h.object_id===o.id).map(h=><div key={h.id}><span>{h.title}: {h.value}{h.unit?' '+h.unit:''}</span><button onClick={()=>command('scene_hud_remove',{hud_id:h.id})}>×</button></div>)}</div>
   {o.kind==='custom'&&<div className="scene-custom-anim"><label>MODEL ANIM HIZ<input type="range" min="0" max="4" step=".1" value={o.clip_speed??1} onChange={e=>command('scene_update',{object_id:o.id,clip_speed:+e.target.value})}/></label><button onClick={()=>command('scene_update',{object_id:o.id,clip_paused:!o.clip_paused})}>{o.clip_paused?'MODEL ANIM PLAY':'MODEL ANIM PAUSE'}</button></div>}
   <div className="scene-motion"><button className={o.motion?.type==='orbit'?'active':''} onClick={()=>command('scene_motion',{object_id:o.id,motion:'orbit',motion_speed:1,radius:1.5})}>ORBIT</button><button className={o.motion?.type==='bob'?'active':''} onClick={()=>command('scene_motion',{object_id:o.id,motion:'bob',motion_speed:1,amplitude:.55})}>BOB</button><button className={o.motion?.type==='patrol'?'active':''} onClick={()=>command('scene_motion',{object_id:o.id,motion:'patrol',motion_speed:1,amplitude:1.4})}>PATROL</button><button className={o.motion?.type==='pulse'?'active':''} onClick={()=>command('scene_motion',{object_id:o.id,motion:'pulse',motion_speed:1,amplitude:.8})}>PULSE</button><button onClick={()=>command('scene_motion',{object_id:o.id,motion:'none'})}>STOP</button></div>
   <div className="scene-physics"><b>PHYSICS</b><button className={o.physics?.mode==='drop'?'active':''} onClick={()=>command('scene_physics',{object_id:o.id,physics_mode:'drop',gravity:9.81,bounce:.45})}>DROP</button><button className={o.physics?.mode==='launch'?'active':''} onClick={()=>command('scene_physics',{object_id:o.id,physics_mode:'launch',vy:5,vx:1.2,gravity:9.81,bounce:.35})}>LAUNCH</button><button className={o.physics?.mode==='zero_g'?'active':''} onClick={()=>command('scene_physics',{object_id:o.id,physics_mode:'zero_g',vx:.15,vy:.08,vz:.1,gravity:0})}>ZERO-G</button><button className={o.physics?.mode==='float'?'active':''} onClick={()=>command('scene_physics',{object_id:o.id,physics_mode:'float',gravity:0})}>FLOAT</button><button onClick={()=>command('scene_physics',{object_id:o.id,physics_mode:'off'})}>OFF</button></div>
   <div className="scene-v5-target"><b>TARGET / CONSTRAINT</b><select value={o.constraint?.target_id||''} onChange={e=>{const id=e.target.value;void command('scene_constraint',id?{object_id:o.id,constraint:o.constraint?.type&&o.constraint.type!=='none'?o.constraint.type:'look_at',target_id:id}:{object_id:o.id,constraint:'none'});}}><option value="">NO TARGET</option>{stage.scene.objects.filter(x=>x.id!==o.id).map(x=><option key={x.id} value={x.id}>{x.label}</option>)}</select><div><button disabled={!targetId} className={o.constraint?.type==='follow'?'active':''} onClick={()=>command('scene_constraint',{object_id:o.id,constraint:'follow',target_id:targetId,distance:2,constraint_speed:1})}>FOLLOW</button><button disabled={!targetId} className={o.constraint?.type==='look_at'?'active':''} onClick={()=>command('scene_constraint',{object_id:o.id,constraint:'look_at',target_id:targetId})}>LOOK AT</button><button disabled={!targetId} className={o.constraint?.type==='orbit_target'?'active':''} onClick={()=>command('scene_constraint',{object_id:o.id,constraint:'orbit_target',target_id:targetId,distance:2.5,constraint_speed:1})}>ORBIT TARGET</button><button onClick={()=>command('scene_constraint',{object_id:o.id,constraint:'none'})}>STOP</button></div><button className={stage.scene.target_id===o.id?'active':''} onClick={()=>command(stage.scene.target_id===o.id?'scene_target_clear':'scene_target_lock',{object_id:o.id})}>{stage.scene.target_id===o.id?'UNLOCK TARGET':'TARGET LOCK THIS'}</button></div>
   <div className="scene-v5-path"><b>WAYPOINT PATH <span>{o.path?.points?.length||0}</span></b><div><button onClick={()=>command('scene_waypoint_add',{object_id:o.id,x:o.position?.[0]||0,y:o.position?.[1]||0,z:o.position?.[2]||0})}>+ WAYPOINT</button><button disabled={(o.path?.points?.length||0)<2} className={o.path?.started_at?'active':''} onClick={()=>command('scene_path_play',{object_id:o.id,path_speed:o.path?.speed||1,loop:true})}>PLAY PATH</button><button disabled={!o.path?.started_at} onClick={()=>command('scene_path_stop',{object_id:o.id})}>STOP</button><button disabled={!(o.path?.points?.length)} onClick={()=>command('scene_waypoint_clear',{object_id:o.id})}>CLEAR</button></div></div>
  </div>})()}{liveRecordProgress>0&&liveRecordProgress<100&&<div className="scene-recording"><i/><b>LIVE 3D RECORDING</b><span>%{liveRecordProgress}</span></div>}<SceneTimeline scene={stage.scene} onCommand={(op,extra={})=>{void command(op,extra);}}/></div>}
  {stage.mode==='video_rendering'&&<div className="stage-video-render"><VideoRenderer stage={stage} onReady={(url,blob)=>{if(videoUrl)URL.revokeObjectURL(videoUrl);setVideoUrl(url);setVideoBlob(blob);setRenderProgress(100);}} onError={setRenderError} onProgress={setRenderProgress}/><div className="render-overlay"><Sparkles/><h2>ULTRON VIDEO RENDER</h2><p>{stage.video.template.replaceAll('_',' ').toUpperCase()} · {stage.video.duration}s</p><div className="stage-progress"><i style={{width:renderProgress+'%'}}/></div><b className="render-percent">%{renderProgress}</b><small>{renderError||'Frame üretimi ve WebM kodlama devam ediyor…'}</small></div></div>}
  {stage.mode==='video_preview'&&<div className="stage-video-preview">{videoUrl?<video ref={video} src={videoUrl} autoPlay loop controls playsInline/>:<div className="stage-missing-video"><Video/><h2>VIDEO OTURUMU HAZIR</h2><p>Bu render başka bir UI oturumunda üretildi. Yeniden üretmek için Render düğmesini kullan.</p></div>}<div className="video-actions"><button onClick={()=>{const v=video.current;if(!v)return;v.paused?v.play():v.pause();}}><Play/> OYNAT / DURAKLAT</button><button disabled={!videoBlob} onClick={downloadVideo}><Download/> KAYDET</button><button onClick={()=>command('video_create',{template:stage.video.template,duration:stage.video.duration,title:stage.video.title})}><RotateCcw/> YENİDEN RENDER</button><button onClick={()=>command('reset')}><Maximize2/> CORE</button></div></div>}
  {stage.mode==='task_progress'&&<div className="stage-task"><div className="task-orb"/><h2>{stage.title}</h2><p>{stage.subtitle}</p><div className="stage-progress"><i style={{width:Math.max(0,Math.min(100,stage.progress))+'%'}}/></div><b>%{Math.round(stage.progress)}</b></div>}
  {stage.mode==='screen_preview'&&<div className="stage-task"><ScanFrame/><h2>SCREEN PREVIEW</h2><p>Vizyon önizlemesi için Ekran Yakalama aracını kullan.</p><button onClick={()=>command('reset')}>CORE'A DÖN</button></div>}
  {stage.mode!=='core_idle'&&<div className="stage-mode-tag"><span>{stage.title}</span><small>{customModelName?customModelName+' / '+stage.subtitle:stage.subtitle}</small></div>}
  <input ref={sceneModelFile} hidden type="file" accept=".glb,model/gltf-binary" onChange={async e=>{const file=e.target.files?.[0];e.target.value='';if(!file)return;if(!/\.glb$/i.test(file.name)){notify('Scene Lab için GLB dosyası seç.');return;}if(file.size>50*1024*1024){notify('GLB modeli en fazla 50 MB olabilir.');return;}try{const upload=await fetch('/api/stage/model',{method:'POST',headers:{'Content-Type':'model/gltf-binary','X-Model-Name':encodeURIComponent(file.name)},body:file}),data=await upload.json();if(!upload.ok||!data.ok)throw Error(data.error||'upload_failed');await request('/api/stage/command',{operation:'scene_add',kind:'custom',model_id:data.model_id,label:file.name.replace(/\.glb$/i,''),color:'#ff3047',wireframe:true});await refreshAssets(false);}catch(err){notify('GLB Scene Lab’e eklenemedi: '+String(err));}}}/>
  <input ref={sceneFile} hidden type="file" accept=".json,.ultron-scene.json,application/json" onChange={async e=>{const file=e.target.files?.[0];e.target.value='';if(!file)return;try{const data=JSON.parse(await file.text()),scene=data?.scene;if(!scene||!Array.isArray(scene.objects))throw Error('Geçersiz sahne dosyası');await command('scene_load',{scene_json:JSON.stringify(scene)});}catch(err){notify('Sahne açılamadı: '+String(err));}}}/>
  <input ref={modelFile} hidden type="file" accept=".glb,model/gltf-binary" onChange={async e=>{const file=e.target.files?.[0];e.target.value='';if(!file)return;if(!/\.glb$/i.test(file.name)){notify('Center Stage için GLB dosyası seç.');return;}if(file.size>50*1024*1024){notify('GLB modeli en fazla 50 MB olabilir.');return;}try{setCustomModel(await file.arrayBuffer());setCustomModelName(file.name);if(stage.mode!=='hologram_lab')await command('hologram_create',{kind:stage.hologram.kind||'energy',label:file.name.replace(/\.glb$/i,'')});}catch(err){notify('3D model açılamadı: '+String(err));}}}/>
 </div>;
}

function ScanFrame(){return <div className="scan-frame"><i/><i/><i/><i/></div>;}
