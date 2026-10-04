import * as T from 'three';
import {EffectComposer} from 'three/examples/jsm/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/examples/jsm/postprocessing/RenderPass.js';
import {UnrealBloomPass} from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import {OutputPass} from 'three/examples/jsm/postprocessing/OutputPass.js';
import type {CoreState} from '../runtime';

export class CoreScene {
 renderer:T.WebGLRenderer;scene=new T.Scene();camera=new T.PerspectiveCamera(39,1,.1,60);group=new T.Group();rings:T.Group[]=[];
 composer:EffectComposer;bloom:UnrealBloomPass;frame=0;resize:ResizeObserver;state:CoreState='IDLE';amplitude=0;last=0;time=0;pointer=new T.Vector2();energy:T.Mesh;scan:T.Mesh;particles:T.Points;disposed=false;errorAt=-100;frames=0;
 constructor(private host:HTMLDivElement){
  this.renderer=new T.WebGLRenderer({antialias:true,alpha:true,powerPreference:'high-performance'});this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));this.renderer.setClearColor(0,0);this.renderer.toneMapping=T.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.3;host.appendChild(this.renderer.domElement);
  this.renderer.domElement.setAttribute('aria-label','Gerçek zamanlı 3D ULTRON Core');this.camera.position.set(0,1.2,8.6);this.camera.lookAt(0,0,0);this.scene.add(this.group);
  this.scene.add(new T.AmbientLight(0x8392aa,1.2));const light=new T.PointLight(0xff1530,45,15);light.position.set(1,2,3);this.scene.add(light);const white=new T.DirectionalLight(0xdce6ff,4);white.position.set(-3,4,2);this.scene.add(white);
  const metal=new T.MeshStandardMaterial({color:0x242832,metalness:.85,roughness:.27,emissive:0x42040b,emissiveIntensity:.3});
  const red=new T.MeshBasicMaterial({color:new T.Color(3.2,.045,.13)});const pale=new T.MeshBasicMaterial({color:new T.Color(2.8,1.3,1.5)});
  this.energy=new T.Mesh(new T.IcosahedronGeometry(.63,4),new T.MeshStandardMaterial({color:0x680716,emissive:0xff1835,emissiveIntensity:2.2,metalness:.3,roughness:.25}));this.group.add(this.energy);
  const shell=new T.Mesh(new T.IcosahedronGeometry(.96,1),new T.MeshBasicMaterial({color:0xff5369,wireframe:true,transparent:true,opacity:.4}));this.group.add(shell);
  for(let i=0;i<18;i++){const a=i*Math.PI*2/18;const plate=new T.Mesh(new T.SphereGeometry(1.02,12,8,a,.23,.42,2.3),metal);this.group.add(plate);}
  for(let i=0;i<5;i++){
   const g=new T.Group(),r=1.22+i*.23;g.rotation.set(.4+i*.53,i*.7,.3+i*.6);
   g.add(new T.Mesh(new T.TorusGeometry(r,.04,8,128),metal));
   for(let j=0;j<3;j++){const arc=new T.Mesh(new T.TorusGeometry(r,.012,6,64,1.35),j===1?pale:red);arc.rotation.z=j*2.1;g.add(arc);}
   for(let j=0;j<16;j++){const f=new T.Mesh(new T.BoxGeometry(.065,.018,.09),j%5===0?pale:metal);f.position.set(Math.cos(j*Math.PI/8)*r,Math.sin(j*Math.PI/8)*r,0);f.rotation.z=j*Math.PI/8;g.add(f);}
   this.group.add(g);this.rings.push(g);
  }
  const vertices=new Float32Array(720*3);for(let i=0;i<720;i++){const a=i*2.3999632,z=1-2*(i+.5)/720,r=1.85+(i%13)/30;vertices.set([r*Math.sqrt(1-z*z)*Math.cos(a),r*z,r*Math.sqrt(1-z*z)*Math.sin(a)],i*3);}
  const geo=new T.BufferGeometry();geo.setAttribute('position',new T.BufferAttribute(vertices,3));this.particles=new T.Points(geo,new T.PointsMaterial({color:0xff4c61,size:.018,transparent:true,opacity:.65,blending:T.AdditiveBlending,depthWrite:false}));this.group.add(this.particles);
  this.scan=new T.Mesh(new T.TorusGeometry(1.02,.008,6,100),new T.MeshBasicMaterial({color:0xff7d90,transparent:true,opacity:.55}));this.scan.rotation.x=Math.PI/2;this.group.add(this.scan);
  const base=new T.Group();base.position.y=-2.05;base.rotation.x=Math.PI/2;for(let i=0;i<4;i++){base.add(new T.Mesh(new T.TorusGeometry(1.2+i*.35,.025,8,120),i%2?metal:red));}this.scene.add(base);
  const beam=new T.Mesh(new T.CylinderGeometry(.022,.12,4.5,16),new T.MeshBasicMaterial({color:0xff283c,transparent:true,opacity:.22,blending:T.AdditiveBlending,depthWrite:false}));this.scene.add(beam);
  this.composer=new EffectComposer(this.renderer);this.composer.addPass(new RenderPass(this.scene,this.camera));this.bloom=new UnrealBloomPass(new T.Vector2(400,400),.85,.55,.65);this.composer.addPass(this.bloom);this.composer.addPass(new OutputPass());
  this.resize=new ResizeObserver(()=>{const w=host.clientWidth,h=host.clientHeight;if(!w||!h)return;this.camera.aspect=w/h;this.camera.updateProjectionMatrix();this.renderer.setSize(w,h);this.composer.setSize(w,h);this.bloom.setSize(Math.min(w,640),Math.min(h,640));});this.resize.observe(host);
  host.addEventListener('pointermove',this.move);host.addEventListener('pointerleave',this.leave);this.frame=requestAnimationFrame(this.animate);
 }
 move=(e:PointerEvent)=>{const b=this.host.getBoundingClientRect();this.pointer.set((e.clientX-b.left)/b.width-.5,(e.clientY-b.top)/b.height-.5);};leave=()=>this.pointer.set(0,0);
 setState(state:CoreState,amp:number){if(state==='ERROR'&&this.state!=='ERROR')this.errorAt=this.time;this.state=state;this.amplitude=Math.min(1,Math.max(0,amp));}
 animate=(now:number)=>{if(this.disposed)return;this.frame=requestAnimationFrame(this.animate);const dt=Math.min((now-this.last)/1000,.05);this.last=now;if(document.hidden)return;this.time+=dt;
  const speed={IDLE:.12,LISTENING:.28,THINKING:.66,SPEAKING:.2,WORKING:.48,ERROR:.08}[this.state];
  this.rings.forEach((r,i)=>{r.rotation.z+=dt*speed*(i%2?-1:1)*(1+i*.19);r.rotation.y+=dt*speed*.19;});
  this.group.rotation.y=T.MathUtils.lerp(this.group.rotation.y,this.pointer.x*.18,.04);this.group.rotation.x=T.MathUtils.lerp(this.group.rotation.x,this.pointer.y*.1,.04);
  const pulse=1+.025*Math.sin(this.time*2)+(['LISTENING','SPEAKING'].includes(this.state)?this.amplitude*.22:0)+(this.state==='ERROR'?Math.max(0,1-(this.time-this.errorAt)/1.5)*.12:0);
  this.energy.scale.setScalar(pulse);(this.energy.material as T.MeshStandardMaterial).emissiveIntensity=1.4+this.amplitude*2;
  this.particles.rotation.y+=dt*.045;this.particles.geometry.setDrawRange(0,this.state==='THINKING'?720:480);this.scan.position.y=Math.sin(this.time*.8)*.8;this.scan.scale.setScalar(Math.sqrt(1-this.scan.position.y**2));
  this.composer.render();this.frames++;this.host.dataset.frames=String(this.frames);this.host.dataset.state=this.state;
 };
 dispose(){this.disposed=true;cancelAnimationFrame(this.frame);this.resize.disconnect();this.host.removeEventListener('pointermove',this.move);this.host.removeEventListener('pointerleave',this.leave);const materials=new Set<T.Material>();this.scene.traverse(o=>{const mesh=o as T.Mesh;if(mesh.geometry)mesh.geometry.dispose();if(mesh.material)(Array.isArray(mesh.material)?mesh.material:[mesh.material]).forEach(m=>materials.add(m));});materials.forEach(m=>m.dispose());this.bloom.dispose();this.composer.dispose();this.renderer.dispose();this.renderer.domElement.remove();}
}
