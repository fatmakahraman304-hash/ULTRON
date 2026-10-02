import { useEffect, useRef } from 'react';

export function OrbitalCore({accent, brightness, motion, avatar, tracking, speaking}:{accent:string;brightness:number;motion:boolean;avatar:boolean;tracking:boolean;speaking:boolean}) {
  const ref=useRef<HTMLCanvasElement>(null);
  useEffect(()=>{
    const canvas=ref.current!;const ctx=canvas.getContext('2d')!;let raf=0,frame=0;
    let w=600,h=620,px=0,py=0;
    const resize=new ResizeObserver(entries=>{const r=entries[0].contentRect;w=r.width;h=r.height;const d=Math.min(devicePixelRatio,2);canvas.width=w*d;canvas.height=h*d;ctx.setTransform(d,0,0,d,0,0);});resize.observe(canvas);
    const point=(e:PointerEvent)=>{const box=canvas.getBoundingClientRect();px=(e.clientX-box.left)/w-.5;py=(e.clientY-box.top)/h-.5;};canvas.addEventListener('pointermove',point);
    let seed=113;const rand=()=>{seed=(seed*16807)%2147483647;return seed/2147483647;};
    const stars=Array.from({length:1600},()=>({a:rand()*Math.PI*2,r:.94+rand()*.76,z:rand(),speed:.3+rand()*.7}));
    const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
    const draw=()=>{
      frame++;const t=motion&&!reduced?performance.now()/1000:0;
      ctx.clearRect(0,0,w,h);const r=Math.min(w*.245,h*.23),cx=w/2+(tracking?px*10:0),cy=h*.42+(tracking?py*7:0),floor=cy+r*1.95;
      const ellipse=(x:number,y:number,rx:number,ry:number,rotation:number,color:string,width=1)=>{ctx.beginPath();ctx.ellipse(x,y,rx,ry,rotation,0,Math.PI*2);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke();};
      ctx.globalAlpha=brightness;
      const aura=ctx.createRadialGradient(cx,cy,0,cx,cy,r*2.4);aura.addColorStop(0,accent+'26');aura.addColorStop(.55,accent+'12');aura.addColorStop(1,'transparent');ctx.fillStyle=aura;ctx.fillRect(0,0,w,h);
      // Etched reticle: rings, degree ticks and crosshair keep the core grounded.
      for(let i=0;i<5;i++)ellipse(cx,cy,r*(1.42+i*.15),r*(1.42+i*.15),0,i%2?accent+'18':'#85939919');
      for(let i=0;i<120;i++){const a=i*Math.PI/60;ctx.beginPath();ctx.moveTo(cx+Math.cos(a)*r*2.02,cy+Math.sin(a)*r*2.02);ctx.lineTo(cx+Math.cos(a)*r*(i%5?2.04:2.1),cy+Math.sin(a)*r*(i%5?2.04:2.1));ctx.strokeStyle=i%5?'#85939925':accent+'60';ctx.lineWidth=1;ctx.stroke();}
      ctx.strokeStyle=accent+'35';ctx.beginPath();ctx.moveTo(cx,5);ctx.lineTo(cx,h*.83);ctx.moveTo(15,cy);ctx.lineTo(w-15,cy);ctx.stroke();
      // Metal pedestal and a narrow energy column.
      const base=ctx.createLinearGradient(0,floor-20,0,floor+50);base.addColorStop(0,'#65717b');base.addColorStop(.2,'#101318');base.addColorStop(.7,'#020305');base.addColorStop(1,'#343a40');
      ctx.fillStyle=base;ctx.beginPath();ctx.ellipse(cx,floor+13,r*1.73,r*.34,0,0,Math.PI*2);ctx.fill();
      for(let i=0;i<7;i++)ellipse(cx,floor,r*(1.73-i*.15),r*(.34-i*.027),0,i===3?accent:(i===0?'#66707b':'#41474d'),i===3?3:1.4);
      ctx.save();ctx.shadowColor=accent;ctx.shadowBlur=24;ellipse(cx,floor,r*.61,r*.12,0,accent,3);ellipse(cx,floor,r*.2,r*.055,0,'#fff1ef',2);
      const beam=ctx.createLinearGradient(cx-12,0,cx+12,0);beam.addColorStop(0,accent+'00');beam.addColorStop(.4,accent+'99');beam.addColorStop(.5,'#fff6f2');beam.addColorStop(.6,accent+'99');beam.addColorStop(1,accent+'00');ctx.fillStyle=beam;ctx.fillRect(cx-12,cy+r*.7,24,floor-cy-r*.7);ctx.restore();
      // The satellite belt has depth, rotating around the central sphere.
      for(const star of stars){const a=star.a+t*.09*star.speed;const rr=r*star.r;const x=cx+Math.cos(a)*rr;const y=cy+Math.sin(a)*rr*.94;const sparkle=.25+.75*Math.sin(a*11+t*star.speed)**2;ctx.globalAlpha=brightness*sparkle;ctx.fillStyle=star.z>.96?'#fff4ed':accent;ctx.fillRect(x,y,star.z> .94?2.2:1,star.z>.94?2.2:1);}
      ctx.globalAlpha=brightness;
      ellipse(cx,cy,r*1.65,r*.37,-.38,accent+'99',1);ellipse(cx,cy,r*1.74,r*.54,.48,'#adb1b075',1);
      if(!avatar){
        const sphere=ctx.createRadialGradient(cx-r*.35,cy-r*.5,2,cx,cy,r);sphere.addColorStop(0,'#d7dddf');sphere.addColorStop(.14,'#575e65');sphere.addColorStop(.42,'#15191f');sphere.addColorStop(.76,'#090c12');sphere.addColorStop(1,accent+'bb');
        ctx.save();ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.fillStyle=sphere;ctx.fill();ctx.clip();
        for(let i=0;i<23;i++){const a=i/23*Math.PI+t*.07;ellipse(cx,cy,Math.abs(Math.cos(a))*r,r,.25,'#bac4cc26',.8);ellipse(cx,cy+(i/23-.5)*r*2,Math.sqrt(Math.max(0,1-(i/23*2-1)**2))*r,r*.14,.15,accent+'45',.6);}
        for(let i=0;i<260;i++){const a=i*2.39996+t*.1,z=1-2*i/260,s=Math.sqrt(1-z*z);const x=cx+Math.cos(a)*s*r,y=cy+z*r;if(Math.sin(a)>0){ctx.fillStyle=i%4?accent:'#eeeeee';ctx.fillRect(x,y,1.4,1.4);}}
        const fire=ctx.createRadialGradient(cx,cy+8,0,cx,cy+8,r*.72);fire.addColorStop(0,'#fffdf0');fire.addColorStop(.06,'#ffffff');fire.addColorStop(.16,accent);fire.addColorStop(.5,accent+'66');fire.addColorStop(1,accent+'00');ctx.fillStyle=fire;ctx.fillRect(cx-r,cy-r,r*2,r*2);ctx.restore();
      }
      // Foreground metallic rings and point lights.
      ctx.save();ctx.shadowColor=accent;ctx.shadowBlur=14;ellipse(cx,cy,r*1.5,r*.43,-.28,'#d6d8d9',3);ellipse(cx,cy,r*1.51,r*.43,-.28,accent+'cc',1);ellipse(cx,cy,r*1.8,r*.56,-.64,accent,1);
      for(let i=0;i<4;i++){const a=t*.25+i*1.7;const x=cx+Math.cos(a)*r*1.7,y=cy+Math.sin(a)*r*.6;ctx.fillStyle='#fff6eb';ctx.beginPath();ctx.arc(x,y,2.6,0,Math.PI*2);ctx.fill();}ctx.restore();
      ctx.save();ctx.shadowColor=accent;ctx.shadowBlur=25;ctx.fillStyle=accent+'99';ctx.fillRect(cx-r*1.9,cy,3.8*r,1);ctx.restore();
      if(!document.hidden)raf=requestAnimationFrame(draw);else raf=window.setTimeout(draw,150) as unknown as number;
    };draw();return()=>{cancelAnimationFrame(raf);clearTimeout(raf);resize.disconnect();canvas.removeEventListener('pointermove',point);};
  },[accent,brightness,motion,avatar,tracking]);
  return <div className="orbital-render"><canvas ref={ref} aria-label="Animasyonlu ULTRON enerji çekirdeği" />{avatar&&<svg className={'core-avatar '+(speaking?'speaking':'')} viewBox="0 0 240 290" aria-label="ULTRON robot avatarı"><defs><linearGradient id="metal"><stop stopColor="#090c10"/><stop offset=".42" stopColor="#626972"/><stop offset=".52" stopColor="#151a21"/><stop offset=".8" stopColor="#424952"/><stop offset="1" stopColor="#070a0e"/></linearGradient></defs><path d="M35 82 58 27 97 9 142 9 183 28 206 82 193 190 159 250 120 278 78 253 44 194Z" fill="url(#metal)" stroke="#777e87"/><path d="M64 32 87 104 108 126 106 16M176 32 153 104 132 126 134 16M40 98 71 115 89 161 66 177 45 139M201 98 170 115 151 161 174 177 195 139" fill="#070b0f" stroke="#aab0b855"/><path d="m57 123 44 17-8 14-31-13Zm126 0-44 17 8 14 31-13Z" fill="var(--accent)" className="avatar-eyes"/><path d="m111 129-13 71 22 12 22-12-13-71M74 184 83 220 109 246 120 254 132 246 158 219 167 184" fill="#171d24" stroke="#727981"/><path className="avatar-mouth" d="M99 225h42M105 234h30" stroke="var(--accent)" strokeWidth="3"/><path d="m47 193 33 2m80 0 33-2M113 27v57m14-57v57" stroke="var(--accent)" opacity=".6"/></svg>}</div>;
}
