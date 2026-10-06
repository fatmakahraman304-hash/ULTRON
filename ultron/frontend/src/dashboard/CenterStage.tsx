import {useEffect,useMemo,useRef,useState} from 'react';
import * as THREE from 'three';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {TransformControls} from 'three/examples/jsm/controls/TransformControls.js';
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
function lerp(a:number,b:number,t:number){return a+(b-a)*t;}
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
 const span=Math.max(.0001,b.time-a.time),t=(time-a.time)/span;
 return {position:[0,1,2].map(i=>lerp(a.position?.[i]||0,b.position?.[i]||0,t)),rotation:[0,1,2].map(i=>lerp(a.rotation?.[i]||0,b.rotation?.[i]||0,t)),scale:lerp(a.scale||1,b.scale||1,t)};
}
function makeLabelSprite(text:string,color:string){
 const canvas=document.createElement('canvas');canvas.width=320;canvas.height=72;const ctx=canvas.getContext('2d')!;
 ctx.clearRect(0,0,320,72);ctx.fillStyle='rgba(2,4,7,.78)';ctx.fillRect(2,2,316,68);ctx.strokeStyle=color;ctx.lineWidth=2;ctx.strokeRect(2,2,316,68);
 ctx.font='600 26px Consolas,monospace';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle='#f5f7fa';ctx.fillText(text.slice(0,26),160,36);
 const tex=new THREE.CanvasTexture(canvas);tex.colorSpace=THREE.SRGBColorSpace;const mat=new THREE.SpriteMaterial({map:tex,transparent:true,depthTest:false});const sprite=new THREE.Sprite(mat);sprite.scale.set(1.9,.43,1);sprite.position.set(0,1.65,0);sprite.userData.labelTexture=tex;return sprite;
}

function SceneLab({scene,transformMode,onCommand}:{scene:SceneState;transformMode:'translate'|'rotate'|'scale';onCommand:(operation:string,extra?:Record<string,unknown>)=>void}){
 const host=useRef<HTMLDivElement>(null);
 const key=JSON.stringify(scene);
 useEffect(()=>{
  const el=host.current;if(!el)return;
  const accent=sceneAccent(scene.theme),accentColor=colorOf(accent);
  const world=new THREE.Scene();world.fog=new THREE.FogExp2(0x020407,.038);
  const camera=new THREE.PerspectiveCamera(42,1,.1,100);
  const cam=scene.camera||'isometric';
  if(cam==='front')camera.position.set(0,1.2,9);
  else if(cam==='top')camera.position.set(0,9,.01);
  else if(cam==='side')camera.position.set(9,1.2,0);
  else if(cam==='close')camera.position.set(0,.8,5.2);
  else camera.position.set(6,4.2,7.2);
  camera.lookAt(0,0,0);
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'high-performance'});
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setClearColor(0x000000,0);el.appendChild(renderer.domElement);
  const orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;orbit.dampingFactor=.07;orbit.enablePan=true;orbit.minDistance=3.5;orbit.maxDistance=18;orbit.autoRotate=scene.auto_orbit||scene.camera==='orbit';orbit.autoRotateSpeed=.55;
  const sceneRoot=new THREE.Group();world.add(sceneRoot);
  if(scene.grid){
   const grid=new THREE.GridHelper(14,28,accentColor.getHex(),colorOf(accent).multiplyScalar(.22).getHex());grid.position.y=-1.55;sceneRoot.add(grid);
  }
  const matFor=(o:SceneObject)=>new THREE.MeshBasicMaterial({color:colorOf(o.color),wireframe:o.wireframe,transparent:true,opacity:o.opacity});
  const addPart=(group:THREE.Group,geo:THREE.BufferGeometry,mat:THREE.Material,pos:[number,number,number],dir:[number,number,number]=pos)=>{
   const m=new THREE.Mesh(geo,mat);m.position.set(...pos);m.userData.base=[...pos];m.userData.dir=[...dir];group.add(m);return m;
  };
  const objectGroups=new Map<string,THREE.Group>();
  for(const o of scene.objects||[]){
   if(o.visible===false)continue;
   const group=new THREE.Group();group.userData.objectId=o.id;group.userData.basePosition=[...(o.position||[0,0,0])];group.userData.baseRotation=[...(o.rotation||[0,0,0])];group.userData.baseScale=o.scale||1;group.position.set(o.position?.[0]||0,o.position?.[1]||0,o.position?.[2]||0);group.rotation.set(o.rotation?.[0]||0,o.rotation?.[1]||0,o.rotation?.[2]||0);group.scale.setScalar(o.scale||1);
   const mat=matFor(o),dim=new THREE.MeshBasicMaterial({color:colorOf(o.color),wireframe:true,transparent:true,opacity:Math.max(.18,o.opacity*.38)});
   const kind=o.kind||'energy';
   if(kind==='vehicle'){
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
   }else{
    addPart(group,new THREE.IcosahedronGeometry(kind==='sphere'?1.05:.9,kind==='sphere'?2:1),kind==='sphere'?dim:mat,[0,0,0],[0,0,0]);
    for(let i=0;i<3;i++){const r=addPart(group,new THREE.TorusGeometry(1.12+i*.16,.012,7,80),mat,[0,0,0],[0,0,0]);r.rotation.set(i*.55,i*.7,i);}
   }
   if(scene.show_labels!==false){const label=makeLabelSprite(o.label||o.kind,o.color||accent);label.userData.objectId=o.id;group.add(label);}
   group.traverse(ch=>{ch.userData.objectId=o.id;});
   if(o.id===scene.selected_id){const helper=new THREE.BoxHelper(group,colorOf('#ffffff'));helper.userData.selection=true;group.add(helper);}
   sceneRoot.add(group);objectGroups.set(o.id,group);
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
  let dead=false,raf=0,last=performance.now();
  const resize=()=>{const w=Math.max(1,el.clientWidth),h=Math.max(1,el.clientHeight);renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();};resize();const ro=new ResizeObserver(resize);ro.observe(el);
  const ray=new THREE.Raycaster(),mouse=new THREE.Vector2();
  const click=(e:PointerEvent)=>{const r=renderer.domElement.getBoundingClientRect();mouse.x=((e.clientX-r.left)/r.width)*2-1;mouse.y=-((e.clientY-r.top)/r.height)*2+1;ray.setFromCamera(mouse,camera);const hits=ray.intersectObjects([...objectGroups.values()],true);const hit=hits.find(h=>!h.object.userData.selection);if(hit){let obj:THREE.Object3D|null=hit.object;while(obj&&!obj.userData.objectId)obj=obj.parent;const id=obj?.userData.objectId;if(id)onCommand('scene_select',{object_id:id});}};
  renderer.domElement.addEventListener('pointerdown',click);
  const loop=(now:number)=>{if(dead)return;const dt=Math.min(.05,(now-last)/1000);last=now;const seconds=now/1000,tlTime=timelineCursor(scene,Date.now()/1000);
   for(const o of scene.objects||[]){const g=objectGroups.get(o.id);if(!g)continue;const sampled=sampleSceneObject(scene,o,tlTime),motion=o.motion||{type:'none',speed:1,radius:1.5,amplitude:.5,axis:'y'};let px=sampled.position[0]||0,py=sampled.position[1]||0,pz=sampled.position[2]||0;const ms=Number(motion.speed)||1,amp=Number(motion.amplitude)||.5,rad=Number(motion.radius)||1.5;
    if(motion.type==='orbit'){px+=Math.cos(seconds*ms)*rad;pz+=Math.sin(seconds*ms)*rad;}
    else if(motion.type==='bob'){py+=Math.sin(seconds*ms*2)*amp;}
    else if(motion.type==='patrol'){px+=Math.sin(seconds*ms)*amp*2;}
    g.position.set(px,py,pz);g.rotation.set(sampled.rotation[0]||0,(sampled.rotation[1]||0)+seconds*(o.spin||0),sampled.rotation[2]||0);const pulse=motion.type==='pulse'?1+Math.sin(seconds*ms*3)*Math.min(.35,amp*.18):1;g.scale.setScalar((sampled.scale||1)*pulse);
    const ex=Math.max(0,Number(scene.explode||0)+Number(o.explode||0));g.traverse(ch=>{if(!(ch instanceof THREE.Mesh)||!ch.userData.base)return;const b=ch.userData.base as number[],d=ch.userData.dir as number[];ch.position.set(b[0]+d[0]*ex*.35,b[1]+d[1]*ex*.35,b[2]+d[2]*ex*.35);});
   }
   const cin=scene.cinematic;if(cin?.enabled&&cin.started_at){const d=Math.max(2,Number(cin.duration)||8),elapsed=Math.max(0,Date.now()/1000-Number(cin.started_at)),p=(cin.loop?elapsed%d:Math.min(d,elapsed))/d,a=p*Math.PI*2;
    if(cin.preset==='flyby')camera.position.set(lerp(-8,8,p),2.2,5.5);
    else if(cin.preset==='topdown')camera.position.set(Math.sin(a)*2,8.5,Math.cos(a)*2);
    else if(cin.preset==='hero')camera.position.set(Math.sin(a*.5)*2.2,1.2+Math.sin(a)*.6,4.4+Math.cos(a)*.7);
    else if(cin.preset==='spiral'){const r=8-4*p;camera.position.set(Math.cos(a*2)*r,2+4*p,Math.sin(a*2)*r);}
    else camera.position.set(Math.cos(a)*7,3.4,Math.sin(a)*7);camera.lookAt(0,0,0);orbit.target.set(0,0,0);
   }
   if(scan.visible)scan.position.y=-1.3+((now*.001)%1)*2.6;orbit.update();renderer.render(world,camera);raf=requestAnimationFrame(loop);};raf=requestAnimationFrame(loop);
  return()=>{dead=true;cancelAnimationFrame(raf);ro.disconnect();renderer.domElement.removeEventListener('pointerdown',click);transform.detach();transform.dispose();orbit.dispose();renderer.dispose();world.traverse(o=>{const m=o as THREE.Mesh;if(m.geometry)m.geometry.dispose();const tex=(o as any).userData?.labelTexture;if(tex)tex.dispose();const mm=(m as any).material;if(mm)(Array.isArray(mm)?mm:[mm]).forEach((x:THREE.Material)=>x.dispose());});renderer.domElement.remove();};
 },[key,transformMode]);
 return <div className="scene-lab-webgl" ref={host}/>;
}

function drawVideoFrame(ctx:CanvasRenderingContext2D,w:number,h:number,p:number,stage:StageState){
 const video=stage.video,color=colorOf(stage.hologram.color),theme='#'+color.getHexString(),title=video.title||'ULTRON',template=video.template||'ultron_intro';
 ctx.fillStyle='#020407';ctx.fillRect(0,0,w,h);
 const g=ctx.createRadialGradient(w*.5,h*.48,10,w*.5,h*.48,w*.48);g.addColorStop(0,theme+'55');g.addColorStop(.45,theme+'13');g.addColorStop(1,'#00000000');ctx.fillStyle=g;ctx.fillRect(0,0,w,h);
 ctx.save();ctx.translate(w/2,h/2);ctx.strokeStyle=theme;ctx.shadowColor=theme;ctx.shadowBlur=16;ctx.globalAlpha=.9;
 const spin=p*Math.PI*2*(template==='energy_core'?2.2:1);
 if(template==='hologram_capture'&&stage.video.source_scene){
  const objs=stage.scene.objects||[];ctx.save();ctx.rotate(spin*.08);
  for(const [i,o] of objs.entries()){const x=(o.position?.[0]||0)*70,y=-(o.position?.[2]||0)*42+(o.position?.[1]||0)*55,s=36*(o.scale||1);ctx.save();ctx.translate(x,y);ctx.rotate(spin*(o.spin||.3)*.15+i*.2);ctx.strokeStyle=o.color||theme;ctx.globalAlpha=o.opacity||.85;ctx.strokeRect(-s,-s*.6,s*2,s*1.2);ctx.beginPath();ctx.arc(0,0,s*.65,0,Math.PI*2);ctx.stroke();ctx.font='12px Consolas';ctx.fillStyle=o.color||theme;ctx.textAlign='center';ctx.fillText(o.label||o.kind,0,s*.95);ctx.restore();}
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

export default function CenterStage({stage,state,amplitude,notify}:Props){
 const [videoUrl,setVideoUrl]=useState(''),[videoBlob,setVideoBlob]=useState<Blob|null>(null),[renderError,setRenderError]=useState(''),[renderProgress,setRenderProgress]=useState(0),[customModel,setCustomModel]=useState<ArrayBuffer|null>(null),[customModelName,setCustomModelName]=useState(''),[transformMode,setTransformMode]=useState<'translate'|'rotate'|'scale'>('translate');
 const video=useRef<HTMLVideoElement>(null),modelFile=useRef<HTMLInputElement>(null),sceneFile=useRef<HTMLInputElement>(null),lastSaveNonce=useRef(Number(stage.save_nonce||0)),lastHologramKind=useRef(stage.hologram.kind);
 useEffect(()=>()=>{if(videoUrl)URL.revokeObjectURL(videoUrl);},[videoUrl]);
 useEffect(()=>{if(stage.mode==='video_rendering'){setRenderError('');setRenderProgress(0);}},[stage.job_id,stage.mode]);
 useEffect(()=>{if(lastHologramKind.current!==stage.hologram.kind){lastHologramKind.current=stage.hologram.kind;if(customModel){setCustomModel(null);setCustomModelName('');}}},[stage.hologram.kind]);
 useEffect(()=>{if(video.current)stage.video_paused?video.current.pause():video.current.play().catch(()=>{});},[stage.video_paused,stage.revision]);
 const patch=(body:Record<string,unknown>)=>request('/api/stage/control',body).catch(e=>notify(String(e)));
 const command=(operation:string,extra:Record<string,unknown>={})=>request('/api/stage/command',{operation,...extra}).catch(e=>notify(String(e)));
 const downloadVideo=()=>{if(!videoBlob||!videoUrl){notify('Bu oturumda video verisi yok. Videoyu yeniden render et.');return;}const a=document.createElement('a');a.href=videoUrl;a.download='ultron-'+(stage.video.template||'animation')+'.webm';a.click();};
 const downloadHologram=()=>{const payload={version:1,type:'ultron-center-stage',saved_at:new Date().toISOString(),hologram:stage.hologram,custom_model:customModelName||null};const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='ultron-hologram.ultron.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);};
 const downloadScene=()=>{const payload={version:2,type:'ultron-scene',saved_at:new Date().toISOString(),scene:stage.scene};const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='ultron-scene.ultron-scene.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);};
 useEffect(()=>{const nonce=Number(stage.save_nonce||0);if(!nonce||nonce===lastSaveNonce.current)return;lastSaveNonce.current=nonce;if(stage.save_kind==='video')downloadVideo();else if(stage.save_kind==='hologram')downloadHologram();else if(stage.save_kind==='scene')downloadScene();},[stage.save_nonce,stage.save_kind,videoBlob,videoUrl,stage.hologram,stage.video.template]);
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
  {stage.mode==='scene_lab'&&<div className="scene-lab-shell"><SceneLab scene={stage.scene} transformMode={transformMode} onCommand={(op,extra={})=>{void command(op,extra);}}/><div className="scene-object-list"><b>SCENE OBJECTS</b>{stage.scene.objects.map(o=><button key={o.id} className={o.id===stage.scene.selected_id?'active':''} onClick={()=>command('scene_select',{object_id:o.id})}><span>{o.label}</span><small>{o.kind.toUpperCase()}</small></button>)}</div><div className="scene-toolbar">
   <button onClick={()=>command('scene_add',{kind:'energy',label:'CORE',x:0,y:0,z:0})}>+ CORE</button><button onClick={()=>command('scene_add',{kind:'vehicle',label:'VEHICLE'})}>+ VEHICLE</button><button onClick={()=>command('scene_add',{kind:'drone',label:'DRONE'})}>+ DRONE</button><button onClick={()=>command('scene_add',{kind:'globe',label:'EARTH',color:'#35ffe4'})}>+ GLOBE</button>
   <button onClick={()=>command('scene_arrange',{layout:'orbit'})}>ORBIT DÜZEN</button><button onClick={()=>command('scene_arrange',{layout:'grid'})}>GRID DÜZEN</button><button onClick={()=>command('scene_camera',{camera:'isometric'})}>ISO CAM</button><button onClick={()=>command('scene_camera',{camera:'top'})}>TOP CAM</button><button onClick={()=>command('scene_animation',{animation:stage.scene.explode?'assemble':'explode'})}>{stage.scene.explode?'BİRLEŞTİR':'PATLAT'}</button><button onClick={()=>command('scene_animation',{animation:stage.scene.animation==='scan'?'idle':'scan'})}>SCAN</button><button onClick={downloadScene}><Download/> SAHNEYİ KAYDET</button><button onClick={()=>sceneFile.current?.click()}>SAHNE AÇ</button><button onClick={()=>command('video_from_stage',{duration:8,title:'ULTRON SCENE'})}><Video/> SAHNEYİ VİDEO YAP</button><button onClick={()=>command('reset')}><RotateCcw/> CORE</button>
  </div>{(()=>{const o=stage.scene.objects.find(x=>x.id===stage.scene.selected_id);if(!o)return null;return <div className="scene-inspector"><b>{o.label}</b><span>{o.id}</span><div className="gizmo-modes"><button className={transformMode==='translate'?'active':''} onClick={()=>setTransformMode('translate')}>TAŞI</button><button className={transformMode==='rotate'?'active':''} onClick={()=>setTransformMode('rotate')}>DÖNDÜR</button><button className={transformMode==='scale'?'active':''} onClick={()=>setTransformMode('scale')}>ÖLÇEK</button></div><div><button onClick={()=>command('scene_update',{object_id:o.id,x:(o.position?.[0]||0)-.5})}>←</button><button onClick={()=>command('scene_update',{object_id:o.id,x:(o.position?.[0]||0)+.5})}>→</button><button onClick={()=>command('scene_update',{object_id:o.id,y:(o.position?.[1]||0)+.5})}>↑</button><button onClick={()=>command('scene_update',{object_id:o.id,y:(o.position?.[1]||0)-.5})}>↓</button></div><label>BOYUT<input type="range" min=".2" max="3" step=".1" value={o.scale} onChange={e=>command('scene_update',{object_id:o.id,scale:+e.target.value})}/></label><label>PATLAT<input type="range" min="0" max="2" step=".1" value={o.explode||0} onChange={e=>command('scene_update',{object_id:o.id,explode:+e.target.value})}/></label><button onClick={()=>command('scene_remove',{object_id:o.id})}>NESNEYİ SİL</button></div>})()}</div>}
  {stage.mode==='video_rendering'&&<div className="stage-video-render"><VideoRenderer stage={stage} onReady={(url,blob)=>{if(videoUrl)URL.revokeObjectURL(videoUrl);setVideoUrl(url);setVideoBlob(blob);setRenderProgress(100);}} onError={setRenderError} onProgress={setRenderProgress}/><div className="render-overlay"><Sparkles/><h2>ULTRON VIDEO RENDER</h2><p>{stage.video.template.replaceAll('_',' ').toUpperCase()} · {stage.video.duration}s</p><div className="stage-progress"><i style={{width:renderProgress+'%'}}/></div><b className="render-percent">%{renderProgress}</b><small>{renderError||'Frame üretimi ve WebM kodlama devam ediyor…'}</small></div></div>}
  {stage.mode==='video_preview'&&<div className="stage-video-preview">{videoUrl?<video ref={video} src={videoUrl} autoPlay loop controls playsInline/>:<div className="stage-missing-video"><Video/><h2>VIDEO OTURUMU HAZIR</h2><p>Bu render başka bir UI oturumunda üretildi. Yeniden üretmek için Render düğmesini kullan.</p></div>}<div className="video-actions"><button onClick={()=>{const v=video.current;if(!v)return;v.paused?v.play():v.pause();}}><Play/> OYNAT / DURAKLAT</button><button disabled={!videoBlob} onClick={downloadVideo}><Download/> KAYDET</button><button onClick={()=>command('video_create',{template:stage.video.template,duration:stage.video.duration,title:stage.video.title})}><RotateCcw/> YENİDEN RENDER</button><button onClick={()=>command('reset')}><Maximize2/> CORE</button></div></div>}
  {stage.mode==='task_progress'&&<div className="stage-task"><div className="task-orb"/><h2>{stage.title}</h2><p>{stage.subtitle}</p><div className="stage-progress"><i style={{width:Math.max(0,Math.min(100,stage.progress))+'%'}}/></div><b>%{Math.round(stage.progress)}</b></div>}
  {stage.mode==='screen_preview'&&<div className="stage-task"><ScanFrame/><h2>SCREEN PREVIEW</h2><p>Vizyon önizlemesi için Ekran Yakalama aracını kullan.</p><button onClick={()=>command('reset')}>CORE'A DÖN</button></div>}
  {stage.mode!=='core_idle'&&<div className="stage-mode-tag"><span>{stage.title}</span><small>{customModelName?customModelName+' / '+stage.subtitle:stage.subtitle}</small></div>}
  <input ref={sceneFile} hidden type="file" accept=".json,.ultron-scene.json,application/json" onChange={async e=>{const file=e.target.files?.[0];e.target.value='';if(!file)return;try{const data=JSON.parse(await file.text()),scene=data?.scene;if(!scene||!Array.isArray(scene.objects))throw Error('Geçersiz sahne dosyası');await command('scene_batch',{objects_json:JSON.stringify(scene.objects),camera:scene.camera||'isometric',animation:scene.animation||'idle'});}catch(err){notify('Sahne açılamadı: '+String(err));}}}/>
  <input ref={modelFile} hidden type="file" accept=".glb,model/gltf-binary" onChange={async e=>{const file=e.target.files?.[0];e.target.value='';if(!file)return;if(!/\.glb$/i.test(file.name)){notify('Center Stage için GLB dosyası seç.');return;}if(file.size>50*1024*1024){notify('GLB modeli en fazla 50 MB olabilir.');return;}try{setCustomModel(await file.arrayBuffer());setCustomModelName(file.name);if(stage.mode!=='hologram_lab')await command('hologram_create',{kind:stage.hologram.kind||'energy',label:file.name.replace(/\.glb$/i,'')});}catch(err){notify('3D model açılamadı: '+String(err));}}}/>
 </div>;
}

function ScanFrame(){return <div className="scan-frame"><i/><i/><i/><i/></div>;}
