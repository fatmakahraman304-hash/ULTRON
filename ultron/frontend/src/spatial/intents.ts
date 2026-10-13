/** Deliberate UI-only commands. No tool, file deletion or model API invocation. */
export type SceneIntent =
 | {kind:'create';model:'engine'|'arm'|'reactor'|'cube'|'sphere'}
 | {kind:'move'|'rotate';axis:'x'|'y'|'z';amount:number;target:string}
 | {kind:'scale';factor:number;target:string}
 | {kind:'remove'|'select';target:string}
 | {kind:'undo'|'redo'|'home'|'upload'|'reset'}
 | {kind:'clarify';reply:string};
export const normalize=(s:string)=>s.toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i').replace(/\s+/g,' ').trim();
export function sceneIntent(raw:string,active=false):SceneIntent|null {
 let t=normalize(raw).replace(/[.!?]+$/,'').replace(/^ultron[, ]+/,'').replace(/^lutfen /,'').replace(/ lutfen$/,'');
 t=t.replace(/([0-9]+(?:[.,][0-9]+)?) derece (saga|sola)/,'$2 $1 derece').replace(/([xyz] ekseninde) ([0-9]+(?:[.,][0-9]+)?) derece/,'$2 derece $1');
 if(!t||t.length>240||/["“”]/.test(t)||/\b(?:nasil|neden|hakkinda|demek|yapma|silme|tasima|dondurme|gosterme|istemiyorum)\b/.test(t))return null;
 const create=t.match(/^(?:bana )?(?:bir )?(motor(?:un|u)?|robot kol(?:u|unun|unu)?|enerji cekirdeg(?:i|inin|ini)|kup(?:un|u)?|kure(?:nin|yi)?)\s*(?:(?:3d|3b|uc boyutlu)\s*)?(?:model(?:i|ini|ni)\s*)?(?:goster|olustur|ac|getir|ekle)$/);
 if(create){const m=create[1];return {kind:'create',model:m.startsWith('motor')?'engine':m.startsWith('robot')?'arm':m.startsWith('enerji')?'reactor':m.startsWith('kup')?'cube':'sphere'};}
 if(/(?:3d|3b|uc boyutlu) model(?:i|ini|ni)? (?:goster|olustur|ekle)$/.test(t))return {kind:'clarify',reply:'Bu model hazır kütüphanede yok. Bir GLB dosyası yükleyebilir veya motor, robot kolu, küp ya da küre isteyebilirsin.'};
 if(!active)return null;
 t=t.replace(/^(?:(onu|bunu|sunu) )?(?:kaldir|tasi) (sag |sol )?kenara$/,(_m,object,side)=>`${object?object+' ':''}${side||''}kenara al`);
 if(/^(?:bir |3d |3b )?(?:model|glb)(?:i)? (?:yukle|ice aktar)$/.test(t))return {kind:'upload'};
 if(/^(?:sahneyi |modeli )?sifirla$/.test(t))return {kind:'reset'};
 if(t==='geri al')return {kind:'undo'};
 if(t==='ileri al')return {kind:'redo'};
 if(/^(?:modeli |gorunumu )?(?:ortala|merkeze al|odaklan)$/.test(t))return {kind:'home'};
 const prefix='(?:(onu|bunu|sunu|modeli|motoru|nesneyi|tamamini|hepsini|secili parcayi|[a-z0-9 ]+? parcasi(?:ni)?|piston(?:u| [1-4])?) )?';
 let m=t.match(new RegExp('^'+prefix+'(?:biraz )?(saga|sola|yukari|asagi|one|arkaya)(?: ([0-9]+(?:[.,][0-9]+)?) birim)? (?:tasi|kaydir|gotur|al|kaldir|indir)$'));
 if(m){const value=m[3]?Number(m[3].replace(',','.')):1;if(!(value>0&&value<=8))return {kind:'clarify',reply:'Tek komutta 0 ile 8 arasında bir model birimi kullanabilirim.'};const dir=m[2];return {kind:'move',axis:/saga|sola/.test(dir)?'x':/yukari|asagi/.test(dir)?'y':'z',amount:value*(/sola|asagi|arkaya/.test(dir)?-1:1),target:m[1]||''};}
 // Non-capturing grammar below keeps target and amount unambiguous.
 const target='(?:(onu|bunu|sunu|modeli|motoru|nesneyi|tamamini|hepsini|secili parcayi|piston(?:u| [1-4])?) )?';
 m=t.match(new RegExp('^'+target+'(?:(sag|sol) )?kenara (?:al|tasi|koy|kaldir)$'));
 if(m)return {kind:'move',axis:'x',amount:m[2]==='sol'?-2:2,target:m[1]||''};
 m=t.match(new RegExp('^'+target+'(?:(saga|sola) )?(?:([0-9]+(?:[.,][0-9]+)?) derece )?(?:([xyz]) ekseninde )?(?:dondur|cevir)$'));
 if(m){const value=m[3]?Number(m[3].replace(',','.')):45;if(!(value>0&&value<=360))return {kind:'clarify',reply:'Döndürme açısını 0 ile 360 derece arasında söyle.'};return {kind:'rotate',axis:(m[4] as 'x'|'y'|'z')||'y',amount:value*(m[2]==='sola'?-1:1),target:m[1]||''};}
 m=t.match(new RegExp('^'+target+'(?:biraz )?(buyut|kucult)$'));
 if(m)return {kind:'scale',factor:m[2]==='buyut'?1.25:.8,target:m[1]||''};
 m=t.match(new RegExp('^'+target+'(?:yok et|sil|sahneden (?:sil|kaldir))$'));
 if(m)return {kind:'remove',target:m[1]||''};
 if(new RegExp('^'+target+'kaldir$').test(t))return {kind:'clarify',reply:'Yukarı mı taşıyayım, yoksa sahneden mi sileyim?'};
 if(new RegExp('^'+target+'tasi$').test(t))return {kind:'clarify',reply:'Hangi yöne taşıyayım: sağa, sola, yukarı, aşağı, öne veya arkaya?'};
 m=t.match(/^(?:parca )?(.{1,60}) sec$/);
 if(m)return {kind:'select',target:m[1]};
 return null;
}
