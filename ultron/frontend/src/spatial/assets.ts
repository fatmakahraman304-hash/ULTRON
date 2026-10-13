export type Asset={id:string;name:string;source:string;license:string;authors:string};
export async function findAsset(query:string,signal:AbortSignal):Promise<{asset:Asset;buffer:ArrayBuffer}>{
 const response=await fetch('/api/scene-assets?query='+encodeURIComponent(query),{credentials:'include',signal});
 if(!response.ok)throw Error('Model kaynağına şu anda ulaşılamıyor. Önceki sahnen korunuyor.');
 const data=await response.json();const asset:Asset=data.items?.[0];
 if(!asset)throw Error('Açık lisanslı katalogda eşleşen model bulunamadı. İngilizce adını deneyebilir veya tariften model oluşturmamı isteyebilirsin.');
 if(!/^[A-Za-z0-9_-]{1,100}$/.test(asset.id)||asset.source!=='https://polyhaven.com/a/'+asset.id||asset.license!=='CC0-1.0'||typeof asset.name!=='string'||asset.name.length>150)throw Error('Model kaynağı doğrulanamadı.');
 const res=await fetch('/api/scene-assets/'+encodeURIComponent(asset.id),{credentials:'include',signal});
 if(!res.ok||!res.body)throw Error('Model indirilemedi. Önceki sahnen korunuyor.');
 const reader=res.body.getReader(),chunks:Uint8Array[]=[];let total=0;
 try{while(true){const {value,done}=await reader.read();if(done)break;total+=value.byteLength;if(total>30*1024*1024)throw Error('Model 30 MB sınırını aşıyor.');chunks.push(value);}}
 catch(e){await reader.cancel();throw e;}
 const bytes=new Uint8Array(total);let offset=0;for(const part of chunks){bytes.set(part,offset);offset+=part.byteLength;}
 return {asset,buffer:bytes.buffer};
}
export const assetCredit=(asset:Asset)=>`${asset.name} — Poly Haven, CC0. ${asset.authors||''} ${asset.source}`;
