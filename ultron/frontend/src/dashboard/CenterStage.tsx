import {useEffect,useMemo,useRef,useState} from 'react';
import * as THREE from 'three';
import {Download,Maximize2,Play,RotateCcw,Sparkles,Video} from 'lucide-react';
import UltronCore from './core/UltronCore';
import {request,type CoreState,type HologramConfig,type StageState} from './runtime';

type Props={stage:StageState;state:CoreState;amplitude:number;notify:(text:string)=>void};

function colorOf(value:string){
 try{return new THREE.Color(value||'#ff3047');}catch{return new THREE.Color('#ff3047');}
}

function HologramStage({config}:{config:HologramConfig}){
 const host=useRef<HTMLDivElement>(null);
 useEffect(()=>{
  const el=host.current;if(!el)return;
  const scene=new THREE.Scene();
  scene.fog=new THREE.FogExp2(0x020407,.055);
  const camera=new THREE.PerspectiveCamera(42,1,.1,100);camera.position.set(0,.25,7.6);
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'high-performance'});
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setClearColor(0x000000,0);
  el.appendChild(renderer.domElement);
  const root=new THREE.Group();scene.add(root);
  const color=colorOf(config.color),mat=new THREE.MeshBasicMaterial({color,transparent:true,opacity:config.opacity,wireframe:config.wireframe});
  const dim=new THREE.MeshBasicMaterial({color,transparent:true,opacity:Math.max(.12,config.opacity*.38),wireframe:true});
  const add=(g:THREE.BufferGeometry,m:THREE.Material=mat,x=0,y=0,z=0)=>{const mesh=new THREE.Mesh(g,m);mesh.position.set(x,y,z);root.add(mesh);return mesh;};
  const torus=(r:number,t=.012,rx=0,ry=0,rz=0)=>{const m=add(new THREE.TorusGeometry(r,t,8,128));m.rotation.set(rx,ry,rz);return m;};

  const kind=config.kind||'energy';
  if(kind==='globe'){
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

  let dead=false,frame=0,last=performance.now();
  const resize=()=>{const w=Math.max(1,el.clientWidth),h=Math.max(1,el.clientHeight);renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();};resize();
  const ro=new ResizeObserver(resize);ro.observe(el);
  const move=(e:PointerEvent)=>{const r=renderer.domElement.getBoundingClientRect();const x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;root.rotation.y=x*1.1;root.rotation.x=-y*.65;};
  renderer.domElement.addEventListener('pointermove',move);
  const loop=(now:number)=>{if(dead)return;const dt=Math.min(.05,(now-last)/1000);last=now;const pulse=config.pulse?1+Math.sin(now*.003)*.055:1;root.scale.setScalar(config.scale*pulse);root.rotation.y+=dt*.42*config.speed;particles.rotation.y-=dt*.11*config.speed;renderer.render(scene,camera);frame=requestAnimationFrame(loop);};frame=requestAnimationFrame(loop);
  return()=>{dead=true;cancelAnimationFrame(frame);ro.disconnect();renderer.domElement.removeEventListener('pointermove',move);renderer.dispose();scene.traverse(o=>{const m=o as THREE.Mesh;if(m.geometry)m.geometry.dispose();if((m as any).material){const a=Array.isArray((m as any).material)?(m as any).material:[(m as any).material];a.forEach((x:THREE.Material)=>x.dispose());}});renderer.domElement.remove();};
 },[config.kind,config.color,config.glow,config.speed,config.rings,config.particles,config.scale,config.opacity,config.wireframe,config.pulse]);
 return <div className="stage-hologram"><div ref={host} className="stage-webgl"/><div className="stage-holo-label"><b>{config.label||'ULTRON'}</b><span>{String(config.kind||'energy').toUpperCase()} HOLOGRAM</span></div></div>;
}

function drawVideoFrame(ctx:CanvasRenderingContext2D,w:number,h:number,p:number,stage:StageState){
 const video=stage.video,color=colorOf(stage.hologram.color),theme='#'+color.getHexString(),title=video.title||'ULTRON',template=video.template||'ultron_intro';
 ctx.fillStyle='#020407';ctx.fillRect(0,0,w,h);
 const g=ctx.createRadialGradient(w*.5,h*.48,10,w*.5,h*.48,w*.48);g.addColorStop(0,theme+'55');g.addColorStop(.45,theme+'13');g.addColorStop(1,'#00000000');ctx.fillStyle=g;ctx.fillRect(0,0,w,h);
 ctx.save();ctx.translate(w/2,h/2);ctx.strokeStyle=theme;ctx.shadowColor=theme;ctx.shadowBlur=16;ctx.globalAlpha=.9;
 const spin=p*Math.PI*2*(template==='energy_core'?2.2:1);
 for(let i=0;i<7;i++){ctx.beginPath();ctx.ellipse(0,0,145+i*24,(145+i*24)*(.52+.12*Math.sin(i)),spin*(i%2?1:-1)+i*.4,0,Math.PI*2);ctx.lineWidth=i%2?2:1;ctx.stroke();}
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
 const [videoUrl,setVideoUrl]=useState(''),[videoBlob,setVideoBlob]=useState<Blob|null>(null),[renderError,setRenderError]=useState(''),[renderProgress,setRenderProgress]=useState(0);
 const video=useRef<HTMLVideoElement>(null),lastSaveNonce=useRef(0);
 useEffect(()=>()=>{if(videoUrl)URL.revokeObjectURL(videoUrl);},[videoUrl]);
 useEffect(()=>{if(stage.mode==='video_rendering'){setRenderError('');setRenderProgress(0);}},[stage.job_id,stage.mode]);
 useEffect(()=>{if(video.current)stage.video_paused?video.current.pause():video.current.play().catch(()=>{});},[stage.video_paused,stage.revision]);
 const patch=(body:Record<string,unknown>)=>request('/api/stage/control',body).catch(e=>notify(String(e)));
 const command=(operation:string,extra:Record<string,unknown>={})=>request('/api/stage/command',{operation,...extra}).catch(e=>notify(String(e)));
 const downloadVideo=()=>{if(!videoBlob||!videoUrl){notify('Bu oturumda video verisi yok. Videoyu yeniden render et.');return;}const a=document.createElement('a');a.href=videoUrl;a.download='ultron-'+(stage.video.template||'animation')+'.webm';a.click();};
 const downloadHologram=()=>{const payload={version:1,type:'ultron-center-stage',saved_at:new Date().toISOString(),hologram:stage.hologram};const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='ultron-hologram.ultron.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);};
 useEffect(()=>{const nonce=Number(stage.save_nonce||0);if(!nonce||nonce===lastSaveNonce.current)return;lastSaveNonce.current=nonce;if(stage.save_kind==='video')downloadVideo();else if(stage.save_kind==='hologram')downloadHologram();},[stage.save_nonce,stage.save_kind,videoBlob,videoUrl,stage.hologram,stage.video.template]);
 const presets=useMemo(()=>['energy','globe','network','drone','vehicle','logo','sphere'],[]);
 return <div className={'center-stage mode-'+stage.mode}>
  {stage.mode==='core_idle'&&<><UltronCore state={state} amplitude={amplitude}/><div className="core-title">ULTRON<small>NEURAL CORE</small></div></>}
  {stage.mode==='hologram_lab'&&<><HologramStage config={stage.hologram}/><div className="stage-controls">
   <div className="stage-presets">{presets.map(k=><button key={k} className={stage.hologram.kind===k?'active':''} onClick={()=>patch({kind:k})}>{k.toUpperCase()}</button>)}</div>
   <label>RENK<input type="color" value={stage.hologram.color.startsWith('#')?stage.hologram.color:'#ff3047'} onChange={e=>patch({color:e.target.value})}/></label>
   <label>BOYUT<input type="range" min=".35" max="2" step=".05" value={stage.hologram.scale} onChange={e=>patch({scale:+e.target.value})}/></label>
   <label>HIZ<input type="range" min=".05" max="4" step=".05" value={stage.hologram.speed} onChange={e=>patch({speed:+e.target.value})}/></label>
   <label>HALKA<input type="range" min="0" max="10" step="1" value={stage.hologram.rings} onChange={e=>patch({rings:+e.target.value})}/></label>
   <button onClick={()=>patch({wireframe:!stage.hologram.wireframe})}>{stage.hologram.wireframe?'SOLID':'WIREFRAME'}</button>
   <button onClick={downloadHologram}><Download/> KAYDET</button>
   <button onClick={()=>command('video_from_stage',{duration:6,title:stage.hologram.label})}><Video/> VİDEOYA ÇEVİR</button>
   <button onClick={()=>command('reset')}><RotateCcw/> CORE</button>
  </div></>}
  {stage.mode==='video_rendering'&&<div className="stage-video-render"><VideoRenderer stage={stage} onReady={(url,blob)=>{if(videoUrl)URL.revokeObjectURL(videoUrl);setVideoUrl(url);setVideoBlob(blob);setRenderProgress(100);}} onError={setRenderError} onProgress={setRenderProgress}/><div className="render-overlay"><Sparkles/><h2>ULTRON VIDEO RENDER</h2><p>{stage.video.template.replaceAll('_',' ').toUpperCase()} · {stage.video.duration}s</p><div className="stage-progress"><i style={{width:renderProgress+'%'}}/></div><b className="render-percent">%{renderProgress}</b><small>{renderError||'Frame üretimi ve WebM kodlama devam ediyor…'}</small></div></div>}
  {stage.mode==='video_preview'&&<div className="stage-video-preview">{videoUrl?<video ref={video} src={videoUrl} autoPlay loop controls playsInline/>:<div className="stage-missing-video"><Video/><h2>VIDEO OTURUMU HAZIR</h2><p>Bu render başka bir UI oturumunda üretildi. Yeniden üretmek için Render düğmesini kullan.</p></div>}<div className="video-actions"><button onClick={()=>{const v=video.current;if(!v)return;v.paused?v.play():v.pause();}}><Play/> OYNAT / DURAKLAT</button><button disabled={!videoBlob} onClick={downloadVideo}><Download/> KAYDET</button><button onClick={()=>command('video_create',{template:stage.video.template,duration:stage.video.duration,title:stage.video.title})}><RotateCcw/> YENİDEN RENDER</button><button onClick={()=>command('reset')}><Maximize2/> CORE</button></div></div>}
  {stage.mode==='task_progress'&&<div className="stage-task"><div className="task-orb"/><h2>{stage.title}</h2><p>{stage.subtitle}</p><div className="stage-progress"><i style={{width:Math.max(0,Math.min(100,stage.progress))+'%'}}/></div><b>%{Math.round(stage.progress)}</b></div>}
  {stage.mode==='screen_preview'&&<div className="stage-task"><ScanFrame/><h2>SCREEN PREVIEW</h2><p>Vizyon önizlemesi için Ekran Yakalama aracını kullan.</p><button onClick={()=>command('reset')}>CORE'A DÖN</button></div>}
  {stage.mode!=='core_idle'&&<div className="stage-mode-tag"><span>{stage.title}</span><small>{stage.subtitle}</small></div>}
 </div>;
}

function ScanFrame(){return <div className="scan-frame"><i/><i/><i/><i/></div>;}
