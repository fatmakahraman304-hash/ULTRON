"use strict";
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const dir=path.join(__dirname,'static');
const script=fs.readFileSync(path.join(dir,'dev-requests.js'),'utf8');
const html=fs.readFileSync(path.join(dir,'index.html'),'utf8');
const schema=fs.readFileSync(path.join(__dirname,'schema.sql'),'utf8');
const sw=fs.readFileSync(path.join(dir,'sw.js'),'utf8');

function helper(){
 let api=null;
 const window={
  addEventListener(){}, open(){throw new Error('must require explicit click')}
 };
 const context={window,document:{},navigator:{},setInterval(){}};
 vm.runInNewContext(script,context,{filename:'dev-requests.js'});
 api=window.ULTRONDevRequests;
 assert.ok(api);return api;
}

test('mobile development request intent is conservative',()=>{
 const h=helper();
 assert.equal(h.detect('ULTRON kendini güncelle, yeni özellik ekle'),true);
 assert.equal(h.detect('ULTRON arayüzünü geliştir'),true);
 assert.equal(h.detect('ULTRON hava durumunu söyle'),false);
 assert.equal(h.detect('Dünyayı aç'),false);
});
test('device inference does not mislabel requested phone-only or Windows-only',()=>{
 const h=helper();
 assert.equal(h.suggestTarget('Sadece iPhone arayüzünü geliştir'),'phone');
 assert.equal(h.suggestTarget('Sadece Windows ULTRON uygulamasını geliştir'),'desktop');
 assert.equal(h.suggestTarget('ULTRON kendini güncelle'),'both');
});
test('phone requires click to explicitly copy + open ChatGPT',()=>{
 assert.match(script,/copy\.onclick=\(\)=>copyRequest\(item\)/);
 assert.match(script,/open\.onclick=\(\)=>root\.open\('https:\/\/chatgpt\.com\/'/);
 assert.match(script,/navigator\.clipboard\.writeText\(text\)/);
 assert.doesNotMatch(script,/\bfetch\(['"]https:\/\/chatgpt\.com/);
 assert.doesNotMatch(script,/\bfetch\(['"]https:\/\/api\.openai\.com/);
});
test('verified status is retrieved from server and not client-side set to completed',()=>{
 assert.match(script,/api\('\/api\/dev-requests\/'\+encodeURIComponent\(item\.id\)\+'\/verify','POST'\)/);
 assert.match(script,/Object\.assign\(item,d\.request\)/);
 assert.match(script,/item\.status==='completed'/);
 assert.doesNotMatch(script,/item\.status\s*=\s*['"]completed['"]/);
 assert.match(script,/güncelleme tamamlandı/);
});
test('iPhone shows development panel for typed and voice input',()=>{
 assert.match(html,/id="developView"/);
 assert.match(html,/<button data-view="develop">GELİŞTİR<\/button>/);
 assert.match(html,/id="devPrompt"/);
 assert.match(html,/id="devTarget"/);
 assert.match(html,/\/static\/dev-requests\.js/);
 assert.match(html,/ULTRONDevRequests\?\.fromSpeech\(heard\)/);
 assert.match(html,/ULTRONDevRequests\?\.fromText\(text\)/);
 assert.match(html,/ULTRONDevRequests\?\.init\(\)/);
 assert.match(sw,/ultron-shell-v41/);
 assert.match(sw,/\/static\/dev-requests\.js/);
});
test('the cloud database does not give client direct completion privileges',()=>{
 assert.match(schema,/CREATE TABLE IF NOT EXISTS dev_requests/);
 assert.match(schema,/verified_tests BOOLEAN NOT NULL DEFAULT FALSE/);
 assert.match(schema,/verified_cloud BOOLEAN NOT NULL DEFAULT FALSE/);
});
