import {useEffect,useRef,useState} from 'react';
import type {SystemSnapshot,AIStatus,TaskProposal,PatchProposal} from '../lib/types';
export type CoreState='IDLE'|'LISTENING'|'THINKING'|'SPEAKING'|'WORKING'|'ERROR';
export type StageMode='core_idle'|'hologram_lab'|'scene_lab'|'earth_watch'|'video_rendering'|'video_preview'|'task_progress'|'screen_preview'|'animation_preview'|'world_map';
export type HologramConfig={
 kind:string;color:string;glow:number;speed:number;rings:number;particles:number;
 scale:number;opacity:number;wireframe:boolean;pulse:boolean;label:string;
};
export type EarthMarker={id:string;lat:number;lon:number;label:string;color:string};
export type EarthState={auto_rotate:boolean;rotation_speed:number;clouds:boolean;atmosphere:boolean;stars:boolean;sun_sync:boolean;grid:boolean;night:boolean;live_iss:boolean;focus_lat:number;focus_lon:number;focus_label:string;markers:EarthMarker[]};
export type SceneMotion={type:string;speed:number;radius:number;amplitude:number;axis:string};
export type ScenePhysics={mode:string;gravity:number;velocity:number[];bounce:number;floor:number;started_at?:number|null};
export type SceneConstraint={type:string;target_id?:string|null;distance:number;speed:number;offset:number[]};
export type ScenePath={points:number[][];speed:number;loop:boolean;started_at?:number|null};
export type SceneObject={id:string;kind:string;label:string;model_id?:string|null;parent_id?:string|null;color:string;position:number[];rotation:number[];scale:number;opacity:number;wireframe:boolean;spin:number;explode:number;visible?:boolean;locked?:boolean;clip_speed?:number;clip_paused?:boolean;motion?:SceneMotion;physics?:ScenePhysics;constraint?:SceneConstraint;path?:ScenePath};
export type SceneKeyframe={id:string;time:number;object_id:string;position:number[];rotation:number[];scale:number;easing?:'linear'|'ease_in'|'ease_out'|'ease_in_out'};
export type SceneTimeline={duration:number;cursor:number;playing:boolean;loop:boolean;started_at?:number|null;keyframes:SceneKeyframe[]};
export type SceneCinematic={enabled:boolean;preset:string;duration:number;started_at?:number|null;loop:boolean};
export type SceneLink={id:string;source:string;target:string;label:string;color:string};
export type SceneHud={id:string;object_id?:string|null;title:string;value:string;unit:string;color:string};
export type SceneCameraPose={position:number[];target:number[]};
export type SceneGroup={id:string;name:string;members:string[]};
export type SceneCameraBookmark={id:string;name:string;pose:SceneCameraPose};
export type SceneCameraKeyframe={id:string;time:number;position:number[];target:number[];easing?:'linear'|'ease_in'|'ease_out'|'ease_in_out'};
export type SceneSequenceStep={id:string;at:number;operation:string;args:Record<string,unknown>;label:string};
export type SceneSequence={name:string;steps:SceneSequenceStep[];playing:boolean;loop:boolean;started_at?:number|null;run_id:number;duration:number};
export type SceneTrigger={id:string;name:string;enabled:boolean;condition_type:'timer'|'distance_lt'|'distance_gt'|'collision';source_id?:string|null;target_id?:string|null;threshold:number;delay:number;action_operation:string;action_args:Record<string,unknown>;once:boolean;cooldown:number;fired:boolean;last_fired_at?:number|null;armed_at:number};
export type SceneMeasurement={id:string;source:string;target:string;label:string;color:string};
export type SceneState={objects:SceneObject[];links?:SceneLink[];hud?:SceneHud[];groups?:SceneGroup[];camera_bookmarks?:SceneCameraBookmark[];camera_track?:SceneCameraKeyframe[];sequence?:SceneSequence;triggers?:SceneTrigger[];measurements?:SceneMeasurement[];selected_id?:string|null;selected_ids?:string[];focus_id?:string|null;target_id?:string|null;camera:string;camera_pose?:SceneCameraPose|null;project_name?:string;explode:number;auto_orbit:boolean;grid:boolean;show_labels?:boolean;show_trails?:boolean;audio_reactive?:boolean;collision_overlay?:boolean;render_mode?:string;theme?:string;snap?:number;animation:string;timeline?:SceneTimeline;cinematic?:SceneCinematic};
export type StageState={
 mode:StageMode;title:string;subtitle:string;progress:number;revision:number;
 job_id?:string|null;video_paused?:boolean;save_nonce?:number;save_kind?:string;record_nonce?:number;record_duration?:number;project_result?:any;snapshot_result?:any;diagnostics_result?:any;measurement_result?:any;asset_result?:any;
 animation?:{kind:string;title:string};
 hologram:HologramConfig;
 earth:EarthState;
 scene:SceneState;
 video:{template:string;duration:number;title:string;ready:boolean;mime:string;bytes:number;source_hologram?:boolean;source_scene?:boolean};
};
export const defaultStage:StageState={
 mode:'core_idle',title:'ULTRON',subtitle:'NEURAL CORE',progress:0,revision:0,job_id:null,save_nonce:0,save_kind:'',record_nonce:0,record_duration:8,
 animation:{kind:'bird',title:'KÜÇÜK ANİMASYON'},
 hologram:{kind:'energy',color:'#ff3047',glow:1,speed:1,rings:4,particles:900,scale:1,opacity:.92,wireframe:false,pulse:true,label:'ULTRON'},
 earth:{auto_rotate:true,rotation_speed:.08,clouds:true,atmosphere:true,stars:true,sun_sync:true,grid:false,night:false,live_iss:false,focus_lat:20,focus_lon:0,focus_label:'GLOBAL',markers:[]},
 scene:{objects:[],links:[],hud:[],groups:[],camera_bookmarks:[],camera_track:[],sequence:{name:'',steps:[],playing:false,loop:false,started_at:null,run_id:0,duration:0},triggers:[],measurements:[],selected_id:null,selected_ids:[],focus_id:null,target_id:null,camera:'isometric',camera_pose:null,project_name:'Untitled',explode:0,auto_orbit:true,grid:true,show_labels:true,show_trails:true,audio_reactive:true,collision_overlay:false,render_mode:'hologram',theme:'crimson',snap:.25,animation:'idle',timeline:{duration:8,cursor:0,playing:false,loop:true,started_at:null,keyframes:[]},cinematic:{enabled:false,preset:'orbit',duration:8,started_at:null,loop:true}},
 video:{template:'ultron_intro',duration:6,title:'ULTRON',ready:false,mime:'',bytes:0}
};
export const coreState=(value:string):CoreState=>({PLANNING:'THINKING',EXECUTING:'WORKING',VERIFYING:'WORKING',DONE:'IDLE',WAITING_APPROVAL:'IDLE'}[value]??(['IDLE','LISTENING','THINKING','SPEAKING','WORKING','ERROR'].includes(value)?value:'IDLE')) as CoreState;
export type Native={send:(text:string)=>void;action:(name:string)=>void;videoRequest?:(action:string,source:string)=>void;devRequest?:(prompt:string,target:string)=>void;devRefresh?:()=>void;devVerify?:(id:string)=>void;devInstall?:(id:string)=>void;openChatGPT?:(handoff:string)=>void;hologramAction?:(name:string)=>void;ready:()=>void;message:{connect:(fn:(data:string)=>void)=>void;disconnect?:(fn:(data:string)=>void)=>void}};
declare global {interface Window {qt?:{webChannelTransport:unknown};QWebChannel?:new(transport:unknown,callback:(channel:{objects:{mark:Native}})=>void)=>unknown;}}
export async function request(path:string,body?:unknown,signal?:AbortSignal){
 const res=await fetch(path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:signal??AbortSignal.timeout(200000)});
 const data=await res.json();if(!res.ok||data.ok===false)throw Error(data.error||`HTTP ${res.status}`);return data;
}
export type DevRequest={id:string;prompt:string;target:'phone'|'desktop'|'both';status:string;handoff:string;commit_sha?:string;verified_cloud?:boolean;verified_tests?:boolean};
export type Message={role:'user'|'assistant';text:string;id:number;time:number;cloudId?:number};
export function useUltron(){
 const [connected,setConnected]=useState(false),[system,setSystem]=useState<SystemSnapshot|null>(null),[ai,setAi]=useState<AIStatus|null>(null);
 const [state,setState]=useState<CoreState>('IDLE'),[nativeState,setNativeState]=useState<CoreState>('IDLE'),[amplitude,setAmplitude]=useState(0),[muted,setMuted]=useState(true),[native,setNative]=useState<Native|null>(null);
 const [devRequests,setDevRequests]=useState<DevRequest[]>([]);
 const [messages,setMessages]=useState<Message[]>([]),[pending,setPending]=useState<TaskProposal|null>(null),[patch,setPatch]=useState<PatchProposal|null>(null),[notice,setNotice]=useState(''),[notifications,setNotifications]=useState<any[]>([]);
 const [health,setHealth]=useState<any>(null),[tools,setTools]=useState<any[]>([]),[memory,setMemory]=useState<any>(null),[plugins,setPlugins]=useState<any[]|null>(null),[history,setHistory]=useState<SystemSnapshot[]>([]),[taskState,setTaskState]=useState<CoreState>('IDLE'),[devicePresence,setDevicePresence]=useState<any[]>([]),[stage,setStage]=useState<StageState>(defaultStage);
 const cloudKnown=useRef<Set<number>>(new Set());
 const add=(role:Message['role'],text:string)=>setMessages(p=>[...p,{role,text,id:Date.now()+Math.random(),time:Date.now()}].slice(-300));
 const mergeCloud=(rows:any[])=>setMessages(previous=>{
  const next=[...previous];
  for(const row of Array.isArray(rows)?rows:[]){
   const cloudId=Number(row?.id);
   const role:Message['role']|null=row?.role==='user'?'user':row?.role==='assistant'?'assistant':null;
   const text=String(row?.content??'').trim();
   if(!Number.isFinite(cloudId)||!role||!text||cloudKnown.current.has(cloudId))continue;
   cloudKnown.current.add(cloudId);
   const parsed=Date.parse(String(row?.created_at??''));
   const time=Number.isFinite(parsed)?parsed:Date.now();
   const match=next.findIndex(m=>m.cloudId===undefined&&m.role===role&&m.text===text&&Math.abs(m.time-time)<120000);
   if(match>=0)next[match]={...next[match],cloudId,time};
   else next.push({role,text,id:-cloudId,time,cloudId});
  }
  next.sort((a,b)=>a.time-b.time||a.id-b.id);
  return next.slice(-300);
 });
 useEffect(()=>{if(system)setHistory(p=>[...p,system].slice(-40));},[system]);
 useEffect(()=>{let active=true;const ctl=new AbortController();const poll=()=>{if(location.protocol==='file:')return;request('/api/merged/health',undefined,ctl.signal).then(h=>{if(active)setHealth(h);}).catch(()=>{if(active)setHealth(null);});};poll();const t=setInterval(poll,8000);return()=>{active=false;ctl.abort();clearInterval(t);};},[]);
 useEffect(()=>{
  let stopped=false,ws:WebSocket|null=null,retry:ReturnType<typeof setTimeout>|undefined,delay=1000;
  const open=()=>{if(stopped||!location.host)return;ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`);
   ws.onopen=()=>{delay=1000;setConnected(true);};
   ws.onmessage=e=>{if(stopped)return;let m;try{m=JSON.parse(e.data);}catch{return;}
    if(m.type==='hello'){setSystem(m.system);setAi(m.ai);setState(coreState(m.agent?.state));setNotifications(m.notifications??[]);setTools(m.tools??[]);setMemory(m.memory);if(m.stage)setStage(m.stage);}
    if(m.type==='tools')setTools(m.data??[]);if(m.type==='memory')setMemory(m.data);
    if(m.type==='task_engine'){const status=m.data?.status??'';setTaskState(previous=>/START|RUNNING|STEP_START/.test(status)?'WORKING':/COMPLETE|FAILED|CANCELLED|PAUSED|APPROVAL/.test(status)?'IDLE':previous);setStage(previous=>{if(/START|RUNNING|STEP_START/.test(status)&&previous.mode==='core_idle')return {...previous,mode:'task_progress',title:String(m.data?.goal||m.data?.message||'GÖREV ÇALIŞIYOR').slice(0,100),subtitle:String(m.data?.message||status).slice(0,140),progress:Number(m.data?.percent??m.data?.progress??previous.progress??0)};if(/COMPLETE|FAILED|CANCELLED/.test(status)&&previous.mode==='task_progress')return {...defaultStage,revision:previous.revision+1};return previous;});}
    if(m.type==='system')setSystem(m.data);if(m.type==='ai')setAi(m.data);
    if(m.type==='agent'){setState(coreState(m.state));if(['DONE','ERROR'].includes(m.state)&&m.message)add('assistant',m.message);}
    if(m.type==='task')setPending(m.data);if(m.type==='patch')setPatch(m.data);
    if(m.type==='notifications')setNotifications(m.data??[]);
    if(m.type==='stage'&&m.data)setStage(m.data);
    if(m.type==='proactive_speech')add('assistant',m.text);
   };
   ws.onclose=()=>{if(stopped)return;setConnected(false);setSystem(null);setAi(null);setMemory(null);setTools([]);setTaskState('IDLE');retry=setTimeout(open,delay);delay=Math.min(delay*1.7,10000);};ws.onerror=()=>ws?.close();
  };open();
  const ctl=new AbortController();
  request('/api/task/pending',undefined,ctl.signal).then(p=>setPending(p.id?p:null)).catch(()=>{});
  request('/api/codegen/pending',undefined,ctl.signal).then(p=>setPatch(p.id?p:null)).catch(()=>{});
  request('/api/stage',undefined,ctl.signal).then(s=>{if(s?.mode)setStage(s);}).catch(()=>{});
  return()=>{stopped=true;ctl.abort();clearTimeout(retry);if(ws){ws.onclose=null;ws.close();}};
 },[]);
 useEffect(()=>{if(!window.qt)return;let active=true,bridge:Native|undefined;const receive=(raw:string)=>{if(!active)return;let e:any;try{e=JSON.parse(raw);}catch{return;}if(e.kind==='video_notice'){setNotice(String(e.text||'MARK video işlemi tamamlandı.'));}
   if(e.kind==='dev_requests')setDevRequests(Array.isArray(e.data)?e.data:[]);
   if(e.kind==='dev_request_created'&&e.data){setDevRequests(prev=>[e.data,...prev.filter(t=>t.id!==e.data.id)]);setNotice('Geliştirme isteği kaydedildi. GELİŞTİR ekranından ChatGPT’ye gönder.');}
   if(e.kind==='dev_verified'&&e.data){setDevRequests(prev=>prev.map(t=>t.id===e.data.id?e.data:t));if(e.data.status==='completed'){setNotice('Tamam efendim, doğrulanmış güncelleme tamamlandı.');add('assistant','Tamam efendim, güncelleme tamamlandı.');}else setNotice('Güncelleme durumu: '+String(e.data.status));}
   if(e.kind==='dev_install_result'&&e.data?.restart_required){setNotice('Güncelleme dosyaları hazır. Kurulu sürümün etkinleşmesi için ULTRON’u yeniden başlat.');}
   if(e.kind==='dev_notice'||e.kind==='dev_error')setNotice(String(e.text||''));
   if(e.kind==='state'){setNativeState(coreState(e.state));setMuted(e.muted);setAmplitude(Number(e.amplitude)||0);}if(e.kind==='file')setNotice(e.name+' ses motoruna eklendi.');if(e.kind==='plugins')setPlugins(e.data);if(e.kind==='cloud_messages')mergeCloud(e.data??[]);if(e.kind==='device_presence')setDevicePresence(e.data??[]);if(e.kind==='remote_notice')setNotice(e.text);if(e.kind==='log')add(e.role,e.text);if(e.kind==='error'){setNotice(e.text);setNativeState('ERROR');}};
  const script=document.createElement('script');script.src='qrc:///qtwebchannel/qwebchannel.js';script.onload=()=>{if(window.QWebChannel)new window.QWebChannel(window.qt!.webChannelTransport,c=>{if(!active)return;bridge=c.objects.mark;setNative(bridge);bridge.message.connect(receive);bridge.ready();});};document.head.appendChild(script);
  return()=>{active=false;bridge?.message.disconnect?.(receive);script.remove();};
 },[]);
 return {devRequests,health,tools,memory,plugins,history,taskState,devicePresence,stage,setStage,connected,system,ai,state,nativeState,amplitude,muted,native,messages,setMessages,add,pending,setPending,patch,setPatch,notice,setNotice,notifications};
}
