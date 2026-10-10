"use strict";
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const base=__dirname;
const web=fs.readFileSync(path.join(base,'static','world.html'),'utf8');
const js=fs.readFileSync(path.join(base,'static','world.js'),'utf8');
const pwa=fs.readFileSync(path.join(base,'static','index.html'),'utf8');
const backend=fs.readFileSync(path.join(base,'world_api.py'),'utf8');
const app=fs.readFileSync(path.join(base,'app.py'),'utf8');

test('PWA speech and typed WORLD controls accept only allowlisted same-origin iframe commands',()=>{
 assert.match(pwa,/function worldVoiceIntent\(text\)/);
 assert.match(pwa,/handlePanelIntent\(heard\)/);
 assert.match(pwa,/function handlePanelIntent\(text\)/);
 assert.match(pwa,/if\(!worldVoiceIntent\(text\)\)showView\('world'\)/);
 assert.match(pwa,/worldVoiceIntent\(text\)/);
 assert.match(pwa,/worldCommandQueue\.length>=4/);
 assert.match(js,/event\.origin!==location\.origin\|\|event\.source!==window\.parent/);
 assert.match(js,/cmd\.type!=='ultron_world'/);
 assert.match(js,/Number\.isFinite\(lat\)/);
 assert.ok(js.includes("['flights','quakes','weather'].includes(cmd.value)"));
});
test('iPhone PWA embeds WORLD behind the on-demand workspace menu',()=>{
 assert.match(pwa,/<section id="worldView" class="view">/);
 assert.match(pwa,/<button data-view="world">DÜNYA<\/button>/);
 assert.match(pwa,/\.tabs:not\(\.panel-nav-open\)\{opacity:0!important/);
 assert.match(pwa,/iframe id="worldFrame"[^>]*src="\/static\/world.html"/);
});
test('2D map offers OpenStreetMap zoom to house scale with required attribution',()=>{
 assert.match(web,/id="map"/);
 assert.match(js,/https:\/\/tile\.openstreetmap\.org\/\{z\}\/\{x\}\/\{y\}\.png/);
 assert.match(js,/maxZoom:19/);
 assert.match(web,/openstreetmap.org\/copyright/);
});
test('real 3D display requires Three.js WebGL and user-driven rotation',()=>{
 assert.match(js,/await import\('https:\/\/esm\.sh\/three@0\.177\.0'\)/);
 assert.match(js,/new THREE.WebGLRenderer/);
 assert.match(js,/SphereGeometry\(2\.4/);
 assert.match(js,/pointermove/);
 assert.match(js,/getPointerCapture|setPointerCapture/);
});
test('cloud-only real providers: weather, ADSB flights, earthquake and Photon',()=>{
 for(const source of ['api.open-meteo.com','api.adsb.lol','earthquake.usgs.gov','photon.komoot.io','air-quality-api.open-meteo.com'])assert.ok(backend.includes(source),source);
 for(const route of ['/api/world/weather','/api/world/flights','/api/world/earthquakes','/api/world/search','/api/world/air-quality'])assert.ok(backend.includes(route),route);
 assert.match(app,/add_world_routes\(app\)/);
 assert.match(backend,/_CACHE_LIMIT = 180/);
 assert.match(backend,/async def _upstream/);
});
test('aircraft has an independently operated fallback with source attribution',()=>{
 assert.match(backend,/opendata\.adsb\.fi\/api\/v3\/lat/);
 assert.match(backend,/reported = data\.get\("ac", data\.get\("aircraft"\)\)/);
 assert.match(js,/String\(d\.source\|\|'ADS-B'\)/);
 assert.match(web,/href="https:\/\/adsb\.fi\//);
});
test('unavailable aircraft and quakes clear stale markers instead of inventing data',()=>{
 assert.match(js,/flightsLayer\?\.clearLayers\(\)/);
 assert.match(js,/quakesLayer\?\.clearLayers\(\)/);
 assert.match(js,/sahte uçak gösterilmiyor/);
 assert.match(js,/sahte olay gösterilmiyor/);
});
test('fixed source adapters have bounded coordinates and no arbitrary user URLs',()=>{
 assert.match(backend,/not math\.isfinite\(value\)/);
 assert.match(backend,/coordinate\(request\.query\.get\("lat"\), -90, 90/);
 assert.match(backend,/coordinate\(request\.query\.get\("lon"\), -180, 180/);
 assert.match(backend,/allow_redirects=False/);
 assert.match(backend,/read\(2_000_001\)/);
 assert.doesNotMatch(backend,/_upstream\(request\.query/);
});
test('weather has real rate-limit fallback and labels its provider truthfully',()=>{
 assert.match(backend,/api\.met\.no\/weatherapi\/locationforecast\/2\.0\/compact/);
 assert.match(backend,/forecast_not_observation/);
 assert.match(js,/d\.forecast_not_observation/);
 assert.match(js,/String\(d\.source\|\|'Sağlayıcı bilinmiyor'\)/);
 assert.match(web,/MET Norway/);
});
test('UV, sunrise, air quality, wind, radar and ship sources must be identified',()=>{
 assert.match(js,/const days=d\.daily\|\|\{\}/);
 assert.match(js,/days\.sunrise/);
 assert.match(web,/id="airQuality"/);
 assert.match(js,/asAPI\('air-quality'/);
 assert.match(js,/rainviewer\.com/);
 assert.match(js,/earth\.nullschool\.net/);
 assert.match(js,/marinetraffic\.com/);
});
test('other data layers are labeled external and do not impersonate native traffic or satellite',()=>{
 assert.match(web,/UYDU ↗/);
 assert.match(web,/TRAFİK ↗/);
 assert.match(web,/SOKAK GÖRÜNÜMÜ ↗/);
 assert.match(js,/google\.com\/maps/);
 assert.match(js,/www\.openstreetmap\.org\/directions/);
});
test('user location requested on tap only, never silently sent',()=>{
 assert.match(js,/btn\('findMe'/);
 assert.match(js,/navigator\.geolocation\.getCurrentPosition/);
 assert.doesNotMatch(js,/watchPosition/);
});
test('PWA caches world shell but does not cache external map tiles',()=>{
 const sw=fs.readFileSync(path.join(base,'static','sw.js'),'utf8');
 assert.match(sw,/ultron-shell-v[0-9]+/);
 assert.match(sw,/\/static\/world\.html/);
 assert.match(sw,/\/static\/world\.js/);
 assert.match(sw,/if\(url\.origin!==location\.origin\)return/);
});
