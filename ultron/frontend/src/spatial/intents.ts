/** Explicit scene intentions; geometry synthesis is data-only, never OS tools. */
export type SceneIntent =
 | {kind:'design';description:string}
 | {kind:'find';query:string}
 | {kind:'create';model:'engine'|'arm'|'reactor'|'cube'|'sphere'|'circle'|'square'|'triangle'|'cylinder'|'cone'|'torus'}
 | {kind:'move'|'rotate';axis:'x'|'y'|'z';amount:number;target:string}
 | {kind:'scale';factor:number;target:string}
 | {kind:'remove'|'select';target:string}
 | {kind:'undo'|'redo'|'home'|'upload'|'reset'}
 | {kind:'clarify';reply:string};
export const normalize=(s:string)=>s.toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i').replace(/\s+/g,' ').trim();
/** Folded shape nouns the cloud shape library builds instantly. Keep in sync with shape_library.CATALOG (test enforced). */
export const SHAPE_PREFIX_NOUNS=['notebook','kure','silindir','koni','simit','yuzuk','piramit','yildiz','kalp','helis','sarmal','spiral','girdap','galaksi','agac','kardan adam','robot','roket','uzay araci','araba','otomobil','sandalye','koltuk','merdiven','gunes sistemi','solar system','gezegenler','satur','dunya','ucak','cicek','papatya','kale','mantar','fincan','kupa','bardak','laptop','bilgisayar','telefon','kitap','lamba','abajur','kopru','kule','gokdelen','eyfel','gemi','tekne','disli','cark','elmas','mucevher','kum saati','piyon','satranc','kulube'];
export const SHAPE_WORD_NOUNS=['kup','kutu','halka','top','dna','ev','ok','masa','atom','saat','mum','arac','cube','box','sphere','ball','cylinder','cone','torus','ring','pyramid','star','heart','helix','galaxy','house','tree','snowman','rocket','car','table','chair','stairs','earth','globe','airplane','plane','flower','arrow','castle','mushroom','cup','mug','phone','book','candle','lamp','bridge','tower','skyscraper','eiffel','ship','boat','gear','clock','diamond','hourglass','pawn'];
const SHAPE_REQUEST=new RegExp('^(?:bana )?(?:bir )?((?:[0-9]{1,2} |[a-z]+ ){0,2}(?:(?:'+SHAPE_PREFIX_NOUNS.join('|')+')[a-z]*|(?:'+SHAPE_WORD_NOUNS.join('|')+')(?:i|in|e|de|den|u|un|ler|lar|im)?)) (?:modeli |hologrami )?(?:ciz|olustur|yarat)$');
export function sceneIntent(raw:string,active=false):SceneIntent|null {
 let t=normalize(raw).replace(/[.!?]+$/,'').replace(/^(?:ultron|golge)[, ]+/,'').replace(/^lutfen /,'').replace(/ lutfen$/,'');
 t=t.replace(/([0-9]+(?:[.,][0-9]+)?) derece (saga|sola)/,'$2 $1 derece').replace(/([xyz] ekseninde) ([0-9]+(?:[.,][0-9]+)?) derece/,'$2 derece $1');
 if(!t||t.length>240||/["“”]/.test(t)||/\b(?:nasil|neden|hakkinda|demek|yapma|silme|tasima|dondurme|gosterme|istemiyorum)\b/.test(t))return null;
 const find=t.match(/^(?:bana )?(?:bir )?(?:(?:internetten|webden) )?(.{2,160}?) (?:(?:3d |3b )?model(?:i|ini|ni)? )?(?:bul getir|ara getir|bul|indir)$/);
 if(find&&(active||/\b(?:model|modeli|modelini|internetten|webden)\b/.test(t)))return {kind:'find',query:find[1].replace(/ (?:3d|3b)$/,'')};
 const shape=t.match(/^(?:bir )?(daire|cember|kare|ucgen|silindir|koni|halka)(?:yi|yu|i|u)?(?: (?:3d |3b )?(?:modelini |seklini )?(?:yap|ciz|olustur|goster|ekle|getir))?$/);
 if(shape)return {kind:'create',model:({daire:'circle',cember:'torus',kare:'square',ucgen:'triangle',silindir:'cylinder',koni:'cone',halka:'torus'} as const)[shape[1] as 'daire']};
 const create=t.match(/^(?:bana )?(?:bir )?(motor(?:un|u)?|robot kol(?:u|unun|unu)?|enerji cekirdeg(?:i|inin|ini)|kup(?:un|u)?|kure(?:nin|yi)?)\s*(?:(?:3d|3b|uc boyutlu)\s*)?(?:model(?:i|ini|ni)\s*)?(?:goster|olustur|ac|getir|ekle)$/);
 if(create){const m=create[1];return {kind:'create',model:m.startsWith('motor')?'engine':m.startsWith('robot')?'arm':m.startsWith('enerji')?'reactor':m.startsWith('kup')?'cube':'sphere'};}
 // Known library shapes (see cloud shape_library.py) work without the word "model"; "hologram" opens any request.
 const holo=t.match(/^(?:bana )?(?:bir )?hologram(?:da|a|imde|inde)? (?:bir )?(.{2,100}?) (?:goster|ciz|olustur|yarat|yap)$/);
 if(holo&&!/\b(?:dosya|uygulama|kod|sifre|hesap)\b/.test(holo[1]))return {kind:'design',description:holo[1].replace(/ hologram(?:i|ini)?$/,'')};
 const lib=t.match(SHAPE_REQUEST);
 if(lib)return {kind:'design',description:lib[1]};
 const design=t.match(/^(?:bana )?(?:bir )?(.{2,160}?) (?:3d |3b |uc boyutlu )?model(?:i|ini|ni)? (?:yap|ciz|goster|olustur|ekle|bul getir)$/);
 if(design)return /^(?:onu|bunu|sunu)$/.test(design[1])?{kind:'clarify',reply:'Hangi nesneyi oluşturmamı istiyorsun?'}:{kind:'design',description:design[1]};
 if(active){const free=t.match(/^(?:bana )?(?:bir )?(.{2,160}?) (?:modelini yap|olustur|ciz|yap|bul getir)$/);if(free&&!/\b(?:dosya|uygulama|kod|sifre|hesap)\b/.test(free[1]))return {kind:'design',description:free[1]};}

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
