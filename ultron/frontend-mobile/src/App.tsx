import { lazy, Suspense } from 'react';
import Cockpit from '../../frontend/src/cockpit/Cockpit';
const Legacy=lazy(()=>import('./LegacyApp'));
export type Page = 'home' | 'chat' | 'voice' | 'vision' | 'more';
export default function App(){return location.search.includes('legacy=1')?<Suspense fallback={<p>Yükleniyor…</p>}><Legacy/><button style={{position:'fixed',top:50,right:12,zIndex:9999,padding:8,background:'#181d24',color:'white',border:'1px solid #66313e'}} onClick={()=>location.assign('/frontend-mobile/index.html')}>← Yeni arayüz</button></Suspense>:<Cockpit mobile/>;}
