import {useLayoutEffect,useRef,useState,type MutableRefObject} from 'react';
import GolgeOrb from './GolgeOrb';
import {EarthWatch,type EarthView,type SceneTransition} from './EarthWatch';
import type {EarthSearch,PlaceHit} from './useEarthActions';
import type {CoreState,EarthState} from './runtime';
type Props={earth:boolean;config:EarthState;state:CoreState;amplitude:number;onCommand:(op:string,args?:Record<string,unknown>)=>unknown;viewMemory?:MutableRefObject<EarthView|null>;search?:EarthSearch|null;onChoose?:(hit:PlaceHit)=>unknown};
/** The outgoing GPU scene stays alive only for the bounded energy transition. */
export default function CoreEarthStage({earth,config,state,amplitude,onCommand,viewMemory,search,onChoose}:Props){
 const [shown,setShown]=useState({earth,core:!earth,transition:'stable' as SceneTransition}),first=useRef(true);
 useLayoutEffect(()=>{
  if(first.current){first.current=false;return;}
  setShown({earth:true,core:true,transition:earth?'enter':'exit'});
  const duration=window.matchMedia('(prefers-reduced-motion: reduce)').matches?0:1400;
  const timer=setTimeout(()=>setShown({earth,core:!earth,transition:'stable'}),duration);
  return()=>clearTimeout(timer);
 },[earth]);
 return <div className={'core-earth-workspace '+(earth?'show-earth':'show-core')} data-transition={shown.transition}>
  {shown.core&&<div className="core-scene-layer"><GolgeOrb state={state} amplitude={amplitude} transition={shown.transition==='stable'?'stable':earth?'exit':'enter'}/></div>}
  {shown.earth&&<div className={'earth-scene-layer '+(!earth?'leaving':'')}><EarthWatch config={config} onCommand={onCommand} viewMemory={viewMemory} transition={shown.transition} search={search} onChoose={onChoose}/></div>}
  {shown.transition!=='stable'&&<div className="scene-transfer-label" role="status">{earth?'DÜNYA GÖRÜNTÜSÜNE GEÇİLİYOR':'CORE YENİDEN ETKİNLEŞİYOR'}</div>}
 </div>;
}
