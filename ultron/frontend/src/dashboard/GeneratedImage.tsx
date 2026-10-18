import {useState,useEffect,useRef} from 'react';
export default function GeneratedImage({id}:{id:number}){
 const [failed,setFailed]=useState(false),[open,setOpen]=useState(false),[notice,setNotice]=useState(''),[zoom,setZoom]=useState(1);
 const dialog=useRef<HTMLDialogElement>(null);
 useEffect(()=>{if(open)dialog.current?.showModal();},[open]);
 if(!Number.isSafeInteger(id)||id<=0)return null;
 const url='/api/merged/image-studio/generated/'+id;
 if(failed)return <p>Görsel bulunamadı veya 30 günlük saklama süresi doldu.</p>;
 const share=async()=>{try{const r=await fetch(url);if(!r.ok)throw Error();const blob=await r.blob();const file=new File([blob],'golge-gorsel.png',{type:blob.type});if(navigator.canShare?.({files:[file]}))await navigator.share({files:[file]});else setNotice('Paylaşım desteklenmiyor; İndir seçeneğini kullanın.');}catch{setNotice('Paylaşım tamamlanamadı.');}};
 return <figure className="generated-image" style={{margin:0}}><button onClick={()=>setOpen(true)} aria-label="Görseli büyüt"><img src={url} alt="GÖLGE tarafından üretilen görsel" loading="lazy" onError={()=>setFailed(true)} style={{maxWidth:'100%',maxHeight:'50vh',borderRadius:12}}/></button><div><a href={url} download>Görseli indir / kaydet</a> <button onClick={()=>void share()}>Paylaş</button></div>{notice&&<p role="status">{notice}</p>}{open&&<dialog ref={dialog} onClose={()=>setOpen(false)} aria-label="Görselin tam boy görünümü" style={{position:'fixed',inset:20,zIndex:2000,maxWidth:'95vw',maxHeight:'95vh',overflow:'auto',background:'#071522',color:'white'}}><button autoFocus onClick={()=>setOpen(false)}>Kapat</button><label>Yakınlaştır <input aria-label="Görsel yakınlaştırma" type="range" min="1" max="3" step="0.25" value={zoom} onChange={e=>setZoom(Number(e.target.value))}/></label><img src={url} alt="Üretilen görsel — tam boy" style={{width:`${zoom*100}%`,maxWidth:'none'}}/></dialog>}</figure>;
}
