import {useState,type ReactNode} from 'react';
import {Check,Copy} from 'lucide-react';

function inline(text:string){
 return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part,index)=>{
  if(part.startsWith('**')&&part.endsWith('**'))return <strong key={index}>{part.slice(2,-2)}</strong>;
  if(part.startsWith('`')&&part.endsWith('`'))return <code key={index}>{part.slice(1,-1)}</code>;
  return <span key={index}>{part}</span>;
 });
}
function CodeBlock({language,code}:{language:string;code:string}){
 const [copied,setCopied]=useState(false);
 const copy=async()=>{try{await navigator.clipboard.writeText(code);setCopied(true);window.setTimeout(()=>setCopied(false),1400);}catch{setCopied(false);}};
 return <div className="message-code"><header><span>{language||'Kod'}</span><button aria-label="Kod bloğunu kopyala" disabled={!navigator.clipboard} onClick={()=>void copy()}>{copied?<Check/>:<Copy/>}{copied?'Kopyalandı':'Kopyala'}</button></header><pre><code>{code}</code></pre></div>;
}
export default function MessageText({text}:{text:string}){
 const parts=String(text||'').split(/```([^\n`]*)\n([\s\S]*?)```/g);
 const output=[] as ReactNode[];
 for(let i=0;i<parts.length;i+=3){
  const prose=parts[i]||'';
  if(prose)output.push(<div className="message-prose" key={`p-${i}`}>{prose.split(/\n{2,}/).map((paragraph,j)=><p key={j}>{paragraph.split('\n').map((line,k)=><span key={k}>{k>0&&<br/>}{inline(line)}</span>)}</p>)}</div>);
  if(i+1<parts.length)output.push(<CodeBlock key={`c-${i}`} language={parts[i+1].trim()} code={parts[i+2]||''}/>);
 }
 return <div className="message-text">{output}</div>;
}
