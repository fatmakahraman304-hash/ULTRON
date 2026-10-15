/** Data-only geometry: never execute model output or fetch URLs from it. */
export type Shape='box'|'sphere'|'cylinder'|'cone'|'torus'|'circle'|'plane'|'triangle';
export type Design={name:string;parts:{name:string;shape:Shape;size:[number,number,number];position:[number,number,number];rotation:[number,number,number]}[]};
export function validateDesign(raw:unknown):Design{
 const fail=():never=>{throw Error('Geçerli bir model taslağı üretilemedi. Önceki sahnen korunuyor.');};
 let d:any=raw;
 if(typeof d==='string'){if(d.length>24000)fail();try{d=JSON.parse(d.replace(/^```(?:json)?\s*/,'').replace(/\s*```$/,''));}catch{fail();}}
 const keys=(o:any,allowed:string[])=>o&&typeof o==='object'&&!Array.isArray(o)&&Object.keys(o).every(k=>allowed.includes(k));
 const vec=(v:any,min:number,max:number)=>Array.isArray(v)&&v.length===3&&v.every(n=>typeof n==='number'&&Number.isFinite(n)&&n>=min&&n<=max);
 if(!keys(d,['name','parts'])||typeof d.name!=='string'||!d.name.trim()||d.name.length>100||!Array.isArray(d.parts)||d.parts.length<1||d.parts.length>24)fail();
 for(const p of d.parts)if(!keys(p,['name','shape','size','position','rotation'])||typeof p.name!=='string'||!p.name.trim()||p.name.length>100||!['box','sphere','cylinder','cone','torus','circle','plane','triangle'].includes(p.shape)||!vec(p.size,.05,6)||!vec(p.position,-6,6)||!vec(p.rotation,-6.29,6.29))fail();
 return d;
}
export async function requestDesign(description:string,signal:AbortSignal):Promise<Design>{
 const res=await fetch('/api/scene-design',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({description}),signal});
 if(!res.ok)throw Error('Model taslağı şu anda üretilemiyor. Önceki sahnen korunuyor.');
 const data=await res.json();return validateDesign(data.design);
}
