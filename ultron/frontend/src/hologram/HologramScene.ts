import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import type { Gesture } from './gestures';
import {validateProject,type Project,type ViewState,type V3} from './project';

export type PartInfo={id:number;name:string;description:string;vertices:number;triangles:number;dimensions:V3;note:string};
type Part=PartInfo & {mesh:THREE.Mesh;base:THREE.Vector3;direction:THREE.Vector3;offset:THREE.Vector3};
export class HologramScene {
  private scene=new THREE.Scene();private group=new THREE.Group();
  private camera=new THREE.PerspectiveCamera(42,1,.05,100);
  private renderer:THREE.WebGLRenderer;private controls:OrbitControls;private observer:ResizeObserver;
  private ray=new THREE.Raycaster();private parts:Part[]=[];private selected=-1;
  private frame=0;private dead=false;private explosion=0;private isolated=false;private wire=false;
  private drag: {id:number;point:THREE.Vector3;offset:THREE.Vector3}|null=null;
  private down:{x:number;y:number}|null=null;private previous:Gesture|null=null;
  private past:ViewState[]=[];private future:ViewState[]=[];private applying=false;private lastEdit='';private lastTime=0;
  private cut:number|null=null;private cutPlane=new THREE.Plane(new THREE.Vector3(-1,0,0),0);
  onView:(view:ViewState,undo:boolean,redo:boolean)=>void=()=>{};
  private view():ViewState{return {explosion:this.explosion,selected:this.selected,isolated:this.isolated,wire:this.wire,cut:this.cut,camera:this.camera.position.toArray() as V3,target:this.controls.target.toArray() as V3,offsets:this.parts.map(p=>p.offset.toArray() as V3),notes:this.parts.map(p=>p.note)};}
  private notify(){this.onView(this.view(),!!this.past.length,!!this.future.length);}
  private checkpoint(key:string){if(this.applying)return;const now=performance.now();if(key!==this.lastEdit||now-this.lastTime>450){this.past.push(this.view());if(this.past.length>60)this.past.shift();}this.lastEdit=key;this.lastTime=now;this.future=[];this.notify();}
  private restore(v:ViewState){this.applying=true;this.stopGesture();this.explosion=v.explosion;this.isolated=v.isolated;this.wireframe(v.wire);this.section(v.cut);this.parts.forEach((p,i)=>{p.offset.fromArray(v.offsets[i]);p.note=v.notes[i];});this.camera.position.fromArray(v.camera);this.controls.target.fromArray(v.target);this.select(v.selected);this.controls.update();this.applying=false;this.onExplosion(this.explosion);this.notify();}
  undo(){const v=this.past.pop();if(!v)return;this.future.push(this.view());this.restore(v);this.lastEdit='';}
  redo(){const v=this.future.pop();if(!v)return;this.past.push(this.view());this.restore(v);this.lastEdit='';}
  section(value:number|null){this.checkpoint('section');this.cut=value;this.cutPlane.constant=value??0;this.parts.forEach(p=>p.mesh.traverse(o=>{const m=(o as THREE.Mesh).material;if(m)for(const mat of Array.isArray(m)?m:[m]){mat.clippingPlanes=value===null?[]:[this.cutPlane];mat.needsUpdate=true;}}));this.notify();}
  annotate(text:string){if(this.selected<0)return;this.checkpoint('note:'+this.selected);this.parts[this.selected].note=text.slice(0,2000);this.onSelect(this.parts[this.selected]);this.notify();}
  project(name:string):Project{return {schema:'ultron-project-v1',name:name.slice(0,200),view:this.view(),parts:this.parts.map(p=>({name:p.name,description:p.description,positions:Array.from(p.mesh.geometry.attributes.position.array),indices:p.mesh.geometry.index?Array.from(p.mesh.geometry.index.array):null,base:p.base.toArray() as V3,rotation:[p.mesh.rotation.x,p.mesh.rotation.y,p.mesh.rotation.z]}))};}
  loadProject(raw:unknown){const project=validateProject(raw);const prepared=project.parts.map(p=>{const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(p.positions,3));if(p.indices)g.setIndex(p.indices);g.computeVertexNormals();return {p,g};});this.clear();prepared.forEach(({p,g})=>this.add(p.name,p.description,g,new THREE.Vector3(...p.base),new THREE.Euler(...p.rotation)));this.restore(project.view);this.past=[];this.future=[];this.notify();return {name:project.name,parts:this.list()};}
  private resources:THREE.Object3D[]=[];
  onSelect:(part:PartInfo|null)=>void=()=>{};onExplosion:(n:number)=>void=()=>{};
  constructor(private host:HTMLElement,private accent:string){
    this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,preserveDrawingBuffer:true});
    this.renderer.localClippingEnabled=true;
    this.renderer.setPixelRatio(Math.min(devicePixelRatio,2));this.renderer.setClearColor(0x060c13,0);
    this.renderer.domElement.setAttribute('aria-label','Etkileşimli üç boyutlu hologram');
    this.host.appendChild(this.renderer.domElement);
    this.camera.position.set(6,4,8);this.controls=new OrbitControls(this.camera,this.renderer.domElement);
    this.controls.enableDamping=true;this.controls.minDistance=3;this.controls.maxDistance=35;
    this.controls.target.set(0,.1,0);this.scene.add(this.group);
    this.scene.add(new THREE.AmbientLight(0x91dbe5,2));
    const light=new THREE.DirectionalLight(0xd5fcff,4);light.position.set(3,5,4);this.scene.add(light);
    const grid=new THREE.GridHelper(18,36,0x1e6270,0x0e2834);grid.position.y=-2.4;this.scene.add(grid);
    for(const r of [2.7,3,3.6]){const ring=new THREE.Mesh(new THREE.TorusGeometry(r,.009,5,100),new THREE.MeshBasicMaterial({color:0x2c9baa,transparent:true,opacity:.5}));ring.rotation.x=Math.PI/2;ring.position.y=-2.39;this.scene.add(ring);}
    this.observer=new ResizeObserver(()=>this.resize());this.observer.observe(host);this.resize();
    const el=this.renderer.domElement;el.addEventListener('pointerdown',this.pointerDown,true);el.addEventListener('pointermove',this.pointerMove);el.addEventListener('pointerup',this.pointerUp);el.addEventListener('pointercancel',this.pointerCancel);
    this.demo('reactor');this.animate();
  }
  private resize(){const {width,height}=this.host.getBoundingClientRect();this.camera.aspect=width/Math.max(1,height);this.camera.updateProjectionMatrix();this.renderer.setSize(width,height);}
  private animate=()=>{if(this.dead)return;this.frame=requestAnimationFrame(this.animate);if(document.hidden)return;this.controls.update();for(const p of this.parts){const goal=p.base.clone().addScaledVector(p.direction,this.explosion*2.5).add(p.offset);p.mesh.position.lerp(goal,.16);}this.renderer.render(this.scene,this.camera);};
  private add(name:string,description:string,geometry:THREE.BufferGeometry,position:THREE.Vector3,rotation?:THREE.Euler){
    name=name.slice(0,200);description=description.slice(0,4000);
    const material=new THREE.MeshStandardMaterial({color:0x214957,emissive:0x12667b,emissiveIntensity:.3,metalness:.65,roughness:.28,transparent:true,opacity:.85,side:THREE.DoubleSide});
    const mesh=new THREE.Mesh(geometry,material);mesh.position.copy(position);if(rotation)mesh.rotation.copy(rotation);
    const edges=new THREE.LineSegments(new THREE.EdgesGeometry(geometry,28),new THREE.LineBasicMaterial({color:0x67edff,transparent:true,opacity:.7}));mesh.add(edges);
    this.group.add(mesh);const id=this.parts.length;
    const direction=position.length()>.1?position.clone().normalize():new THREE.Vector3();
    const bounds=geometry.clone().applyMatrix4(new THREE.Matrix4().makeRotationFromEuler(mesh.rotation));bounds.computeBoundingBox();const dimensions=bounds.boundingBox!.getSize(new THREE.Vector3()).toArray() as V3;bounds.dispose();
    this.parts.push({id,name,description,dimensions,note:'',mesh,base:position.clone(),direction,offset:new THREE.Vector3(),vertices:geometry.attributes.position.count,triangles:(geometry.index?.count??geometry.attributes.position.count)/3});mesh.userData.part=id;
  }
  private disposeObject(obj:THREE.Object3D){obj.traverse(o=>{const m=o as THREE.Mesh;if(m.geometry)m.geometry.dispose();if(m.material){for(const mat of Array.isArray(m.material)?m.material:[m.material]){for(const value of Object.values(mat))if(value instanceof THREE.Texture)value.dispose();mat.dispose();}}});}
  private clear(){this.stopGesture();this.resources.forEach(o=>this.disposeObject(o));this.resources=[];this.disposeObject(this.group);this.group.clear();this.parts=[];this.past=[];this.future=[];this.lastEdit="";this.cut=null;this.renderer.clippingPlanes=[];this.wire=false;this.selected=-1;this.explosion=0;this.isolated=false;this.onSelect(null);this.onExplosion(0);}
  demo(kind:'reactor'|'arm'){
    this.clear();
    if(kind==='reactor'){
      this.add('Enerji çekirdeği','Kavramsal modelin merkez küresi. Gerçek bir reaktör veya çalışan enerji sistemi değildir.',new THREE.IcosahedronGeometry(.65,2),new THREE.Vector3());
      for(let i=0;i<3;i++)this.add(['İç alan halkası','Orta stabilizasyon halkası','Dış koruma halkası'][i],'Ayrı bir geometrik parça. Çekirdeği çevreleyen örnek halka.',new THREE.TorusGeometry(1+i*.32,.11,12,64),new THREE.Vector3(0,(i-1)*.6,0),new THREE.Euler(Math.PI/2,0,0));
      for(let i=0;i<8;i++){const a=i*Math.PI/4;this.add(`Soğutucu segment ${i+1}`,'Halka çevresinde konumlandırılmış kavramsal soğutucu modülü.',new THREE.BoxGeometry(.3,1.05,.4),new THREE.Vector3(Math.cos(a)*1.6,0,Math.sin(a)*1.6),new THREE.Euler(0,-a,0));}
      this.add('Üst kapak','Bağımsız üst muhafaza.',new THREE.CylinderGeometry(.9,1.1,.22,32),new THREE.Vector3(0,1.05,0));
      this.add('Alt bağlantı','Bağımsız taban ve bağlantı modülü.',new THREE.CylinderGeometry(1.1,.85,.3,32),new THREE.Vector3(0,-1.1,0));
    }else{
      const items:[string,number,number,number,number,number,number][]=[['Omuz yuvası',0,1.5,0,1.25,.55,1.1],['Üst kol dış kabuğu',0,.7,0,.75,1.1,.7],['Dirsek mafsalı',0,-.05,0,.85,.4,.8],['Ön kol gövdesi',0,-.65,0,.65,.85,.65],['Bilek halkası',0,-1.2,0,.75,.2,.7],['Avuç plakası',0,-1.6,0,.8,.55,.25]];
      for(const [n,x,y,z,w,h,d] of items)this.add(n,'Parçalara ayrılabilen örnek robot kolu. Ölçüler model birimleridir; mühendislik doğrulaması yapılmamıştır.',new THREE.BoxGeometry(w,h,d),new THREE.Vector3(x,y,z));
      for(let i=0;i<4;i++)this.add(`Parmak ${i+1}`,'Bağımsız parmak segmenti.',new THREE.BoxGeometry(.13,.42,.2),new THREE.Vector3((i-1.5)*.2,-2.08,0));
      this.add('Başparmak','Bağımsız başparmak segmenti.',new THREE.BoxGeometry(.16,.45,.2),new THREE.Vector3(-.55,-1.7,0),new THREE.Euler(0,0,-.5));
    }
    this.home();this.notify();return this.list();
  }
  list(){return this.parts.map(({id,name,description,vertices,triangles,dimensions,note})=>({id,name,description,vertices,triangles,dimensions,note}));}
  async importGLB(buffer:ArrayBuffer){
    const manager=new THREE.LoadingManager();manager.setURLModifier(url=>{if(url.startsWith('blob:')||url.startsWith('data:'))return url;throw Error('Model dış dosyalar içeriyor. Dokuları gömülü tek bir GLB kullanın.');});
    const gltf=await new GLTFLoader(manager).parseAsync(buffer,'');
    if(this.dead){this.disposeObject(gltf.scene);return [];}
    const meshes:THREE.Mesh[]=[];let triangles=0;
    gltf.scene.updateMatrixWorld(true);gltf.scene.traverse(o=>{if((o as THREE.Mesh).isMesh){const m=o as THREE.Mesh;meshes.push(m);triangles+=(m.geometry.index?.count??m.geometry.attributes.position.count)/3;}});
    if(!meshes.length||meshes.length>200||triangles>750000||meshes.some(m=>(m as THREE.SkinnedMesh).isSkinnedMesh)){this.disposeObject(gltf.scene);throw Error('En fazla 200 statik parça ve 750.000 üçgen içeren bir GLB seçin.');}
    const box=new THREE.Box3().setFromObject(gltf.scene),center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3());const scale=3.8/Math.max(size.x,size.y,size.z,.001);
    this.clear();
    for(const mesh of meshes){const geometry=mesh.geometry.clone().applyMatrix4(mesh.matrixWorld);geometry.translate(-center.x,-center.y,-center.z);geometry.scale(scale,scale,scale);geometry.computeBoundingBox();const local=geometry.boundingBox!.getCenter(new THREE.Vector3());geometry.translate(-local.x,-local.y,-local.z);this.add(mesh.name||`Parça ${this.parts.length+1}`,'İçe aktarılan model geometrisi. İşlev ve malzeme bilgisi dosyadan doğrulanmadı.',geometry,local);}
    this.disposeObject(gltf.scene);this.home();this.notify();return this.list();
  }
  explode(amount:number){this.checkpoint('explode');const next=THREE.MathUtils.clamp(amount,0,1);const ratio=(1+next*.8)/(1+this.explosion*.8);this.camera.position.sub(this.controls.target).multiplyScalar(ratio).clampLength(3,35).add(this.controls.target);this.explosion=next;if(next===0)this.parts.forEach(p=>p.offset.set(0,0,0));this.onExplosion(this.explosion);this.notify();}
  select(id:number){this.selected=id;for(const p of this.parts){const m=p.mesh.material as THREE.MeshStandardMaterial;m.color.set(p.id===id?this.accent:0x214957);m.emissive.set(p.id===id?this.accent:0x12667b);m.emissiveIntensity=p.id===id?.5:.3;p.mesh.visible=!this.isolated||id===p.id;}this.onSelect(this.parts[id]??null);this.notify();}
  isolate(value:boolean){this.checkpoint('isolate');this.isolated=value;this.select(this.selected);}
  wireframe(value:boolean){this.checkpoint('wire');this.wire=value;this.parts.forEach(p=>(p.mesh.material as THREE.MeshStandardMaterial).wireframe=value);this.notify();}
  home(){this.controls.target.set(0,0,0);this.camera.position.set(6,4,8).multiplyScalar((1+this.explosion*.8)/Math.min(1,this.camera.aspect));this.controls.update();}
  reset(){this.checkpoint('reset');this.applying=true;this.parts.forEach(p=>p.offset.set(0,0,0));this.explode(0);this.isolated=false;this.select(-1);this.home();this.section(null);this.wireframe(false);this.applying=false;this.notify();}
  focus(){const p=this.parts[this.selected];if(!p)return;this.controls.target.copy(p.mesh.position);this.camera.position.copy(p.mesh.position).add(new THREE.Vector3(2,1.5,3));this.controls.update();}
  private hit(x:number,y:number){this.ray.setFromCamera(new THREE.Vector2(x*2-1,1-y*2),this.camera);return this.ray.intersectObjects(this.parts.filter(p=>p.mesh.visible).map(p=>p.mesh),false).find(hit=>this.cut===null||this.cutPlane.distanceToPoint(hit.point)>=0);}
  private planePoint(x:number,y:number){this.ray.setFromCamera(new THREE.Vector2(x*2-1,1-y*2),this.camera);const normal=this.camera.getWorldDirection(new THREE.Vector3());const point=this.parts[this.selected]?.mesh.position??new THREE.Vector3();return this.ray.ray.intersectPlane(new THREE.Plane().setFromNormalAndCoplanarPoint(normal,point),new THREE.Vector3());}
  private startDrag(x:number,y:number){const hit=this.hit(x,y);if(!hit)return false;this.checkpoint('drag');this.select(hit.object.userData.part);const point=this.planePoint(x,y);if(point)this.drag={id:this.selected,point,offset:this.parts[this.selected].offset.clone()};return true;}
  private moveDrag(x:number,y:number){if(!this.drag)return;const point=this.planePoint(x,y);if(point){const delta=point.sub(this.drag.point);delta.clampLength(0,8);this.parts[this.drag.id].offset.copy(this.drag.offset).add(delta);}}
  private xy(e:PointerEvent){const r=this.renderer.domElement.getBoundingClientRect();return {x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height};}
  private pointerDown=(e:PointerEvent)=>{this.down={x:e.clientX,y:e.clientY};const p=this.xy(e);if(e.shiftKey&&this.startDrag(p.x,p.y)){this.controls.enabled=false;this.renderer.domElement.setPointerCapture(e.pointerId);}};
  private pointerMove=(e:PointerEvent)=>{if(this.drag){const p=this.xy(e);this.moveDrag(p.x,p.y);}};
  private pointerUp=(e:PointerEvent)=>{if(this.down&&Math.hypot(e.clientX-this.down.x,e.clientY-this.down.y)<5){const p=this.xy(e),hit=this.hit(p.x,p.y);if(hit)this.select(hit.object.userData.part);}this.pointerCancel();};
  private pointerCancel=()=>{this.drag=null;this.down=null;this.controls.enabled=true;};
  gesture(g:Gesture){const prev=this.previous;if(g.kind==='idle'){this.stopGesture();return;}this.controls.enabled=false;
    if(g.kind==='grab'){if(prev?.kind!=='grab')this.startDrag(g.x,g.y);else this.moveDrag(g.x,g.y);}
    else{this.drag=null;if(prev?.kind===g.kind){if(g.kind==='spread')this.explode(this.explosion+(g.distance-prev.distance)*2.5);if(g.kind==='zoom')this.camera.position.sub(this.controls.target).multiplyScalar(THREE.MathUtils.clamp(1-(g.distance-prev.distance)*2,.8,1.2)).clampLength(3,35).add(this.controls.target);if(g.kind==='rotate'){const offset=this.camera.position.clone().sub(this.controls.target);const spherical=new THREE.Spherical().setFromVector3(offset);spherical.theta-=(g.x-prev.x)*5;spherical.phi=THREE.MathUtils.clamp(spherical.phi+(g.y-prev.y)*3,.15,Math.PI-.15);this.camera.position.copy(this.controls.target).add(new THREE.Vector3().setFromSpherical(spherical));}}}
    this.previous=g;
  }
  stopGesture(){this.previous=null;this.drag=null;this.controls.enabled=true;}
  snapshot(){this.renderer.render(this.scene,this.camera);return this.renderer.domElement.toDataURL('image/png');}
  manifest(){return {schema:'ultron-hologram-view-v1',units:'normalized model units',explosion:this.explosion,camera:this.camera.position.toArray(),target:this.controls.target.toArray(),parts:this.parts.map(p=>({name:p.name,base:p.base.toArray(),offset:p.offset.toArray(),vertices:p.vertices,triangles:p.triangles}))};}
  dispose(){this.dead=true;cancelAnimationFrame(this.frame);this.observer.disconnect();this.controls.dispose();this.disposeObject(this.scene);this.resources.forEach(o=>this.disposeObject(o));const el=this.renderer.domElement;el.removeEventListener('pointerdown',this.pointerDown,true);el.removeEventListener('pointermove',this.pointerMove);el.removeEventListener('pointerup',this.pointerUp);el.removeEventListener('pointercancel',this.pointerCancel);this.renderer.dispose();el.remove();}
}
