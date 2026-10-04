import * as T from 'three';
import {EffectComposer} from 'three/examples/jsm/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/examples/jsm/postprocessing/RenderPass.js';
import {UnrealBloomPass} from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import {OutputPass} from 'three/examples/jsm/postprocessing/OutputPass.js';
import type {CoreState} from '../runtime';

/** Procedural reactor: every visible surface is geometry or a shader. */
export class CoreScene {
 renderer:T.WebGLRenderer;scene=new T.Scene();camera=new T.PerspectiveCamera(40,1,.1,70);
 composer:EffectComposer;bloom:UnrealBloomPass;output=new OutputPass();resize:ResizeObserver;
 assembly=new T.Group();mechanics:T.Group[]=[];orbits:T.Group[]=[];nodes:T.Mesh[]=[];platform=new T.Group();particles:T.Points;beam:T.Mesh;
 state:CoreState='IDLE';amplitude=0;frame=0;frames=0;time=0;last=0;errorAt=-20;disposed=false;pointer=new T.Vector2();
 constructor(private host:HTMLDivElement){
  this.renderer=new T.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});
  this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));this.renderer.toneMapping=T.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.15;this.renderer.setClearColor(0x05070b);host.appendChild(this.renderer.domElement);
  this.renderer.domElement.setAttribute('aria-label','Gerçek zamanlı 3D ULTRON Core');this.scene.fog=new T.FogExp2(0x08090e,.035);
  this.camera.position.set(0,1.05,11.7);this.camera.lookAt(0,-.15,0);this.scene.add(this.assembly,this.platform);
  const metal=new T.MeshStandardMaterial({color:0x202731,metalness:.78,roughness:.36});
  const silver=new T.MeshStandardMaterial({color:0x83909f,metalness:.85,roughness:.28});
  const black=new T.MeshStandardMaterial({color:0x080c13,metalness:.65,roughness:.5});
  const red=new T.MeshBasicMaterial({color:new T.Color(2.0,.002,.018)}),dim=new T.MeshBasicMaterial({color:0x6b1324});
  const white=new T.MeshBasicMaterial({color:new T.Color(1.5,1.4,1.45)});
  this.scene.add(new T.HemisphereLight(0xb0c4db,0x15040b,1.3));
  for(const [x,y,z,power,color] of [[-4,3,3,70,0xff1538],[4,2,2,55,0xff243c],[0,5,2,95,0xd2e1ff],[0,-2,2,35,0xff1438]]){const l=new T.PointLight(color,power,18,2);l.position.set(x,y,z);this.scene.add(l);}
  const mesh=(geo:T.BufferGeometry,mat:T.Material,parent:T.Object3D=this.scene,x=0,y=0,z=0)=>{const m=new T.Mesh(geo,mat);m.position.set(x,y,z);parent.add(m);return m;};
  const torus=(r:number,t:number,mat:T.Material,parent:T.Object3D=this.assembly)=>mesh(new T.TorusGeometry(r,t,8,160),mat,parent);
  // Three concentric segmented steel assemblies, instanced for bounded draw calls.
  for(let level=0;level<3;level++){
   const g=new T.Group();g.rotation.z=level*.12;this.assembly.add(g);this.mechanics.push(g);
   const r=2.2+level*.22;torus(r,.075,metal,g);torus(r+.09,.012,silver,g);
   const count=48,segments=new T.InstancedMesh(new T.BoxGeometry(.22,.11,.17),level===1?silver:metal,count),slots=new T.InstancedMesh(new T.BoxGeometry(.14,.014,.018),red,count);const temp=new T.Object3D();
   for(let i=0;i<count;i++){const a=i*Math.PI*2/count;temp.position.set(Math.cos(a)*r,Math.sin(a)*r,level*.05);temp.rotation.set(0,0,a+Math.PI/2);temp.updateMatrix();segments.setMatrixAt(i,temp.matrix);temp.position.z+=.1;temp.updateMatrix();slots.setMatrixAt(i,temp.matrix);}g.add(segments,slots);
  }
  // Dense annular energy, shader-created luminous round particles (no bitmap).
  const positions=new Float32Array(2600*3),seeds=new Float32Array(2600);
  for(let i=0;i<2600;i++){const a=i*2.3999632,r=1.91+.12*Math.sin(i*7.1)+.055*Math.cos(i*2.6);positions.set([Math.cos(a)*r,Math.sin(a)*r,.17*Math.sin(i*4.13)],i*3);seeds[i]=(i%97)/97;}
  const geo=new T.BufferGeometry();geo.setAttribute('position',new T.BufferAttribute(positions,3));geo.setAttribute('seed',new T.BufferAttribute(seeds,1));
  const particleMaterial=new T.ShaderMaterial({transparent:true,depthWrite:false,blending:T.AdditiveBlending,uniforms:{time:{value:0},level:{value:0}},vertexShader:`attribute float seed;uniform float time;uniform float level;varying float v;void main(){v=seed;vec3 p=position*(1.+level*.018);p.z+=sin(time*.6+seed*60.)*.04;vec4 mv=modelViewMatrix*vec4(p,1.);gl_Position=projectionMatrix*mv;gl_PointSize=(2.+seed*3.)*(8./-mv.z);}`,fragmentShader:`varying float v;uniform float time;void main(){float d=length(gl_PointCoord-.5)*2.;if(d>1.)discard;float a=pow(1.-d,1.7)*(.65+.35*sin(time*2.+v*80.));gl_FragColor=vec4(3.,.035+v*.12,.11+v*.1,a);}`});
  this.particles=new T.Points(geo,particleMaterial);this.assembly.add(this.particles);torus(1.88,.012,red);torus(2.03,.008,dim);
  for(let i=0;i<5;i++){
   const g=new T.Group();g.rotation.set(.45+i*.43,.45+i*.52,i*.6);this.assembly.add(g);this.orbits.push(g);
   const r=1.65+i*.105;const orbit=torus(r,.008+i*.0015,i===2?white:red,g);orbit.scale.set(1.27,.88,1);
   const node=mesh(new T.SphereGeometry(.037,12,8),i===2?white:red,g,r*1.27,0,0);this.nodes.push(node);
  }
  // Floated steel fragments along the outer radius.
  const fragments=new T.InstancedMesh(new T.BoxGeometry(.09,.2,.11),silver,36),f=new T.Object3D();
  for(let i=0;i<36;i++){const a=i*2.3999,r=2.85+(i%3)*.04;f.position.set(Math.cos(a)*r,Math.sin(a)*r,-.2);f.rotation.set(i*.3,i*.4,a);f.updateMatrix();fragments.setMatrixAt(i,f.matrix);}this.assembly.add(fragments);
  // Thick platform with machined concentric grooves and illuminated channels.
  this.platform.position.y=-2.8;
  for(let i=0;i<4;i++){const r=3.1-i*.28;mesh(new T.CylinderGeometry(r,r+.04,.11,128),i%2?metal:black,this.platform,0,i*.1,0);const ring=torus(r-.06,.025,i===1||i===3?red:silver,this.platform);ring.rotation.x=Math.PI/2;ring.position.y=i*.1+.065;}
  for(let i=0;i<9;i++){const ring=torus(.7+i*.25,.012,i%3===0?red:metal,this.platform);ring.rotation.x=Math.PI/2;ring.position.y=.45;}
  const blocks=new T.InstancedMesh(new T.BoxGeometry(.38,.24,.19),metal,48),b=new T.Object3D();
  for(let i=0;i<48;i++){const a=i*Math.PI/24;b.position.set(Math.cos(a)*2.97,.24,Math.sin(a)*2.97);b.rotation.y=-a;b.updateMatrix();blocks.setMatrixAt(i,b.matrix);}this.platform.add(blocks);
  this.beam=mesh(new T.CylinderGeometry(.055,.27,2.5,32,1,true),new T.MeshBasicMaterial({color:0xff173e,transparent:true,opacity:.16,blending:T.AdditiveBlending,depthWrite:false}),this.scene,0,-1.4,0);
  // Procedural chamber, struts and recesses. No flat background asset.
  mesh(new T.BoxGeometry(15,.18,17),metal,this.scene,0,-3.06,-2);
  mesh(new T.BoxGeometry(14,12,.35),black,this.scene,0,1,-4.2);
  for(const side of [-1,1])for(let i=0;i<3;i++){
   const strut=mesh(new T.BoxGeometry(.42,9,.5),metal,this.scene,side*(4.2+i*.62),1,-1.6-i*.6);strut.rotation.z=side*-.24;
   const rail=mesh(new T.BoxGeometry(.035,2.5,.04),red,this.scene,side*(3.62+i*.63),1.5,-1.28-i*.6);rail.rotation.z=side*-.24;
   mesh(new T.BoxGeometry(.7,.12,6),metal,this.scene,side*(3.5+i*.5),-2.9,-1);
   mesh(new T.BoxGeometry(.025,.012,8),dim,this.scene,side*(3.5+i*.5),-2.95,-.6);
  }
  for(let i=0;i<8;i++){mesh(new T.BoxGeometry(13,.025,.04),dim,this.scene,0,-2.94,1-i*.8);mesh(new T.BoxGeometry(12,.12,.16),metal,this.scene,0,4.6,-i*.8);}
  // Faded floor light: procedural shader disc imitates reflected red spill.
  const glow=mesh(new T.PlaneGeometry(8,8),new T.ShaderMaterial({transparent:true,depthWrite:false,blending:T.AdditiveBlending,vertexShader:`varying vec2 uvv;void main(){uvv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,fragmentShader:`varying vec2 uvv;void main(){float r=length(uvv-.5)*2.;gl_FragColor=vec4(.5,.005,.018,max(0.,1.-r)*.35);}`}),this.scene,0,-2.95,0);glow.rotation.x=-Math.PI/2;
  const target=new T.WebGLRenderTarget(1,1,{type:T.HalfFloatType,samples:4});this.composer=new EffectComposer(this.renderer,target);this.composer.addPass(new RenderPass(this.scene,this.camera));this.bloom=new UnrealBloomPass(new T.Vector2(500,500),.43,.32,1.0);this.composer.addPass(this.bloom);this.composer.addPass(this.output);
  this.resize=new ResizeObserver(()=>{const w=host.clientWidth,h=host.clientHeight;if(!w||!h)return;this.camera.aspect=w/h;this.camera.updateProjectionMatrix();this.renderer.setSize(w,h);this.composer.setSize(w,h);this.bloom.setSize(Math.min(w,720),Math.min(h,600));});this.resize.observe(host);
  host.addEventListener('pointermove',this.move);host.addEventListener('pointerleave',this.leave);this.frame=requestAnimationFrame(this.animate);
 }
 move=(e:PointerEvent)=>{const r=this.host.getBoundingClientRect();this.pointer.set((e.clientX-r.left)/r.width-.5,(e.clientY-r.top)/r.height-.5);};leave=()=>this.pointer.set(0,0);
 setState(state:CoreState,amp:number){if(state==='ERROR'&&this.state!=='ERROR')this.errorAt=this.time;this.state=state;this.amplitude=Math.max(0,Math.min(1,amp));}
 animate=(now:number)=>{if(this.disposed)return;this.frame=requestAnimationFrame(this.animate);const dt=Math.min((now-this.last)/1000,.05);this.last=now;if(document.hidden)return;this.time+=dt;
  const speed={IDLE:.045,LISTENING:.10,THINKING:.25,SPEAKING:.08,WORKING:.19,ERROR:.025}[this.state];
  this.mechanics.forEach((g,i)=>g.rotation.z+=dt*speed*(i%2?-1:1)*(1+i*.2));
  this.orbits.forEach((g,i)=>{g.rotation.z+=dt*speed*(i%2?1:-1)*2;g.rotation.y+=dt*speed*.17;});
  this.assembly.rotation.y=T.MathUtils.lerp(this.assembly.rotation.y,this.pointer.x*.13,.025);this.assembly.rotation.x=T.MathUtils.lerp(this.assembly.rotation.x,this.pointer.y*.06,.025);
  const level=['LISTENING','SPEAKING'].includes(this.state)?this.amplitude:0;this.particles.scale.setScalar(1+level*.035);this.particles.rotation.z+=dt*.025;
  const mat=this.particles.material as T.ShaderMaterial;mat.uniforms.time.value=this.time;mat.uniforms.level.value=level;this.particles.geometry.setDrawRange(0,this.state==='THINKING'?2600:2100);
  (this.beam.material as T.MeshBasicMaterial).opacity=.11+level*.18;this.platform.rotation.y+=dt*speed*.18;
  this.bloom.strength=.4+level*.13+(this.state==='ERROR'?Math.max(0,1-(this.time-this.errorAt)/1.4)*.18:0);
  this.composer.render();this.host.dataset.frames=String(++this.frames);this.host.dataset.state=this.state;this.host.dataset.amplitude=String(this.amplitude);
 };
 dispose(){this.disposed=true;cancelAnimationFrame(this.frame);this.resize.disconnect();this.host.removeEventListener('pointermove',this.move);this.host.removeEventListener('pointerleave',this.leave);const geos=new Set<T.BufferGeometry>(),mats=new Set<T.Material>();this.scene.traverse(o=>{const m=o as T.Mesh;if(m.geometry)geos.add(m.geometry);if(m.material)(Array.isArray(m.material)?m.material:[m.material]).forEach(x=>mats.add(x));if(o instanceof T.InstancedMesh)o.dispose();});geos.forEach(g=>g.dispose());mats.forEach(m=>m.dispose());this.bloom.dispose();this.output.dispose();this.composer.dispose();this.renderer.dispose();this.renderer.domElement.remove();}
}
