import {useEffect,useRef,useState} from 'react';
import {CoreScene} from './CoreScene';
import type {CoreState} from '../runtime';
export default function UltronCore({state,amplitude}:{state:CoreState;amplitude:number}){
 const host=useRef<HTMLDivElement>(null),scene=useRef<CoreScene|null>(null),[error,setError]=useState('');
 useEffect(()=>{try{scene.current=new CoreScene(host.current!);}catch{setError('WebGL kullanılamıyor. Ekran kartı sürücüsünü kontrol edin.');}return()=>{scene.current?.dispose();scene.current=null;};},[]);
 useEffect(()=>scene.current?.setState(state,amplitude),[state,amplitude]);
 return <div className="core-stage"><div className="core-coordinates"><span>ULTRON / NEURAL ENGINE</span><span>REALTIME 3D</span></div><div ref={host} className="core-canvas"/>{error&&<p role="alert">{error}</p>}<div className="core-caption"><span className="status-dot"/>{state}<small>ULTRON CORE</small></div></div>;
}
