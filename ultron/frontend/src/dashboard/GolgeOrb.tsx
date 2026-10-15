import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import type {CoreState} from './runtime';
import {buildCoreNetwork} from './coreNetwork';

/** GPU light scattering and projection. Activity is independent of audio;
 * amplitude is provided only by the existing native RMS bridge. */
export default function GolgeOrb({state,amplitude}:{state:CoreState;amplitude:number}){
 const host=useRef<HTMLDivElement>(null),dynamics=useRef({state,amplitude});
 const [fallback,setFallback]=useState(false);
 useEffect(()=>{dynamics.current={state,amplitude}},[state,amplitude]);
 useEffect(()=>{
  const el=host.current;if(!el)return;
  let renderer:THREE.WebGLRenderer|undefined,frame=0,disposed=false,visible=true,running=false;
  const geometries:THREE.BufferGeometry[]=[],materials:THREE.Material[]=[];
  const geo=<T extends THREE.BufferGeometry,>(g:T)=>{geometries.push(g);return g};
  const mat=<T extends THREE.Material,>(m:T)=>{materials.push(m);return m};
  let resizeObserver:ResizeObserver|undefined,intersectionObserver:IntersectionObserver|undefined;
  let pointerMove:(e:PointerEvent)=>void=()=>{},visibilityChange=()=>{};
  const dispose=()=>{disposed=true;cancelAnimationFrame(frame);resizeObserver?.disconnect();intersectionObserver?.disconnect();el.removeEventListener('pointermove',pointerMove);document.removeEventListener('visibilitychange',visibilityChange);geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());if(renderer){renderer.dispose();renderer.domElement.remove();}};
  try{
   renderer=new THREE.WebGLRenderer({alpha:false,antialias:true,powerPreference:'low-power'});
   renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.5));renderer.setClearColor(0x030b16,1);renderer.outputColorSpace=THREE.SRGBColorSpace;
   renderer.domElement.setAttribute('aria-hidden','true');renderer.domElement.setAttribute('tabindex','-1');el.appendChild(renderer.domElement);
   const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(43,1,.1,60);
   camera.position.set(0,.42,7.7);camera.lookAt(0,-.45,0);
   const rig=new THREE.Group(),core=new THREE.Group();rig.add(core);scene.add(rig);
   const uniforms={time:{value:0},energy:{value:0},alert:{value:0},pixelScale:{value:1}};
   // The dark field and subtle grid are drawn in the same bounded GPU pass.
   const backdrop=mat(new THREE.ShaderMaterial({depthWrite:false,
    vertexShader:`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader:`varying vec2 vUv;void main(){vec2 p=vUv-.5;float glow=exp(-dot(p,p)*42.);vec2 q=abs(fract(vUv*80.)-.5);float grid=(1.-smoothstep(.0,.012,q.x))+(1.-smoothstep(.0,.012,q.y));vec3 c=vec3(.008,.022,.043)+vec3(.0,.018,.035)*glow+vec3(.0,.012,.022)*grid;gl_FragColor=vec4(c,1.);}`
   }));const backPlane=new THREE.Mesh(geo(new THREE.PlaneGeometry(20,20)),backdrop);backPlane.position.z=-5;scene.add(backPlane);

   const glass=mat(new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,side:THREE.FrontSide,
    uniforms,vertexShader:`varying vec3 vN;varying vec3 vP;void main(){vec4 p=modelViewMatrix*vec4(position,1.);vN=normalize(normalMatrix*normal);vP=p.xyz;gl_Position=projectionMatrix*p;}`,
    fragmentShader:`varying vec3 vN;varying vec3 vP;uniform float energy;uniform float alert;void main(){float rim=pow(1.-abs(dot(normalize(vN),normalize(-vP))),3.4);vec3 color=mix(vec3(.08,.55,1.),vec3(1.,.18,.12),alert);gl_FragColor=vec4(color,rim*(.16+energy*.12));}`
   }));core.add(new THREE.Mesh(geo(new THREE.SphereGeometry(1.62,64,40)),glass));
   const net=buildCoreNetwork(1400),nodeGeometry=geo(new THREE.BufferGeometry());
   nodeGeometry.setAttribute('position',new THREE.BufferAttribute(net.nodePositions,3));nodeGeometry.setAttribute('color',new THREE.BufferAttribute(net.nodeColors,3));nodeGeometry.setAttribute('seed',new THREE.BufferAttribute(net.nodeSeeds,1));
   const nodeMaterial=mat(new THREE.ShaderMaterial({transparent:true,depthWrite:false,vertexColors:true,blending:THREE.AdditiveBlending,uniforms,
    vertexShader:`attribute float seed;uniform float time;uniform float energy;uniform float alert;uniform float pixelScale;varying vec3 vColor;varying float vAlpha;
     void main(){vec3 p=position*(1.+sin(time*.9+seed*24.)*(.004+energy*.009));vec4 mv=modelViewMatrix*vec4(p,1.);gl_Position=projectionMatrix*mv;
     gl_PointSize=clamp((5.5+pow(seed,6.)*18.+energy*4.)*pixelScale*7.7/-mv.z,2.,28.);vColor=mix(color,vec3(1.,.21,.14),alert*.8);
     vAlpha=(.42+.58*smoothstep(-1.7,1.7,p.z))*(.75+.25*sin(time*.6+seed*31.));}`,
    fragmentShader:`varying vec3 vColor;varying float vAlpha;void main(){vec2 p=gl_PointCoord-.5;float r=length(p);if(r>.5)discard;
     float glow=exp(-r*r*16.)*.24+exp(-r*r*64.);float star=pow(max(0.,1.-abs(p.x)*55.),3.)*exp(-abs(p.y)*9.)+pow(max(0.,1.-abs(p.y)*55.),3.)*exp(-abs(p.x)*9.);
     gl_FragColor=vec4(vColor*1.8,(glow+star*.15)*vAlpha);}`
   }));core.add(new THREE.Points(nodeGeometry,nodeMaterial));
   const linkGeometry=geo(new THREE.BufferGeometry());linkGeometry.setAttribute('position',new THREE.BufferAttribute(net.links,3));
   const lineMaterial=mat(new THREE.LineBasicMaterial({color:0x238fe8,transparent:true,opacity:.27,blending:THREE.AdditiveBlending,depthWrite:false}));core.add(new THREE.LineSegments(linkGeometry,lineMaterial));
   const flowCount=net.flowSeeds.length,flowGeometry=geo(new THREE.BufferGeometry()),starts=new Float32Array(flowCount*3),ends=new Float32Array(flowCount*3);
   for(let i=0;i<flowCount;i++){starts.set(net.links.subarray(i*6,i*6+3),i*3);ends.set(net.links.subarray(i*6+3,i*6+6),i*3);}
   flowGeometry.setAttribute('start',new THREE.BufferAttribute(starts,3));flowGeometry.setAttribute('end',new THREE.BufferAttribute(ends,3));flowGeometry.setAttribute('seed',new THREE.BufferAttribute(net.flowSeeds,1));
   const flowMaterial=mat(new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,uniforms:{...uniforms,speed:{value:.04}},
    vertexShader:`attribute vec3 start;attribute vec3 end;attribute float seed;uniform float time;uniform float energy;uniform float speed;varying float vAlpha;
     void main(){float phase=fract(seed+time*speed);vec4 mv=modelViewMatrix*vec4(mix(start,end,phase),1.);gl_Position=projectionMatrix*mv;gl_PointSize=2.+energy*3.;vAlpha=sin(phase*3.14159)*(.08+energy*.65);}`,
    fragmentShader:`uniform float alert;varying float vAlpha;void main(){float r=length(gl_PointCoord-.5);if(r>.5)discard;gl_FragColor=vec4(mix(vec3(.5,.85,1.),vec3(1.,.2,.1),alert),exp(-r*r*26.)*vAlpha);}`
   }));core.add(new THREE.Points(flowGeometry,flowMaterial));
   const rings:THREE.Group[]=[];
   for(let i=0;i<4;i++){
    const orbit=new THREE.Group();orbit.rotation.set([1.12,.44,1.56,.83][i],[.18,.9,-.5,-.1][i],[.38,-.68,.9,-.34][i]);core.add(orbit);rings.push(orbit);
    const r=1.88+i*.09;
    orbit.add(new THREE.Mesh(geo(new THREE.TorusGeometry(r,.035,6,180)),mat(new THREE.MeshBasicMaterial({color:0x148dff,transparent:true,opacity:.085,blending:THREE.AdditiveBlending,depthWrite:false}))));
    orbit.add(new THREE.Mesh(geo(new THREE.TorusGeometry(r,.006,5,180)),mat(new THREE.MeshBasicMaterial({color:i===1?0xd9faff:0x63d9ff,transparent:true,opacity:i===1?.86:.57,blending:THREE.AdditiveBlending,depthWrite:false}))));
    const arc=new THREE.Mesh(geo(new THREE.TorusGeometry(r,.012,5,72,.66)),mat(new THREE.MeshBasicMaterial({color:0xe5feff,transparent:true,opacity:.95,blending:THREE.AdditiveBlending,depthWrite:false})));arc.rotation.z=i*1.5;orbit.add(arc);
   }
   const beamMaterial=mat(new THREE.ShaderMaterial({transparent:true,depthWrite:false,side:THREE.DoubleSide,blending:THREE.AdditiveBlending,uniforms,
    vertexShader:`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader:`varying vec2 vUv;uniform float time;uniform float energy;void main(){float rays=.58+.42*pow(sin(vUv.x*78.+time*.08),8.);float fade=sin(vUv.y*3.14159)*(.28+energy*.16);gl_FragColor=vec4(.13,.65,1.,rays*fade);}`
   }));const beam=new THREE.Mesh(geo(new THREE.ConeGeometry(1.03,1.2,64,1,true)),beamMaterial);beam.rotation.x=Math.PI;beam.position.y=-2.05;rig.add(beam);
   const floorMat=mat(new THREE.ShaderMaterial({transparent:true,depthWrite:false,side:THREE.DoubleSide,blending:THREE.AdditiveBlending,uniforms,
    vertexShader:`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader:`varying vec2 vUv;uniform float energy;void main(){float r=length(vUv-.5);float a=exp(-r*r*28.)*(.35+energy*.3);gl_FragColor=vec4(.04,.54,1.,a);}`
   }));const floor=new THREE.Mesh(geo(new THREE.PlaneGeometry(4,4)),floorMat);floor.rotation.x=-Math.PI/2;floor.position.y=-2.7;rig.add(floor);
   for(let i=0;i<6;i++){
    const base=new THREE.Mesh(geo(new THREE.TorusGeometry(.2+i*.2,i%2===0?.014:.005,6,160)),mat(new THREE.MeshBasicMaterial({color:i%2===0?0x79e4ff:0x167fff,transparent:true,opacity:i%2===0?.8:.5,blending:THREE.AdditiveBlending,depthWrite:false})));
    base.rotation.x=Math.PI/2;base.position.y=-2.68+i*.008;rig.add(base);
   }
   const pillars=new Float32Array(72*6);
   for(let i=0;i<72;i++){const a=i*2.39996,r=1.8+(i%9)*.11,x=Math.cos(a)*r,z=Math.sin(a)*r;pillars.set([x,-1.7,z,x,1.7+(i%7)*.17,z],i*6);}
   const pg=geo(new THREE.BufferGeometry());pg.setAttribute('position',new THREE.BufferAttribute(pillars,3));rig.add(new THREE.LineSegments(pg,mat(new THREE.LineBasicMaterial({color:0x1789e9,transparent:true,opacity:.07,blending:THREE.AdditiveBlending,depthWrite:false}))));
   let targetX=0,targetY=0,t=0,last=0,renderAt=0,energy=0;
   const resize=()=>{const w=Math.max(1,el.clientWidth),h=Math.max(1,el.clientHeight);renderer?.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();uniforms.pixelScale.value=Math.min(1.65,h/650);};resizeObserver=new ResizeObserver(resize);resizeObserver.observe(el);resize();
   pointerMove=e=>{const r=el.getBoundingClientRect();targetY=((e.clientX-r.left)/r.width-.5)*.16;targetX=((e.clientY-r.top)/r.height-.5)*-.08;};el.addEventListener('pointermove',pointerMove,{passive:true});
   const reduce=window.matchMedia?.('(prefers-reduced-motion: reduce)');
   const tick=(now:number)=>{
    if(disposed||!visible||document.hidden){running=false;return;}frame=requestAnimationFrame(tick);if(now-renderAt<1000/60)return;
    const dt=last?Math.min((now-last)/1000,.05):0;last=now;renderAt=now;if(!reduce?.matches)t+=dt;
    const d=dynamics.current,boost=THREE.MathUtils.clamp(Number(d.amplitude)||0,0,1);
    const activity=d.state==='THINKING'?.52:d.state==='WORKING'?.46:d.state==='LISTENING'?.16:d.state==='SPEAKING'?.26:.04;
    energy+=(Math.min(1,activity+boost*.8)-energy)*Math.min(1,dt*7);uniforms.time.value=t;uniforms.energy.value=energy;uniforms.alert.value=d.state==='ERROR'?1:0;
    flowMaterial.uniforms.speed.value=reduce?.matches?0:d.state==='THINKING'?.36:d.state==='SPEAKING'?.2:d.state==='LISTENING'?.13:.055;
    el.dataset.state=d.state;el.dataset.audioLevel=boost.toFixed(3);
    if(!reduce?.matches){core.rotation.y=t*.045;core.rotation.z=Math.sin(t*.18)*.024;core.scale.setScalar(1+Math.sin(t*.8)*.005+boost*.022);rig.rotation.x+=(targetX-rig.rotation.x)*.035;rig.rotation.y+=(targetY-rig.rotation.y)*.035;rings.forEach((o,i)=>{o.rotation.z+=[.12,-.18,.085,-.1][i]*dt*(1+energy);});}
    lineMaterial.opacity=.075+energy*.11;renderer?.render(scene,camera);
   };
   const start=()=>{if(running||disposed||!visible||document.hidden)return;running=true;last=0;frame=requestAnimationFrame(tick);};
   const stop=()=>{running=false;cancelAnimationFrame(frame);};visibilityChange=()=>document.hidden?stop():start();document.addEventListener('visibilitychange',visibilityChange);
   if(typeof IntersectionObserver!=='undefined'){intersectionObserver=new IntersectionObserver(entries=>{visible=Boolean(entries[0]?.isIntersecting);visible?start():stop();});intersectionObserver.observe(el);}start();return dispose;
  }catch{dispose();setFallback(true);}
 },[]);
 return <div className={'core-stage golge-reference-orb '+(fallback?'orb-css-only':'')} role="img" aria-label={'GÖLGE, '+(state==='LISTENING'?'dinliyor':state==='THINKING'?'düşünüyor':state==='SPEAKING'?'konuşuyor':state==='ERROR'?'bağlantı hatası':'hazır')}>
  <div className="core-canvas golge-orb-webgl" ref={host}/><div className="golge-orb-ground" aria-hidden="true"/>
  {fallback&&<span className="orb-fallback-status" role="status">3D görünüm bu cihazda kullanılamıyor</span>}
 </div>;
}
