import {useEffect,useState} from 'react';
import type {SystemSnapshot,AIStatus,TaskProposal,PatchProposal} from '../lib/types';
export type CoreState='IDLE'|'LISTENING'|'THINKING'|'SPEAKING'|'WORKING'|'ERROR';
export const coreState=(value:string):CoreState=>({PLANNING:'THINKING',EXECUTING:'WORKING',VERIFYING:'WORKING',DONE:'IDLE',WAITING_APPROVAL:'IDLE'}[value]??(['IDLE','LISTENING','THINKING','SPEAKING','WORKING','ERROR'].includes(value)?value:'IDLE')) as CoreState;
export type Native={send:(text:string)=>void;action:(name:string)=>void;hologramAction?:(name:string)=>void;ready:()=>void;message:{connect:(fn:(data:string)=>void)=>void;disconnect?:(fn:(data:string)=>void)=>void}};
declare global {interface Window {qt?:{webChannelTransport:unknown};QWebChannel?:new(transport:unknown,callback:(channel:{objects:{mark:Native}})=>void)=>unknown;}}
export async function request(path:string,body?:unknown,signal?:AbortSignal){
 const res=await fetch(path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:signal??AbortSignal.timeout(200000)});
 const data=await res.json();if(!res.ok||data.ok===false)throw Error(data.error||`HTTP ${res.status}`);return data;
}
export type Message={role:'user'|'assistant';text:string;id:number};
export function useUltron(){
 const [connected,setConnected]=useState(false),[system,setSystem]=useState<SystemSnapshot|null>(null),[ai,setAi]=useState<AIStatus|null>(null);
 const [state,setState]=useState<CoreState>('IDLE'),[nativeState,setNativeState]=useState<CoreState>('IDLE'),[amplitude,setAmplitude]=useState(0),[muted,setMuted]=useState(true),[native,setNative]=useState<Native|null>(null);
 const [messages,setMessages]=useState<Message[]>([]),[pending,setPending]=useState<TaskProposal|null>(null),[patch,setPatch]=useState<PatchProposal|null>(null),[notice,setNotice]=useState(''),[notifications,setNotifications]=useState<any[]>([]);
 const add=(role:Message['role'],text:string)=>setMessages(p=>[...p,{role,text,id:Date.now()+Math.random()}].slice(-300));
 useEffect(()=>{
  let stopped=false,ws:WebSocket|null=null,retry:ReturnType<typeof setTimeout>|undefined,delay=1000;
  const open=()=>{if(stopped||!location.host)return;ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`);
   ws.onopen=()=>{delay=1000;setConnected(true);};
   ws.onmessage=e=>{if(stopped)return;let m;try{m=JSON.parse(e.data);}catch{return;}
    if(m.type==='hello'){setSystem(m.system);setAi(m.ai);setState(coreState(m.agent?.state));setNotifications(m.notifications??[]);}
    if(m.type==='system')setSystem(m.data);if(m.type==='ai')setAi(m.data);
    if(m.type==='agent'){setState(coreState(m.state));if(['DONE','ERROR'].includes(m.state)&&m.message)add('assistant',m.message);}
    if(m.type==='task')setPending(m.data);if(m.type==='patch')setPatch(m.data);
    if(m.type==='notifications')setNotifications(m.data??[]);
    if(m.type==='proactive_speech')add('assistant',m.text);
   };
   ws.onclose=()=>{if(stopped)return;setConnected(false);setSystem(null);setAi(null);retry=setTimeout(open,delay);delay=Math.min(delay*1.7,10000);};ws.onerror=()=>ws?.close();
  };open();
  const ctl=new AbortController();
  request('/api/task/pending',undefined,ctl.signal).then(p=>setPending(p.id?p:null)).catch(()=>{});
  request('/api/codegen/pending',undefined,ctl.signal).then(p=>setPatch(p.id?p:null)).catch(()=>{});
  return()=>{stopped=true;ctl.abort();clearTimeout(retry);if(ws){ws.onclose=null;ws.close();}};
 },[]);
 useEffect(()=>{if(!window.qt)return;let active=true,bridge:Native|undefined;const receive=(raw:string)=>{if(!active)return;const e=JSON.parse(raw);if(e.kind==='state'){setNativeState(coreState(e.state));setMuted(e.muted);setAmplitude(Number(e.amplitude)||0);}if(e.kind==='log')add(e.role,e.text);if(e.kind==='error'){setNotice(e.text);setNativeState('ERROR');}};
  const script=document.createElement('script');script.src='qrc:///qtwebchannel/qwebchannel.js';script.onload=()=>{if(window.QWebChannel)new window.QWebChannel(window.qt!.webChannelTransport,c=>{if(!active)return;bridge=c.objects.mark;setNative(bridge);bridge.message.connect(receive);bridge.ready();});};document.head.appendChild(script);
  return()=>{active=false;bridge?.message.disconnect?.(receive);script.remove();};
 },[]);
 return {connected,system,ai,state,nativeState,amplitude,muted,native,messages,setMessages,add,pending,setPending,patch,setPatch,notice,setNotice,notifications};
}
