import {createRequire} from 'node:module';
import test from 'node:test';import assert from 'node:assert/strict';
const {resolve,options}=createRequire(import.meta.url)('../../cloud_service/static/image-intents.js');
for(const text of ['Bana gerçekçi bir Ferrari fotoğrafı oluştur.','Uzayda yürüyen bir astronot çiz.','Mersin sahilinde gün batımı fotoğrafı oluştur.','Bir ejderha ile savaşan şövalye resmi yap.','Telefonum için dikey duvar kâğıdı oluştur.','Create an image of a red car'])test(text,()=>assert.equal(resolve(text),'generate'));
for(const text of ['Ferrari fotoğrafı bul','Ferrari hakkında bilgi ver','Bu fotoğrafı analiz et','Fotoğrafı indir','Bir uygulama oluştur','2 kere 21 kaç eder','Fotoğraf nasıl oluşturulur?','Create an API'])test(text,()=>assert.equal(resolve(text),null));
test('edit is distinct',()=>assert.equal(resolve('Bu görseli daha sinematik yap'),'edit'));
test('actual ratios',()=>{assert.equal(options('Telefonum için dikey duvar kâğıdı oluştur').aspect_ratio,'9:16');assert.equal(options('Yatay fotoğraf oluştur').aspect_ratio,'16:9');assert.equal(options('Kare fotoğraf oluştur').aspect_ratio,'1:1');});
