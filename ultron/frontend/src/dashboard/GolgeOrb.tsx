import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import type {CoreState} from './runtime';
import {buildCoreNetwork} from './coreNetwork';

/** Real-time procedural CORE: bounded GPU buffers, connected nodes and signal flow.
 * Amplitude is supplied by the native audio bridge; the orb never fabricates audio input.
 */
export default function GolgeOrb({state,amplitude}:{state:CoreState;amplitude:number}){
 const host=useRef<HTMLDivElement>(null);
 const dynamics=useRef({state,amplitude});
 const [fallback,setFallback]=useState(false);
 useEffect(()=>{dynamics.current={state,amplitude}},[state,amplitude]);
 useEffect(()=>{
  const el=host.current;if(!el)return;
  let renderer:THREE.WebGLRenderer|undefined,frame=0,disposed=false,visible=true,running=false;
  const geometries:THREE.BufferGeometry[]=[];
  const materials:THREE.Material[]=[];
  const track=<T extends THREE.BufferGeometry,>(g:T)=>{geometries.push(g);return g};
  const material=<T extends THREE.Material,>(m:T)=>{materials.push(m);return m};
  let resizeObserver:ResizeObserver|undefined,intersectionObserver:IntersectionObserver|undefined;
  let pointerMove:(e:PointerEvent)=>void=()=>{};
  let visibilityChange=()=>{};
  try{
   renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'});
   renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.35));
   renderer.setClearColor(0x000000,0);
   renderer.outputColorSpace=THREE.SRGBColorSpace;
   renderer.domElement.setAttribute('aria-hidden','true');
   renderer.domElement.setAttribute('tabindex','-1');
   el.appendChild(renderer.domElement);
   const scene=new THREE.Scene();
   const camera=new THREE.PerspectiveCamera(44,1,.1,60);
   camera.position.set(0,0,8.1);
   const group=new THREE.Group();scene.add(group);
   const glass=material(new THREE.ShaderMaterial({
     transparent:true,depthWrite:false,side:THREE.DoubleSide,
     uniforms:{time:{value:0},energy:{value:0},alert:{value:0}},
     vertexShader:`varying vec3 vN;varying vec3 vP;void main(){vec4 p=modelViewMatrix*vec4(position,1.0);vN=normalize(normalMatrix*normal);vP=p.xyz;gl_Position=projectionMatrix*p;}`,
     fragmentShader:`varying vec3 vN;varying vec3 vP;uniform float time;uniform float energy;uniform float alert;
      void main(){float rim=pow(1.0-abs(dot(normalize(vN),normalize(-vP))),2.6);
      float surface=pow(1.0-abs(dot(normalize(vN),normalize(-vP))),.75);
      float shimmer=.62+.24*sin(time*.43+vN.y*9.0+vN.x*4.0);
      vec3 cyan=vec3(.48,.92,.99),red=vec3(1.0,.17,.25);vec3 col=mix(mix(vec3(.012,.07,.11),cyan,rim),red,alert*.72);
      gl_FragColor=vec4(col*(rim*2.1+surface*.16)*shimmer,clamp(.10+rim*.78+energy*.06,0.,.94));}`
   }));
   const shell=new THREE.Mesh(track(new THREE.SphereGeometry(1.55,72,52)),glass);group.add(shell);
   const inner=material(new THREE.MeshBasicMaterial({color:0x071722,transparent:true,opacity:.82,depthWrite:false}));
   group.add(new THREE.Mesh(track(new THREE.SphereGeometry(1.44,40,32)),inner));

   const net=buildCoreNetwork(1400);
   const nodeGeometry=track(new THREE.BufferGeometry());
   nodeGeometry.setAttribute('position',new THREE.BufferAttribute(net.nodePositions,3));
   nodeGeometry.setAttribute('color',new THREE.BufferAttribute(net.nodeColors,3));
   nodeGeometry.setAttribute('seed',new THREE.BufferAttribute(net.nodeSeeds,1));
   const nodeMaterial=material(new THREE.ShaderMaterial({
    transparent:true,depthWrite:false,vertexColors:true,blending:THREE.AdditiveBlending,
    uniforms:{time:{value:0},energy:{value:0},alert:{value:0}},
    vertexShader:`attribute float seed;uniform float time;uniform float energy;uniform float alert;varying vec3 vColor;varying float vAlpha;
      void main(){float pulse=sin(time*1.25+seed*18.0)*(.012+energy*.025);vec3 p=position*(1.0+pulse);vec4 mv=modelViewMatrix*vec4(p,1.0);gl_Position=projectionMatrix*mv;
      gl_PointSize=clamp((2.2+energy*1.5)*(235.0/-mv.z),1.6,6.0);vColor=mix(color,vec3(1.0,.2,.15),alert*.8);vAlpha=.86+.14*(.5+.5*sin(time*1.7+seed*25.0));}`,
    fragmentShader:`varying vec3 vColor;varying float vAlpha;void main(){vec2 p=gl_PointCoord-.5;float d=length(p);if(d>.5)discard;float core=1.0-smoothstep(.06,.5,d);gl_FragColor=vec4(vColor,core*vAlpha);}`
   }));
   group.add(new THREE.Points(nodeGeometry,nodeMaterial));

   const linkGeometry=track(new THREE.BufferGeometry());linkGeometry.setAttribute('position',new THREE.BufferAttribute(net.links,3));
   const lineMaterial=material(new THREE.LineBasicMaterial({color:0x63d8ea,transparent:true,opacity:.045,blending:THREE.AdditiveBlending,depthWrite:false}));
   group.add(new THREE.LineSegments(linkGeometry,lineMaterial));
   const flowCount=net.flowSeeds.length;
   const flowGeometry=track(new THREE.BufferGeometry());
   const starts=new Float32Array(flowCount*3),ends=new Float32Array(flowCount*3);
   for(let i=0;i<flowCount;i++){const at=i*6,to=i*3;starts.set(net.links.subarray(at,at+3),to);ends.set(net.links.subarray(at+3,at+6),to);}
   flowGeometry.setAttribute('start',new THREE.BufferAttribute(starts,3));
   flowGeometry.setAttribute('end',new THREE.BufferAttribute(ends,3));
   flowGeometry.setAttribute('seed',new THREE.BufferAttribute(net.flowSeeds,1));
   const flowMaterial=material(new THREE.ShaderMaterial({
    transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,
    uniforms:{time:{value:0},energy:{value:0},speed:{value:.05},alert:{value:0}},
    vertexShader:`attribute vec3 start;attribute vec3 end;attribute float seed;uniform float time;uniform float energy;uniform float speed;varying float vAlpha;
     void main(){float phase=fract(seed+time*speed);vec3 p=mix(start,end,phase);vec4 mv=modelViewMatrix*vec4(p,1.0);gl_Position=projectionMatrix*mv;gl_PointSize=clamp((1.2+energy*1.5)*(180.0/-mv.z),1.0,4.6);vAlpha=(.12+.88*sin(phase*3.14159265))*(.04+energy*.85);}`,
    fragmentShader:`uniform float alert;varying float vAlpha;void main(){float d=length(gl_PointCoord-.5);if(d>.5)discard;float glow=1.0-smoothstep(.08,.5,d);vec3 cyan=vec3(.43,.91,1.0);vec3 col=mix(cyan,vec3(1.0,.17,.18),alert);gl_FragColor=vec4(col,glow*vAlpha);}`
   }));
   group.add(new THREE.Points(flowGeometry,flowMaterial));

   const rings:THREE.Group[]=[];
   for(let i=0;i<4;i++){
    const orbit=new THREE.Group();orbit.rotation.set(.27+i*.43,.12+i*.49,-.4+i*.3);
    const color=[0xb3f7ff,0x43d0e6,0x96d6e3,0x70d2dc][i];
    const ringMat=material(new THREE.MeshBasicMaterial({color,transparent:true,opacity:[.58,.28,.21,.16][i],blending:THREE.AdditiveBlending,depthWrite:false}));
    const mesh=new THREE.Mesh(track(new THREE.TorusGeometry(1.62+i*.12,.008+i*.002,6,160)),ringMat);
    mesh.scale.set(1.17,.72,1);orbit.add(mesh);group.add(orbit);rings.push(orbit);
   }
   const beamMaterial=material(new THREE.ShaderMaterial({transparent:true,depthWrite:false,side:THREE.DoubleSide,blending:THREE.AdditiveBlending,
    vertexShader:`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader:`varying vec2 vUv;void main(){float edge=1.0-abs(vUv.x-.5)*2.0;float fade=smoothstep(0.0,.32,vUv.y)*(1.0-smoothstep(.65,1.0,vUv.y));float a=pow(max(0.0,edge),3.0)*fade*.22;gl_FragColor=vec4(.25,.86,1.0,a);}`
   }));
   const beam=new THREE.Mesh(track(new THREE.ConeGeometry(.72,1.38,40,1,true)),beamMaterial);beam.position.set(0,-2.05,0);beam.rotation.x=Math.PI;group.add(beam);
   const baseMaterial=material(new THREE.MeshBasicMaterial({color:0x6feaf4,transparent:true,opacity:.18,blending:THREE.AdditiveBlending,depthWrite:false}));
   for(let i=0;i<3;i++){const base=new THREE.Mesh(track(new THREE.TorusGeometry(.44+i*.24,.012,7,128)),baseMaterial);base.rotation.x=-Math.PI/2;base.position.y=-2.78+i*.015;base.scale.set(1.45,.56,1);group.add(base);}
   const flare=new THREE.Mesh(track(new THREE.SphereGeometry(.1,18,12)),material(new THREE.MeshBasicMaterial({color:0xa5faff,transparent:true,opacity:.86})));
   flare.position.set(.06,-1.30,.72);group.add(flare);

   const resize=()=>{const w=Math.max(1,el.clientWidth),h=Math.max(1,el.clientHeight);renderer?.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();};
   resizeObserver=new ResizeObserver(resize);resizeObserver.observe(el);resize();
   let targetX=0,targetY=0;
   pointerMove=(e:PointerEvent)=>{const r=el.getBoundingClientRect();targetY=THREE.MathUtils.clamp((e.clientX-r.left)/r.width-.5,-.5,.5)*.22;targetX=THREE.MathUtils.clamp((e.clientY-r.top)/r.height-.5,-.5,.5)*-.18;};
   el.addEventListener('pointermove',pointerMove,{passive:true});
   const reduce=window.matchMedia?.('(prefers-reduced-motion: reduce)');
   const clock=new THREE.Clock();let last=0;
   const shouldRender=()=>!disposed&&visible&&!document.hidden;
   const tick=()=>{
    if(!shouldRender()){running=false;return;}
    frame=requestAnimationFrame(tick);
    const t=clock.getElapsedTime();if(t-last<1/60)return;last=t;
    const d=dynamics.current,boost=THREE.MathUtils.clamp(Number(d.amplitude)||0,0,1);
    const active=d.state==='LISTENING'||d.state==='THINKING'||d.state==='SPEAKING';
    const energy=THREE.MathUtils.clamp(boost*.9+(active ? .12 : 0),0,1),alert=d.state==='ERROR'?1:0;
    const motionTime=reduce?.matches?0:t;
    glass.uniforms.time.value=motionTime;glass.uniforms.energy.value=energy;glass.uniforms.alert.value=alert;
    nodeMaterial.uniforms.time.value=motionTime;nodeMaterial.uniforms.energy.value=energy;nodeMaterial.uniforms.alert.value=alert;
    flowMaterial.uniforms.time.value=motionTime;flowMaterial.uniforms.energy.value=energy;flowMaterial.uniforms.alert.value=alert;
    flowMaterial.uniforms.speed.value=reduce?.matches?0:d.state==='THINKING' ? .18 : d.state==='SPEAKING' ? .11 : d.state==='LISTENING' ? .09 : .045;
    if(!reduce?.matches){
     shell.rotation.y=t*.06;shell.rotation.z=Math.sin(t*.18)*.035;
     rings.forEach((o,i)=>{o.rotation.y=t*(i%2?-.19:.14)+i*.48;o.rotation.z=.35+i*.4+t*(i%2?.07:-.045)});
     group.rotation.x+=(targetX-group.rotation.x)*.035;group.rotation.y+=(targetY+t*.025-group.rotation.y)*.035;
     group.position.y=.035*Math.sin(t*.65);group.scale.setScalar(1+energy*.023);
     const pulse=.82+energy*.55;lineMaterial.opacity=.035+energy*.075;flare.scale.setScalar(pulse);
    }
    renderer?.render(scene,camera);
   };
   const start=()=>{if(running||!shouldRender())return;running=true;clock.start();frame=requestAnimationFrame(tick);};
   const stop=()=>{running=false;cancelAnimationFrame(frame);};
   visibilityChange=()=>document.hidden?stop():start();
   if(typeof IntersectionObserver!=='undefined'){intersectionObserver=new IntersectionObserver(entries=>{visible=Boolean(entries[0]?.isIntersecting);visible?start():stop();});intersectionObserver.observe(el);}
   document.addEventListener('visibilitychange',visibilityChange);start();
   (el as any).__golgeStopRender=stop;
   return()=>{
    disposed=true;stop();document.removeEventListener('visibilitychange',visibilityChange);el.removeEventListener('pointermove',pointerMove);
    resizeObserver?.disconnect();intersectionObserver?.disconnect();
    geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());
    if(renderer){renderer.dispose();renderer.domElement.remove();}
   };
  }catch{
   resizeObserver?.disconnect();intersectionObserver?.disconnect();
   el.removeEventListener('pointermove',pointerMove);document.removeEventListener('visibilitychange',visibilityChange);
   geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());
   renderer?.dispose();renderer?.domElement.remove();renderer=undefined;setFallback(true);
  }
  return()=>{disposed=true;cancelAnimationFrame(frame);resizeObserver?.disconnect();intersectionObserver?.disconnect();};
 },[]);
 return <div className={'core-stage golge-reference-orb '+(fallback?'orb-css-only':'')} role="img" aria-label={'GÖLGE, '+(state==='LISTENING'?'dinliyor':state==='THINKING'?'düşünüyor':state==='SPEAKING'?'konuşuyor':state==='ERROR'?'bağlantı hatası':'hazır')}>
   <div className="core-canvas golge-orb-webgl" ref={host}/>
   <div className="golge-orb-css-fallback" aria-hidden="true"><i/><span/><b/></div>
   <div className="golge-orb-ground" aria-hidden="true"/>
   {fallback&&<span className="orb-fallback-status" role="status">3D görünüm bu cihazda kullanılamıyor</span>}
 </div>;
}
