import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveEarthIntent,cleanPlaceQuery} from '../src/dashboard/earthIntent.ts';

test('Earth voice and typed commands use the same action protocol',()=>{
 const cases=[
  ['GÖLGE, Dünya’yı göster.','earth_open'],['GÖLGE, Dünya’yı aç.','earth_open'],
  ["GÖLGE, CORE’a dön.",'reset'],['Normal holograma dön','reset'],['Dünya’dan çık','reset'],
  ['Uydu moduna geç','earth_layer'],['Haritayı aç','earth_layer'],['3D görünümü aç','earth_layer'],
  ['Dünya’nın gece tarafını göster','earth_control'],['Dünyayı döndür','earth_control'],
  ['Biraz daha yakınlaş','earth_zoom'],['Uzaklaş','earth_zoom'],['Uçakları göster','earth_layer'],
  ['Hava durumunu göster','earth_layer'],['Kayıtlı konumları göster','earth_layer'],
  ['Kıbrıs’a git','earth_search'],['Lefkoşa’yı göster','earth_search'],['Avrupa’yı göster','earth_search'],
 ];
 for(const [input,operation] of cases)assert.equal(resolveEarthIntent(input,true)?.operation,operation,input);
 assert.equal(resolveEarthIntent('uydu moduna geç',true).args.layer,'SATELLITE');
 assert.equal(resolveEarthIntent('haritayı aç',true).args.layer,'MAP');
 assert.equal(resolveEarthIntent('uzaklaş',true).args.factor,1.3);
});
test('Geocoding queries preserve Turkish place names and remove command suffixes',()=>{
 assert.equal(cleanPlaceQuery('Lefkoşa’yı'),'Lefkoşa');
 assert.equal(cleanPlaceQuery("Kıbrıs'a"),'Kıbrıs');
 assert.equal(resolveEarthIntent('GÖLGE, Lefkoşa’yı göster.',true).args.query,'Lefkoşa');
 assert.equal(resolveEarthIntent('Türkiye’ye yaklaş',true).args.query,'Türkiye');
});
test('ordinary discussion, device tools and mobile messages are not swallowed',()=>{
 for(const text of ['Dünya kaç yaşında?','Dünya hakkında konuşalım','Uydu nedir?','Dosyaları göster','Kodunu göster','Kamerayı aç','Sistemimi analiz et','Merhaba','Dünya dosyalarını sil'])assert.equal(resolveEarthIntent(text,true),null,text);
 assert.equal(resolveEarthIntent('Biraz daha yakınlaş',false),null);
 assert.equal(resolveEarthIntent('Lefkoşa’yı göster',false),null);
});
test('existing Earth controls and explicit coordinates remain available',()=>{
 for(const [text,key,value] of [['Bulutları kapat','clouds',false],['Izgarayı göster','grid',true],['UTC güneşi kapat','sun_sync',false],['ISS takibini aç','live_iss',true]])assert.equal(resolveEarthIntent(text,true)?.args[key],value,text);
 assert.equal(resolveEarthIntent('Pinleri temizle',true)?.operation,'earth_marker_clear');
 assert.deepEqual(resolveEarthIntent('35.1854, 33.3610 koordinatına git',true)?.args,{lat:35.1854,lon:33.361,place:'KOORDİNAT'});
 assert.equal(resolveEarthIntent('135, 33 koordinatına git',true)?.operation,'earth_invalid');
});
