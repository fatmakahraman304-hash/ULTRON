import {HologramScene} from '../hologram/HologramScene';
import {sceneIntent} from './intents';

declare global {interface Window {ULTRONScene:typeof api}}
function create(options:{host:HTMLElement;open:()=>void;notice:(text:string)=>void}){
 let scene:HologramScene|null=null;
 const file=document.createElement('input');file.type='file';file.accept='.glb';file.hidden=true;options.host.append(file);
 const ensure=()=>{
   options.open();
   if(!scene){scene=new HologramScene(options.host,'#ff3047');scene.onView=v=>{options.host.dataset.scene=JSON.stringify({parts:scene!.list().map(p=>({id:p.id,name:p.name})),selected:v.selected,offsets:v.offsets,rotations:v.rotations,scales:v.scales,removed:v.removed});};}
   return scene;
 };
 let loading=false;
 file.onchange=async()=>{
   const f=file.files?.[0];file.value='';if(!f)return;
   if(!/\.glb$/i.test(f.name)||f.size>30*1024*1024){options.notice('En fazla 30 MB, dokuları gömülü bir GLB seç.');return;}
   loading=true;
   try{await ensure().importGLB(await f.arrayBuffer());options.notice('Modeli sahneye yükledim.');}
   catch{options.notice('Model yüklenemedi. Geçerli, dokuları gömülü ve desteklenen sınırlar içinde bir GLB seç.');}
   finally{loading=false;}
 };
 function handle(text:string,active:boolean){
   const intent=sceneIntent(text,active);if(!intent)return null;
   if(loading)return 'Model yükleniyor; bitmesini bekle.';
   try{
     if(intent.kind==='clarify')return intent.reply;
     const engine=ensure();
     if(intent.kind==='upload'){file.click();return 'Yüklemek için bir GLB dosyası seç.';}
     const reply=engine.command(intent);options.notice(reply);return reply;
   }catch{return '3D sahne açılamadı. WebGL destekli bir tarayıcı gerekiyor.';}
 }
 return {handle,open:()=>{try{ensure()}catch{options.notice('3D sahne açılamadı.')}},upload:()=>file.click(),dispose:()=>{scene?.dispose();file.remove();scene=null;}};
}
const api={create,resolve:sceneIntent};window.ULTRONScene=api;
