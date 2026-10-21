const CACHE='ultron-shell-v80';
const SHELL=['/','/static/manifest.webmanifest','/static/golge-minimal.css','/static/golge-reference-mobile.css','/static/golge-icon.svg','/static/golge-night-lake.webp','/static/assistant-extras.js','/static/laptop-bridge.js','/static/mobile-action-guard.js','/static/world.html','/static/world.js','/static/dev-requests.js','/static/local-voice.js','/static/long-listen.js','/static/listening-analysis.js','/static/local-listening.js','/static/local-listening-probe.js','/static/listening-provider.js','/static/live-playback.js','/static/speaker-policy.js','/static/voice-turn-guard.js','/static/personal-panel.js','/static/owner-plans.js','/static/learning-review.js','/static/panel-intents.js','/static/image-intents.js','/static/auto-brain.js','/static/source-links.js','/static/chat-transport.js','/static/scene-intents.js','/static/conversation-notes.js'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)));self.skipWaiting()});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener('fetch',event=>{
  const req=event.request;
  if(req.method!=='GET')return;
  const url=new URL(req.url);
  if(url.origin!==location.origin)return;
  if(url.pathname.startsWith('/api/'))return;
  event.respondWith(fetch(req,{cache:'no-store'}).then(res=>{if(res.ok){const copy=res.clone();caches.open(CACHE).then(c=>c.put(req,copy)).catch(()=>{});}return res}).catch(()=>caches.match(req)));
});

self.addEventListener('push',event=>{
  let data={};try{data=event.data?event.data.json():{}}catch(e){data={body:event.data&&event.data.text()}}
  const title=String(data.title||'GÖLGE').slice(0,80),body=String(data.body||'').slice(0,300);
  event.waitUntil(self.registration.showNotification(title,{body,tag:data.tag||'golge',icon:'/static/golge-icon.svg',badge:'/static/golge-icon.svg',renotify:true,data:{url:'/'}}));
});
self.addEventListener('notificationclick',event=>{
  event.notification.close();
  event.waitUntil(self.clients.matchAll({type:'window',includeUncontrolled:true}).then(list=>{
    for(const c of list){if('focus' in c)return c.focus()}
    return self.clients.openWindow('/');
  }));
});
