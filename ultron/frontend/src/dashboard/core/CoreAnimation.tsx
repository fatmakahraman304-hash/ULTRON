import {useState} from 'react';
import {RotateCcw,X} from 'lucide-react';

/** Bounded, fully in-Center-Stage animation, never a separate OS/Pygame window. */
export default function CoreAnimation({kind,title,onClose}:{kind:string;title:string;onClose:()=>void}){
 const [paused,setPaused]=useState(false);
 const safeKind=['bird','orbit','pulse'].includes(kind)?kind:'bird';
 return <section className={'ultron-inline-animation '+(paused?'paused':'')} aria-label="ULTRON animasyon önizleme">
  <header><span>ULTRON / CORE ANIMATION</span><div><button onClick={()=>setPaused(x=>!x)}>{paused?'OYNAT':'DURAKLAT'}</button><button aria-label="Animasyonu kapat" onClick={onClose}><X size={16}/></button></div></header>
  <div className={'ultron-inline-animation-canvas theme-'+safeKind}>
   {safeKind==='bird'?<div className="ultron-bird" role="img" aria-label="Kanat çırpan sarı kuş">
    <span className="wing left"/><span className="wing right"/><span className="bird-body"><span className="eye"/><span className="beak"/></span>
   </div>:safeKind==='orbit'?<div className="ultron-orbit" role="img" aria-label="Dönen enerji yörüngeleri"><i/><i/><i/></div>:<div className="ultron-pulse" role="img" aria-label="Enerji nabzı"><i/><i/><i/></div>}
  </div>
  <footer><b>{String(title||'KÜÇÜK ANİMASYON').slice(0,72)}</b><span><RotateCcw size={12}/> CORE İÇİNDE • BOYUTA DUYARLI</span></footer>
 </section>;
}
