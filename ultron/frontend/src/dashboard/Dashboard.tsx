import {lazy,Suspense,useEffect,useRef,useState,type CSSProperties} from 'react';
import {Home,Settings,Gamepad2,Box,Folder,Wrench,Puzzle,Power,Globe,Files,Terminal,Scan,ScanText,Calendar,Code,Activity,Grid2X2,PanelsTopLeft,Mic,MicOff,Send,Square,Trash2,MessageSquare,Command,ShieldCheck,X,Bell} from 'lucide-react';
import {useUltron,request,type CoreState} from './runtime';
import {Panel,ModelPanel,ToolPanel} from './Panels';
import {Brand,SystemRail,FileDrop} from './ReferencePanels';
import CenterStage from './CenterStage';
import './dashboard.css';
const HologramLab=lazy(()=>import('../hologram/HologramLab'));
export default function Dashboard(){
 const u=useUltron(),[modal,setModal]=useState(''),[model,setModel]=useState(''),[input,setInput]=useState(''),[command,setCommand]=useState(''),[busy,setBusy]=useState(false),[localState,setLocalState]=useState<CoreState>('IDLE'),[clock,setClock]=useState(new Date()),[hologram,setHologram]=useState(false),[scale,setScale]=useState(1),[compact,setCompact]=useState(false),[extra,setExtra]=useState(''),[mode,setMode]=useState('general');
 const messages=useRef<HTMLDivElement>(null),abort=useRef<AbortController|null>(null),errorTimer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined);
 useEffect(()=>{const resize=()=>setScale(Math.min(innerWidth/1920,innerHeight/1080));resize();window.addEventListener('resize',resize);const timer=setInterval(()=>setClock(new Date()),1000);return()=>{window.removeEventListener('resize',resize);clearInterval(timer);clearTimeout(errorTimer.current);abort.current?.abort();};},[]);
 useEffect(()=>{messages.current?.scrollTo({top:messages.current.scrollHeight});},[u.messages]);
 const notify=(message:string)=>{u.setNotice(message);setLocalState('ERROR');clearTimeout(errorTimer.current);errorTimer.current=setTimeout(()=>setLocalState('IDLE'),1800);};
 const stageIntent=async(raw:string)=>{
  const t=raw.toLocaleLowerCase('tr-TR').replace(/[’']/g,'').replace(/\s+/g,' ').trim();
  const action=async(operation:string,extra:Record<string,unknown>={})=>{await request('/api/stage/command',{operation,...extra});};
  const color=(()=>{
   if(/kırmızı|kirmizi|red/.test(t))return '#ff3047';if(/cyan|turkuaz/.test(t))return '#35ffe4';
   if(/mavi|blue/.test(t))return '#268bff';if(/yeşil|yesil|green/.test(t))return '#25ff8a';
   if(/mor|purple/.test(t))return '#a855f7';if(/beyaz|white/.test(t))return '#f5f7ff';
   if(/sarı|sari|yellow/.test(t))return '#ffd43b';if(/turuncu|orange/.test(t))return '#ff8a2b';return '';
  })();
  const durationMatch=t.match(/(\d+(?:[.,]\d+)?)\s*saniye/),duration=durationMatch?Math.max(2,Math.min(15,Number(durationMatch[1].replace(',','.')))):6;
  const current=u.stage.hologram;

  if(/(?:core.?a dön|çekirdeğe dön|orta alanı sıfırla|sahneyi sıfırla)/.test(t)){await action('reset');return 'Center Stage çekirdeğe döndü.';}
  if(/(?:bunu|hologramı|hologrami).*(?:videoya çevir|video yap)/.test(t)){await action('video_from_stage',{duration,title:current.label});return 'Hologram video renderına geçti.';}
  if(/(?:video|animasyon|intro).*(?:yap|oluştur|olustur|render|hazırla|hazirla)/.test(t)){
   let template='ultron_intro';if(/logo/.test(t))template='logo_reveal';else if(/enerji|çekirdek|cekirdek/.test(t))template='energy_core';else if(/sistem.*(?:aktiv|açıl|acil)/.test(t))template='system_activation';else if(/görev|gorev.*tamam/.test(t))template='task_complete';
   await action('video_create',{template,duration,title:/ultron/.test(t)?'ULTRON':current.label||'ULTRON'});return duration+' saniyelik video renderı başladı.';
  }
  if(/(?:videoyu|video).*(?:durdur|duraklat|pause)/.test(t)){await action('video_pause');return 'Video duraklatıldı.';}
  if(/(?:videoyu|video).*(?:oynat|devam|play)/.test(t)){await action('video_play');return 'Video oynatılıyor.';}
  if(/(?:videoyu|video).*(?:kaydet|indir)/.test(t)){await action('video_save');return 'Video kaydetme penceresi açıldı.';}
  if(/(?:hologramı|hologrami|tasarımı|tasarimi).*(?:kaydet|indir)/.test(t)){await action('hologram_save');return 'Hologram projesi kaydediliyor.';}

  const createHolo=/(?:hologram|enerji küresi|enerji kuresi|dünya küresi|dunya kuresi|drone|araç|arac|logo).*(?:yap|oluştur|olustur|göster|goster|tasarla)|(?:ortaya|ortada).*(?:küre|kure|hologram|drone|dünya|dunya|araç|arac|logo)/.test(t);
  if(createHolo){
   let kind='energy';if(/dünya|dunya/.test(t))kind='globe';else if(/ağ|ag|network|node/.test(t))kind='network';else if(/drone/.test(t))kind='drone';else if(/araba|araç|arac|vehicle/.test(t))kind='vehicle';else if(/logo/.test(t))kind='logo';else if(/küre|kure|sphere/.test(t)&&!/enerji/.test(t))kind='sphere';
   const extra:Record<string,unknown>={kind,label:kind==='globe'?'EARTH':kind==='logo'?'ULTRON':kind.toUpperCase()};if(color)extra.color=color;
   await action('hologram_create',extra);return 'Hologram Center Stage üzerinde oluşturuldu.';
  }

  const controlHolo=u.stage.mode==='hologram_lab'&&/(?:bunu|hologram|küre|kure|sahne)/.test(t);
  if(controlHolo){
   const patch:Record<string,unknown>={};
   if(color)patch.color=color;
   if(/büyüt|buyut|daha büyük|daha buyuk/.test(t))patch.scale=Math.min(2.5,current.scale*1.2);
   if(/küçült|kucult|daha küçük|daha kucuk/.test(t))patch.scale=Math.max(.25,current.scale/1.2);
   if(/hızlandır|hizlandir|daha hızlı|daha hizli/.test(t))patch.speed=Math.min(5,current.speed*1.3);
   if(/yavaşlat|yavaslat|daha yavaş|daha yavas/.test(t))patch.speed=Math.max(.05,current.speed/1.3);
   if(/wireframe|tel kafes/.test(t))patch.wireframe=!/kapat|çıkar|cikar|solid/.test(t);
   if(/pulse|nabız|nabiz/.test(t))patch.pulse=!/kapat|durdur/.test(t);
   const ring=t.match(/(\d+)\s*(?:halka|ring)/);if(ring)patch.rings=Math.max(0,Math.min(12,Number(ring[1])));
   else if(/halka.*(?:ekle|artır|artir)/.test(t))patch.rings=Math.min(12,current.rings+2);
   if(Object.keys(patch).length){await action('hologram_update',patch);return 'Hologram güncellendi.';}
  }
  return '';
 };
 const send=async(text=input)=>{if(!text.trim()||busy)return;setInput('');setCommand('');if(model==='native'){if(u.native)u.native.send(text);return;}u.add('user',text);
  try{const stageReply=await stageIntent(text);if(stageReply){u.add('assistant',stageReply);return;}}catch(e){notify((e as Error).message);return;}
  setBusy(true);setLocalState('THINKING');const ctl=new AbortController();abort.current=ctl;
  try{const r=await request('/api/merged/invoke',{text,mode,...(model?{model}:{})},ctl.signal);u.add('assistant',r.text||JSON.stringify(r));setLocalState('IDLE');}catch(e){notify((e as Error).message);}finally{setBusy(false);abort.current=null;}};
 const state:CoreState=localState!=='IDLE'?localState:u.state!=='IDLE'?u.state:u.taskState!=='IDLE'?u.taskState:u.nativeState;
 const stop=()=>{abort.current?.abort();u.native?.action('interrupt');};
 useEffect(()=>{const key=(e:KeyboardEvent)=>{if(e.key==='Escape'){stop();setModal('');}};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[u.native]);
 const review=async(path:string,id:string)=>{try{await request(path,{id});u.setPending(null);u.setPatch(null);}catch(e){notify((e as Error).message);}};
 const run=async(path:string,body?:unknown)=>{try{setExtra(JSON.stringify(await request(path,body),null,2));}catch(e){notify((e as Error).message);}};
 const open=(name:string)=>{setModal(name);setExtra('');if(name==='Eklentiler'){u.native?.action('plugins');void run('/api/skills');}if(name==='Araçlar')void run('/api/tools');if(name==='Kontroller')void run('/api/voice/wake');};
 const holo=()=>{void request('/api/stage/command',{operation:'hologram_create',kind:u.stage?.hologram?.kind||'energy'}).catch(e=>notify((e as Error).message));};
 const ready=(value:unknown)=>u.connected?(value?'ONLINE':'N/A'):'OFFLINE';
 const chipsLeft=[['SYSTEM',u.connected?'ONLINE':'OFFLINE'],['MEMORY',ready(u.memory)],['TASK ENGINE',ready(u.health?.components?.task_engine)],['VISION',ready(u.ai?.vision)],['AUDIO',u.native?(u.muted?'MUTED':u.nativeState):'N/A']];
 const chipsRight=[['AI CORE',ready(u.health?.components?.brain)],['NEURAL LINK',ready(u.ai?.connected)],['TOOLS',u.connected?`${u.tools.filter(t=>t.status==='READY').length} READY`:'N/A'],['PLUGINS',u.plugins?`${u.plugins.length} LOADED`:'N/A'],['MONITOR',u.system?'LIVE':'N/A']];
 const disabledSend=busy||!u.connected&&model!=='native';
 const footer=[['Web Tarayıcı',Globe,()=>open('Browser')],['Dosya İşlemleri',Files,()=>open('Dosyalar')],['Terminal',Terminal,()=>open('Terminal')],['Ekran Yakalama',Scan,()=>{open('Vizyon');void run('/api/actions/screenshot',{});}],['OCR',ScanText,()=>{open('Vizyon');void run('/api/merged/tool',{name:'screen_ocr',arguments:{}});}],['Planlayıcı',Calendar,()=>open('Görevler')],['Kod Asistanı',Code,()=>{setMode('coding');open('Kod Asistanı');}],['Sistem Monitörü',Activity,()=>open('Sistem Monitörü')]] as const;
 return <div className="viewport"><div className={'ultron-app '+(compact?'compact':'')} style={{transform:`translate(-50%,-50%) scale(${scale})`}}>
 <header className="main-header metal-frame"><Brand/><nav>
 <button className={!modal?'selected':''} onClick={()=>setModal('')}><Home/>Ana Ekran</button>
 <button onClick={()=>open('Ayarlar')}><Settings/>Ayarlar</button><button onClick={()=>open('Kontroller')}><Gamepad2/>Kontroller</button>
 <button onClick={holo}><Box/>Hologram Çalışma Alanı</button><button onClick={()=>open('Dosyalar')}><Folder/>Dosyalar</button><button onClick={()=>open('Araçlar')}><Wrench/>Araçlar</button><button onClick={()=>open('Eklentiler')}><Puzzle/>Eklentiler</button>
 </nav><time>{clock.toLocaleTimeString('tr-TR')}<small>{clock.toLocaleDateString('tr-TR',{day:'2-digit',month:'short',year:'numeric'})}<br/>{clock.toLocaleDateString('tr-TR',{weekday:'long'})}</small></time><button className="power" aria-label="ULTRON'u kapat" disabled={!u.native} onClick={()=>u.native?.action('shutdown')}><Power/></button></header>
 <main className="main-grid"><SystemRail system={u.system} history={u.history} health={u.health} connected={u.connected}/>
 <section className="reactor-panel metal-frame"><CenterStage stage={u.stage} state={state} amplitude={u.amplitude} notify={notify}/>{u.stage.mode==='core_idle'&&<><div className="subsystems left">{chipsLeft.map(([label,value])=><div key={label} className={value==='OFFLINE'||value==='N/A'?'unavailable':''}><i/>{label}<b>{value}</b></div>)}</div><div className="subsystems right">{chipsRight.map(([label,value])=><div key={label} className={value==='OFFLINE'||value==='N/A'?'unavailable':''}><i/>{label}<b>{value}</b></div>)}</>}{!u.connected&&<div className="offline" role="status">ULTRON BACKEND OFFLINE</div>}</section>
 <aside className="right-panels"><Panel title="KONUŞMA / AKTİVİTE" icon={<MessageSquare/>} className="chat-panel" extra={<button disabled={busy} onClick={()=>u.setMessages([])}><Trash2/>Temizle</button>}><div className="messages" ref={messages}>{!u.messages.length&&<p className="chat-empty">{u.connected?'ULTRON bağlantısı kuruldu. Bir komut yaz veya sor.':'Backend bağlantısı bekleniyor…'}</p>}{u.messages.map(m=><article className={'message '+m.role} key={m.id}><time>{new Date(m.time).toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'})}</time><p><b>{m.role==='user'?'You':'ULTRON'}:</b> {m.text}</p></article>)}{busy&&<p className="muted">Yanıt hazırlanıyor…</p>}</div><form className="composer" onSubmit={e=>{e.preventDefault();void send();}}><input aria-label="Mesaj" value={input} onChange={e=>setInput(e.target.value)} placeholder="Bir komut yaz veya sor…"/><button aria-label="Gönder" disabled={disabledSend||!input.trim()}><Send/></button></form></Panel>
 <FileDrop notify={notify} ask={send} nativeFile={u.native?()=>u.native?.action('file'):undefined}/>
 <Panel title="KOMUT" icon={<Command/>} className="command-panel"><form onSubmit={e=>{e.preventDefault();void send(command);}}><button type="button" className="mic-circle" aria-label="Mikrofon" disabled={!u.native} onClick={()=>u.native?.action('mute')}>{u.muted?<MicOff/>:<Mic/>}</button><input aria-label="Komut" value={command} onChange={e=>setCommand(e.target.value)} placeholder="Komut yaz…"/><button aria-label="Komutu gönder" disabled={disabledSend||!command.trim()}><Send/></button></form><button className="interrupt" onClick={stop}><Square/>KONUŞMAYI DURDUR <span>[ESC]</span></button><button className={'voice-status '+(u.native&&!u.muted?'active':'')} disabled={!u.native} onClick={()=>u.native?.action('mute')}><Mic/>{u.native?(u.muted?'MİKROFON KAPALI':state==='THINKING'?'İŞLENİYOR':'MİKROFON AKTİF'):'MİKROFON N/A'}</button></Panel></aside></main>
 <footer className="bottom-toolbar metal-frame">{footer.map(([name,Icon,action])=><button key={name} onClick={action}><Icon/>{name}</button>)}<div className="view-buttons"><button aria-label="Panel yoğunluğunu değiştir" aria-pressed={compact} onClick={()=>setCompact(!compact)}><PanelsTopLeft/></button><button aria-label="Çalışma alanlarını aç" onClick={()=>open('Araçlar')}><Grid2X2/></button></div></footer>
 {modal&&<div className="modal-shade"><section className="work-dialog metal-frame" role="dialog" aria-modal="true" aria-label={modal}><header><h2>{modal}</h2><button aria-label="Paneli kapat" onClick={()=>setModal('')}><X/></button></header><div className="dialog-content">
 {['Ayarlar','Kod Asistanı'].includes(modal)&&<><ModelPanel ai={u.ai} model={model} setModel={setModel} native={u.native}/><label>Yanıt modu<select aria-label="Yanıt modu" value={mode} onChange={e=>setMode(e.target.value)}><option value="general">Genel</option><option value="coding">Kod</option><option value="fast">Hızlı</option><option value="agent">Araç kullanan agent</option></select></label><button onClick={()=>open('Hafıza')}>Hafıza</button><button onClick={()=>open('Bildirimler')}>Bildirimler</button></>}
 {modal==='Kontroller'&&<><div className="control-buttons"><button disabled={!u.native} onClick={()=>u.native?.action('mute')}>{u.muted?'Mikrofonu aç':'Mikrofonu kapat'}</button><button disabled={!u.native} onClick={()=>u.native?.action('audio')}>Ses aygıtları</button><button disabled={!u.native} onClick={()=>u.native?.action('camera')}>Kamera</button><button disabled={!u.native} onClick={()=>u.native?.action('controls')}>Wake / bas konuş kontrolleri</button></div><h3>Telefon Kontrolü</h3><p className="muted">{(()=>{const phone=u.devicePresence.find((d:any)=>d.device==='phone');return phone?.online?'Telefon ULTRON: ONLINE'+(phone?.state?.view?' • '+phone.state.view.toUpperCase():''):'Telefon ULTRON: OFFLINE';})()}</p><div className="control-buttons"><button disabled={!u.native} onClick={()=>u.native?.action('phone:ping')}>Bağlantı sinyali</button><button disabled={!u.native} onClick={()=>u.native?.action('phone:vibrate')}>Telefonu titreştir</button><button disabled={!u.native} onClick={()=>u.native?.action('phone:refresh')}>Telefon ULTRON'u yenile</button><button disabled={!u.native} onClick={()=>u.native?.action('phone:focus_chat')}>Sohbeti aç</button><button disabled={!u.native} onClick={()=>u.native?.action('phone:open_memory')}>Hafızayı aç</button><button disabled={!u.native} onClick={()=>u.native?.action('phone:open_remote')}>Uzaktan kontrolü aç</button><button disabled={!u.native} onClick={()=>u.native?.action('phone:scroll_top')}>Sayfanın başına git</button></div><p className="muted">Bu panel telefonun ULTRON web arayüzünü yönetir. iOS sisteminin kendi izinleri ayrı kalır.</p></>}
 {modal==='Araçlar'&&<><div className="tool-grid">{['Browser','Dosyalar','Terminal','Vizyon','Görevler','Hafıza','Ayarlar','Kod Asistanı'].map(n=><button key={n} onClick={()=>open(n)}>{n}</button>)}</div><h3>Center Stage</h3><div className="control-buttons"><button onClick={()=>void request('/api/stage/command',{operation:'hologram_create',kind:'energy'})}>Enerji hologramı</button><button onClick={()=>void request('/api/stage/command',{operation:'hologram_create',kind:'globe'})}>Dünya hologramı</button><button onClick={()=>void request('/api/stage/command',{operation:'video_create',template:'ultron_intro',duration:6,title:'ULTRON'})}>ULTRON intro render</button><button onClick={()=>void request('/api/stage/command',{operation:'reset'})}>Core'a dön</button><button onClick={()=>setHologram(true)}>Gelişmiş Hologram Lab</button></div></>}
 {modal==='Eklentiler'&&<><h3>Yerel eklenti kayıtları</h3><pre>{u.plugins?JSON.stringify(u.plugins,null,2):'Native eklenti kaydı N/A'}</pre><h3>Backend becerileri</h3></>}
 {modal==='Sistem Monitörü'&&<pre>{JSON.stringify(u.system??{status:'N/A'},null,2)}</pre>}
 {modal==='Bildirimler'&&<pre>{u.notifications.length?JSON.stringify(u.notifications,null,2):'Bildirim yok.'}</pre>}
 {['Dosyalar','Terminal','Browser','Vizyon','Görevler','Otomasyon','Hafıza','Ayarlar'].includes(modal)&&<ToolPanel key={modal} tab={modal} native={u.native} notify={notify} ask={send}/>}
 {extra&&<pre className="tool-output">{extra}</pre>}
 </div></section></div>}
 {(u.pending||u.patch)&&<div className="modal-shade approval-shade"><section className="work-dialog metal-frame" role="dialog" aria-label="İşlem onayı"><header><h2><ShieldCheck/> İşlem onayı gerekiyor</h2></header><div className="dialog-content"><pre>{JSON.stringify(u.pending??u.patch,null,2)}</pre><p>Yalnız inceleyip kabul ettiğiniz işlemi onaylayın.</p><button onClick={()=>review(u.pending?'/api/task/reject':'/api/codegen/reject',(u.pending??u.patch)!.id)}>Reddet</button><button onClick={()=>review(u.pending?'/api/task/approve':'/api/codegen/apply',(u.pending??u.patch)!.id)}>İnceledim, onayla</button></div></section></div>}
 {u.notice&&<div className="toast" role="alert">{u.notice}<button aria-label="Uyarıyı kapat" onClick={()=>u.setNotice('')}>×</button></div>}
 {hologram&&<Suspense fallback={<div className="modal-shade">Hologram yükleniyor…</div>}><HologramLab accent="#ff3047" onClose={()=>setHologram(false)} onAsk={send}/></Suspense>}
 </div></div>;
}
