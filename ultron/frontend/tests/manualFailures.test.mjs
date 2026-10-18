import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {resolveEarthIntent} from '../src/dashboard/earthIntent.ts';
import {formatWeatherReply} from '../src/dashboard/weatherReply.ts';
import {isStopCommand} from '../src/dashboard/voiceCommand.ts';

test('spoken interruption phrases have an explicit deterministic route',()=>{
  for(const phrase of ['Dur','GÖLGE sus','Konuşmayı kes','Konuşmayı durdur','Yanıtı durdur'])assert.equal(isStopCommand(phrase),true,phrase);
  for(const phrase of ['Biraz durumu anlat','Dünya durmadan dönüyor','Susamlı tarif'])assert.equal(isStopCommand(phrase),false,phrase);
});

test('typed Dur bypasses the busy lock and the composer remains available for it',()=>{
  const dashboard=fs.readFileSync(new URL('../src/dashboard/Dashboard.tsx',import.meta.url),'utf8');
  const start=dashboard.indexOf('const send=async(text=input)');
  const end=dashboard.indexOf("useEffect(()=>{if(u.state!==",start);
  const send=dashboard.slice(start,end);
  assert.ok(start>=0&&end>start);
  assert.ok(send.indexOf('if(isStopCommand(text))')<send.indexOf('if(busy)return'));
  assert.match(dashboard,/busy&&!isStopCommand\(input\)/);
});

test('satellite natural-language variants route to the licensed layer gate',()=>{
  for(const phrase of ['Uydu modunu aç','Uydu moduna geç','Uydu görünümünü aç','Uydu haritasını göster']){
    assert.deepEqual(resolveEarthIntent(phrase,true),{operation:'earth_layer',args:{layer:'SATELLITE'}},phrase);
  }
});

test('weather chat reply reports returned provider data and forecast limits',()=>{
  const reply=formatWeatherReply({source:'Open-Meteo',updated:'2026-10-16T12:00',forecast_not_observation:true,current:{temperature_2m:24.1,wind_speed_10m:2.5},current_units:{temperature_2m:'°C',wind_speed_10m:'km/h'}},'Lefkoşa');
  assert.match(reply,/Lefkoşa/);
  assert.match(reply,/24,1 °C/);
  assert.match(reply,/2,5 km\/sa/);
  assert.match(reply,/Open-Meteo/);
  assert.match(reply,/tahmin verisidir/i);
});

test('native desktop picker sends selected file bytes to the existing image/document handlers',()=>{
  const panels=fs.readFileSync(new URL('../src/dashboard/ReferencePanels.tsx',import.meta.url),'utf8');
  const runtime=fs.readFileSync(new URL('../src/dashboard/runtime.ts',import.meta.url),'utf8');
  const bridge=fs.readFileSync(new URL('../../../integration/web_panel.py',import.meta.url),'utf8');
  assert.match(panels,/pickerRef\.current=openPicker/);
  assert.match(runtime,/e\.kind==='file'[^;]*data/);
  assert.match(runtime,/\/api\/merged\/(?:image|document)/);
  assert.match(bridge,/kind='file',[\s\S]{0,250}data=/);
  assert.match(bridge,/8\s*\*\s*1024\s*\*\s*1024/);
});
