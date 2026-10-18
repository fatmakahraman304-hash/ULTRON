/* Render plain citations and isolated Google suggestion metadata without innerHTML. */
(function(root,factory){const api=factory();if(typeof module!=='undefined'&&module.exports)module.exports=api;if(root)root.GolgeSourceLinks=api;})(typeof window!=='undefined'?window:null,function(){
 'use strict';
 function url(value){try{const u=new URL(value);return ['https:','http:'].includes(u.protocol)&&!u.username&&!u.password&&(!u.port||['80','443'].includes(u.port))&&u.hostname.includes('.')&&!/[<>"`\\\s]/.test(value)&&! /^(?:127\.|10\.|192\.168\.|169\.254\.|172\.(?:1[6-9]|2\d|3[01])\.|0\.)/.test(u.hostname)&&! /\.(?:local|internal|localhost)$/.test(u.hostname)?u.href:null;}catch{return null;}}
 function render(target,text){
  const pattern=/\[([^\]\n]+)\]\((https?:\/\/[^\s<>]+)\)|(https?:\/\/[^\s<>]+)/g;let last=0;
  for(const m of String(text).matchAll(pattern)){target.append(document.createTextNode(text.slice(last,m.index)));const raw=m[2]||m[3],href=raw.replace(/[.,;!?)]+$/,'');const safe=url(href);
   if(safe){const a=document.createElement('a');a.href=safe;a.target='_blank';a.rel='noopener noreferrer';a.textContent=m[1]||href;target.append(a)}else target.append(document.createTextNode(m[1]||href));
   if(!m[1])target.append(document.createTextNode(raw.slice(href.length)));last=m.index+m[0].length;
  }target.append(document.createTextNode(text.slice(last)));
 }
 function widget(target,value){let r=value;try{if(typeof r==='string')r=JSON.parse(r);}catch{return}
  const html=r?.search_suggestions_html;if(typeof html!=='string'||!html||html.length>50000)return;
  const frame=document.createElement('iframe');frame.title='Google arama önerileri';frame.setAttribute('sandbox','allow-popups allow-popups-to-escape-sandbox');frame.referrerPolicy='no-referrer';
  frame.srcdoc='<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data: https://www.gstatic.com; base-uri \'none\'; form-action \'none\'">'+html;
  frame.style.cssText='display:block;width:100%;border:0;height:140px';target.append(frame);
 }
 return {url,render,widget};
});
