import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import type {CoreState} from './runtime';

/** Lightweight procedural glass orb. No remote image, GPU model or network call.
 * WebGL failure falls back to a CSS orb; other stage modes keep their scenes.
 */
export default function GolgeOrb({state,amplitude}:{state:CoreState;amplitude:number}){
 const host=useRef<HTMLDivElement>(null);
 const dynamics=useRef({state,amplitude});
 const [fallback,setFallback]=useState(false);
 useEffect(()=>{dynamics.current={state,amplitude}},[state,amplitude]);
 useEffect(()=>{
  const el=host.current;if(!el)return;
  let renderer:THREE.WebGLRenderer|undefined,frame=0,disposed=false;
  const geometry:THREE.BufferGeometry[]=[];
  const materials:THREE.Material[]=[];
  const track=<T extends THREE.BufferGeometry,>(g:T)=>{geometry.push(g);return g};
  const material=<T extends THREE.Material,>(m:T)=>{materials.push(m);return m};
  let observer:ResizeObserver|undefined;
  try{
   renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'});
   renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.5));
   renderer.setClearColor(0x000000,0);
   renderer.outputColorSpace=THREE.SRGBColorSpace;
   renderer.domElement.setAttribute('aria-hidden','true');
   el.appendChild(renderer.domElement);
   const scene=new THREE.Scene();
   const camera=new THREE.PerspectiveCamera(44,1,.1,60);
   camera.position.set(0,0,8.1);
   const group=new THREE.Group();scene.add(group);
   const glass=material(new THREE.ShaderMaterial({
     transparent:true,depthWrite:false,side:THREE.DoubleSide,
     uniforms:{time:{value:0},energy:{value:0}},
     vertexShader:`varying vec3 vN;varying vec3 vP;void main(){vec4 p=modelViewMatrix*vec4(position,1.0);vN=normalize(normalMatrix*normal);vP=p.xyz;gl_Position=projectionMatrix*p;}`,
     fragmentShader:`varying vec3 vN;varying vec3 vP;uniform float time;uniform float energy;
      void main(){float rim=pow(1.0-abs(dot(normalize(vN),normalize(-vP))),2.6);
      float surface=pow(1.0-abs(dot(normalize(vN),normalize(-vP))),.75);
      float shimmer=.64+.22*sin(time*.43+vN.y*9.0+vN.x*4.0);
      vec3 col=mix(vec3(.012,.07,.11),vec3(.54,.95,1.0),rim);
      gl_FragColor=vec4(col*(rim*2.4+surface*.17)*shimmer,clamp(.12+rim*.81+energy*.05,0.,.96));}`
   }));
   const shell=new THREE.Mesh(track(new THREE.SphereGeometry(1.55,80,64)),glass);
   group.add(shell);
   const core=material(new THREE.MeshBasicMaterial({
      color:0x071722,transparent:true,opacity:.91,depthWrite:false
   }));
   group.add(new THREE.Mesh(track(new THREE.SphereGeometry(1.45,48,36)),core));
   // Three axial rings are actual 3D toroidal geometry (not a static bitmap).
   const rings:THREE.Group[]=[];
   for(let i=0;i<3;i++){
     const orbit=new THREE.Group();
     orbit.rotation.set(.29+i*.5,.12+i*.55,-.4+i*.35);
     const mat=material(new THREE.MeshBasicMaterial({
       color:[0xb3f7ff,0x43d0e6,0x96d6e3][i],transparent:true,
       opacity:[.58,.25,.19][i],blending:THREE.AdditiveBlending,depthWrite:false
     }));
     const mesh=new THREE.Mesh(track(new THREE.TorusGeometry(1.6+i*.14,.009+i*.003,7,180)),mat);
     mesh.scale.set(1.2,.75,1);
     orbit.add(mesh);group.add(orbit);rings.push(orbit);
   }
   const halo=material(new THREE.MeshBasicMaterial({
     color:0x42d8f6,transparent:true,opacity:.13,blending:THREE.AdditiveBlending,depthWrite:false
   }));
   for(let i=0;i<2;i++){
     const arc=new THREE.Mesh(track(new THREE.TorusGeometry(1.52+i*.08,.028,12,190,Math.PI*(1.25+i*.23))),halo);
     arc.rotation.set(.1+i*.95, .35+i*.4, .4+i*.92);
     group.add(arc);
   }
   const positions=new Float32Array(230*3);
   for(let i=0;i<230;i++){
     const a=i*2.3999632297,b=Math.acos(1-2*(i+.5)/230);
     const r=1.87+(i%11)*.031;
     positions[i*3]=r*Math.sin(b)*Math.cos(a);
     positions[i*3+1]=r*Math.cos(b);
     positions[i*3+2]=r*Math.sin(b)*Math.sin(a);
   }
   const pointsGeo=track(new THREE.BufferGeometry());
   pointsGeo.setAttribute('position',new THREE.BufferAttribute(positions,3));
   const particles=new THREE.Points(pointsGeo,material(new THREE.PointsMaterial({
     size:.022,color:0x8ae9fd,transparent:true,opacity:.7,blending:THREE.AdditiveBlending,depthWrite:false
   })));
   group.add(particles);
   const flare=new THREE.Mesh(
     track(new THREE.SphereGeometry(.12,24,16)),
     material(new THREE.MeshBasicMaterial({color:0xa5faff,transparent:true,opacity:.86}))
   );
   flare.position.set(.06,-1.30,.72);group.add(flare);
   const resize=()=>{
     const w=Math.max(1,el.clientWidth),h=Math.max(1,el.clientHeight);
     renderer?.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();
   };
   observer=new ResizeObserver(resize);observer.observe(el);resize();
   const reduced=window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
   const clock=new THREE.Clock();
   let last=0;
   const tick=()=>{
     if(disposed)return;
     frame=requestAnimationFrame(tick);
     if(document.hidden)return;
     const t=clock.getElapsedTime();
     if(t-last<1/40)return;last=t;
     const d=dynamics.current;
     const boost=Math.min(Math.max(d.amplitude||0,0),1);
     const active=d.state==='LISTENING'||d.state==='THINKING'||d.state==='SPEAKING';
     const energy=(active ? 0.5 : 0)+boost*.3;
     glass.uniforms.time.value=t;glass.uniforms.energy.value=energy;
     if(!reduced){
       shell.rotation.y=t*.085;shell.rotation.z=Math.sin(t*.22)*.06;
       rings.forEach((o,i)=>{o.rotation.y=t*(i%2?-.15:.12)+i*.55;o.rotation.z=.4+i*.42+t*(i%2?.06:-.04)});
       particles.rotation.y=-t*.035;
       group.position.y=.045*Math.sin(t*.8);
       group.scale.setScalar(1+energy*.028);
     }
     renderer?.render(scene,camera);
   };
   tick();
  }catch{
   setFallback(true);
  }
  return ()=>{
    disposed=true;cancelAnimationFrame(frame);
    observer?.disconnect();
    geometry.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());
    if(renderer){renderer.dispose();renderer.domElement.remove();}
  };
 },[]);
 return <div className={'core-stage golge-reference-orb '+(fallback?'orb-css-only':'')} role="img" aria-label={'GÖLGE, '+(state==='LISTENING'?'dinliyor':state==='SPEAKING'?'konuşuyor':'hazır')}>
   <div className="core-canvas golge-orb-webgl" ref={host}/>
   <div className="golge-orb-css-fallback" aria-hidden="true"><i/><span/><b/></div>
   <div className="golge-orb-ground" aria-hidden="true"/>
 </div>;
}
