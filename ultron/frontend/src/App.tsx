import { lazy, Suspense } from 'react';
import Cockpit from './cockpit/Cockpit';
const Legacy=lazy(()=>import('./LegacyApp'));
export default function App(){return location.search.includes('legacy=1')?<Suspense fallback={<p>Yükleniyor…</p>}><Legacy/><button style={{position:'fixed',top:12,left:300,zIndex:9999,padding:10,background:'#181d24',color:'white',border:'1px solid #66313e'}} onClick={()=>location.assign('/frontend/index.html')}>← Yeni arayüz</button></Suspense>:<Cockpit/>;}
