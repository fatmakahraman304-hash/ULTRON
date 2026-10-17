/** Safe clickable research links; text stays text, never executable markup. */
export function sourceUrl(value:string):string|null{
 try{const u=new URL(value);if(!['https:','http:'].includes(u.protocol)||u.username||u.password||!u.hostname.includes('.')||/[<>"`\\\s]/.test(value))return null;
 if((u.port&&!['80','443'].includes(u.port))||/^(?:127\.|10\.|192\.168\.|169\.254\.|172\.(?:1[6-9]|2\d|3[01])\.|0\.)/.test(u.hostname)||/\.(?:local|internal|localhost)$/.test(u.hostname))return null;
 return u.href;}catch{return null;}
}
export function sourceParts(text:string):{text:string;href?:string}[]{
 const pieces:{text:string;href?:string}[]=[];
 const pattern=/\[([^\]\n]+)\]\((https?:\/\/[^\s<>]+)\)|(https?:\/\/[^\s<>]+)/g;
 let last=0;
 for(const match of text.matchAll(pattern)){
  const start=match.index!;if(start>last)pieces.push({text:text.slice(last,start)});
  const raw=match[2]||match[3];const url=raw.replace(/[.,;!?)]+$/,'');
  const href=sourceUrl(url);pieces.push({text:match[1]||url,...(href?{href}:{})});
  if(!match[1]&&raw.length>url.length)pieces.push({text:raw.slice(url.length)});
  last=start+match[0].length;
 }
 if(last<text.length)pieces.push({text:text.slice(last)});
 return pieces;
}
export function researchMeta(value:unknown):{search_suggestions_html?:string}|undefined{
 try{const r=typeof value==='string'?JSON.parse(value):value;
 return r&&typeof r==='object'?r:undefined;}catch{return undefined;}
}
export function searchWidgetDocument(html:string):string{
 return '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data: https://www.gstatic.com; base-uri \'none\'; form-action \'none\'">'+html.slice(0,50000);
}
