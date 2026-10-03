export type V3=[number,number,number];
export type ViewState={explosion:number;selected:number;isolated:boolean;wire:boolean;cut:number|null;camera:V3;target:V3;offsets:V3[];notes:string[]};
export type Project={schema:'ultron-project-v1';name:string;view:ViewState;parts:{name:string;description:string;positions:number[];indices:number[]|null;base:V3;rotation:V3}[]};
const fail=():never=>{throw Error('Proje dosyası geçersiz veya desteklenen sınırları aşıyor.');};
const finite=(v:unknown,limit=10000):v is number=>typeof v==='number'&&Number.isFinite(v)&&Math.abs(v)<=limit;
const vector=(v:unknown):v is V3=>Array.isArray(v)&&v.length===3&&v.every(n=>finite(n));
/** Validate every allocation and transform before replacing the user's current scene. */
export function validateProject(input:unknown):Project{
 const p=input as Project;if(!p||p.schema!=='ultron-project-v1'||typeof p.name!=='string'||p.name.length>200||!Array.isArray(p.parts)||p.parts.length<1||p.parts.length>200)fail();
 let triangles=0,vertices=0;
 for(const part of p.parts){
  if(!part||typeof part.name!=='string'||part.name.length>200||typeof part.description!=='string'||part.description.length>4000||!vector(part.base)||!vector(part.rotation)||!Array.isArray(part.positions)||part.positions.length<9||part.positions.length%3||part.positions.length>6750000||!part.positions.every(n=>finite(n)))fail();
  const count=part.positions.length/3;vertices+=count;
  if(part.indices!==null&&(!Array.isArray(part.indices)||part.indices.length<3||part.indices.length%3||part.indices.length>2250000||!part.indices.every(n=>Number.isInteger(n)&&n>=0&&n<count)))fail();
  if(part.indices===null&&count%3)fail();triangles+=(part.indices?.length??count)/3;
 }
 if(triangles>750000||vertices>2250000)fail();
 const v=p.view;if(!v||!finite(v.explosion,1)||v.explosion<0||!Number.isInteger(v.selected)||v.selected< -1||v.selected>=p.parts.length||typeof v.isolated!=='boolean'||(v.isolated&&v.selected<0)||typeof v.wire!=='boolean'||!(v.cut===null||finite(v.cut,6))||!vector(v.camera)||!vector(v.target)||!Array.isArray(v.offsets)||v.offsets.length!==p.parts.length||!v.offsets.every(vector)||!Array.isArray(v.notes)||v.notes.length!==p.parts.length||!v.notes.every(n=>typeof n==='string'&&n.length<=2000))fail();
 if(Math.hypot(...v.camera.map((n,i)=>n-v.target[i]))<.1)fail();
 return p;
}
