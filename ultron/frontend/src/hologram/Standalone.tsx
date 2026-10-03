import {useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import HologramLab from './HologramLab';
import '@fontsource/rajdhani/500.css';
function Standalone(){
 const [native,setNative]=useState<any>(null),[closed,setClosed]=useState(false),[notice,setNotice]=useState('');
 useEffect(()=>{if(!window.qt)return;let active=true;const script=document.createElement('script');script.src='qrc:///qtwebchannel/qwebchannel.js';script.onload=()=>{if(window.QWebChannel)new window.QWebChannel(window.qt!.webChannelTransport,channel=>{if(!active)return;const bridge=channel.objects.mark;setNative(bridge);bridge.message.connect(raw=>{if(!active)return;const event=JSON.parse(raw);if(event.kind==='log'&&event.role==='user')window.dispatchEvent(new CustomEvent('ultron-hologram-command',{detail:event.text}));});bridge.ready();});};document.head.appendChild(script);return()=>{active=false;script.remove();};},[]);
 const close=()=>native?native.hologramAction('close'):setClosed(true);
 return <>{closed?<main style={{color:'#6feaff',padding:40,fontFamily:'sans-serif'}}><h1>ULTRON hologramı kapatıldı</h1><button onClick={()=>setClosed(false)}>Yeniden aç</button></main>:<HologramLab accent="#00dfff" onClose={close} nativeAction={native?(name:string)=>native.hologramAction(name):undefined} onAsk={text=>{if(native)native.send(text);else setNotice('Açıklama istemek için masaüstü ULTRON sohbetini kullanın.');}}/>}{notice&&<p role="status" style={{position:'fixed',bottom:12,left:20,zIndex:100,color:'white'}}>{notice}</p>}</>;
}
createRoot(document.getElementById('root')!).render(<Standalone/>);
