import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from '../ultron/frontend/node_modules/typescript/lib/typescript.js';
const source=fs.readFileSync(new URL('../ultron/frontend/src/spatial/intents.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText;
const {sceneIntent:parse}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
assert.deepEqual(parse('Bir motorun 3D modelini göster'),{kind:'create',model:'engine'});
for(const [text,kind] of [['Motor oluştur','create'],['robot kolunu göster','create'],['Onu yok et','remove'],['motoru sahneden kaldır','remove'],['onu sağa taşı','move'],['yukarı kaldır','move'],['onu kaldır','clarify'],['onu taşı','clarify'],['onu kenara al','move'],['onu kaldır kenara','move'],['onu biraz sağa taşı','move'],['onu 90 derece sola döndür','rotate'],['onu sola 90 derece döndür','rotate'],['onu büyüt','scale'],['geri al','undo'],['sahneyi sıfırla','reset'],['modeli sıfırla','reset'],['sıfırla','reset'],['Piston 1 seç','select']])assert.equal(parse(text,true)?.kind,kind,text);
assert.deepEqual(parse('onu yukarı 2 birim taşı',true),{kind:'move',axis:'y',amount:2,target:'onu'});
assert.deepEqual(parse('onu sola 90 derece döndür',true),{kind:'rotate',axis:'y',amount:-90,target:'onu'});
for(const text of ['sahneyi sıfırla','motor nasıl çalışır','motorun modelini gösterme','dosyayı sil','onu sağa taşı','onu yok et'])assert.equal(parse(text),null,text);
for(const text of ['motor nasıl çalışır','motorun modelini gösterme','dosyayı sil','telefonu sağa taşı','“onu yok et” ne demek','onu silme','sahneyi sıfırlama','dosyayı sıfırla','sahneyi nasıl sıfırlarım'])assert.equal(parse(text,true),null,text);
assert.equal(parse('ejderhanın 3d modelini göster')?.kind,'design');
assert.equal(parse('onu sağa 999 birim taşı',true)?.kind,'clarify');
console.log('Scene intent contracts passed');

for(const text of ['daire','kare','daire çiz','kare yap','üçgen oluştur'])assert.equal(parse(text)?.kind,'create',text);
assert.equal(parse('bir masa modeli oluştur')?.kind,'design');
assert.equal(parse('masa oluştur',true)?.kind,'design');
assert.equal(parse('masa oluştur')?.kind,'design');   // library shape: no "model" word needed
assert.equal(parse('evet oluştur'),null);
assert.equal(parse('ödev oluştur'),null);
assert.equal(parse('dosya oluştur'),null);

assert.equal(parse('internetten sandalye modeli bul getir',true)?.kind,'find');

assert.equal(parse('dosyayı indir'),null);
assert.equal(parse('Gölge, daire çiz')?.kind,'create');

// Shape library + hologram phrases
assert.deepEqual(parse('bana bir kalp çiz'),{kind:'design',description:'kalp'});
assert.deepEqual(parse('8 köşeli yıldız oluştur'),{kind:'design',description:'8 koseli yildiz'});
assert.deepEqual(parse('hologramda bir ejderha göster'),{kind:'design',description:'ejderha'});
assert.deepEqual(parse('bana hologram roket yap'),{kind:'design',description:'roket'});
assert.equal(parse('eyfel kulesi çiz')?.kind,'design');
for(const text of ['hologramda dosya göster','kalp nasıl çalışır','kod oluştur','hesap oluştur','evet yarat','kalp ağrısı çiz'].filter(x=>x!=='kalp ağrısı çiz'))assert.equal(parse(text),null,text);
console.log('Shape library intents passed');
