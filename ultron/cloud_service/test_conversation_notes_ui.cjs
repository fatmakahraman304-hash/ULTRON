"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const notes=require("./static/conversation-notes.js");
const CID="11111111-1111-4111-8111-111111111111";
function fixture(){
 class N {
  constructor(){this.children=[];this.listeners={};this.textContent="";this.value="";this.disabled=false;this.className=""}
  addEventListener(k,fn){this.listeners[k]=fn}
  append(...xs){this.children.push(...xs)}
  appendChild(x){this.children.push(x);return x}
  replaceChildren(...xs){this.children=xs}
 }
 const ids=["previewConversationNote","saveConversationNote","refreshConversationNotes",
  "cancelConversationNote","conversationNotesStatus","conversationNoteTitle",
  "conversationNoteBody","conversationNotesList"];
 const nodes=Object.fromEntries(ids.map(id=>[id,new N()]));
 const document={getElementById:id=>nodes[id]||null,createElement:()=>new N()};
 return {document,nodes};
}
test("no API on mount and regular conversation stays untouched",async()=>{
 const {document,nodes}=fixture(),calls=[];
 const ui=notes.create({document,fetchJson:async(...args)=>{calls.push(args);return{}},
 getConversationId:()=>CID,openMemory:()=>{}});
 assert.equal(ui.init(),true);
 assert.deepEqual(calls,[]);
 for(const input of ["Merhaba","Sohbeti özetle","Dünyayı aç","Kitaptan not çıkar"])
  assert.equal(ui.runCommand(input),false,input);
 assert.equal(notes.draftIntent("Sohbet notu hazırla"),true);
 assert.equal(notes.listIntent("Notlarımı göster"),true);
});
test("explicit note draft is editable; POST only when save tapped",async()=>{
 const {document,nodes}=fixture(),calls=[];let opened=0;
 const ui=notes.create({document,getConversationId:()=>CID,openMemory:()=>opened++,
 fetchJson:async(url,opt)=>{
  calls.push([url,opt]);
  if(url.includes("/preview"))return {draft:{title:"Taslak",body:"<img src=x onerror=evil()>"}};
  if(opt?.method==="POST")return {note_id:7,saved:true};
  return {notes:[]};
 }});
 ui.init();assert.equal(ui.runCommand("Sohbet notu hazırla"),true);
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(opened,1);
 assert.equal(calls.length,1);
 assert.equal(nodes.conversationNoteBody.value,"<img src=x onerror=evil()>");
 assert.match(nodes.conversationNotesStatus.textContent,/KAYDET demeden/);
 nodes.conversationNoteBody.value="Sadece uygun not";
 await nodes.saveConversationNote.listeners.click();
 assert.equal(calls[1][1].method,"POST");
 assert.deepEqual(JSON.parse(calls[1][1].body),{
  conversation_id:CID,title:"Taslak",body:"Sadece uygun not"
 });
 assert.equal(calls[2][0],"/api/conversation-notes?conversation_id="+CID);
});
test("render with textContent, edit only on save, delete confirmation",async()=>{
 const {document,nodes}=fixture(),calls=[];
 let yes=false;
 const item={id:17,title:"<svg/onload=evil()>",body:"<script>attack()</script>"};
 const ui=notes.create({document,getConversationId:()=>CID,confirmDelete:()=>yes,
 fetchJson:async(url,opt)=>{
  calls.push([url,opt]);
  return opt?.method==="PUT"||opt?.method==="DELETE"?{saved:true}:{notes:[item]};
 }});
 ui.init();await nodes.refreshConversationNotes.listeners.click();
 const card=nodes.conversationNotesList.children[0];
 assert.equal(card.children[0].textContent,item.title);
 assert.equal(card.children[1].textContent,item.body);
 const actions=card.children[2];
 await actions.children[0].listeners.click();
 assert.equal(calls.length,1);
 assert.equal(nodes.conversationNoteTitle.value,item.title);
 nodes.conversationNoteBody.value="Edited";
 await nodes.saveConversationNote.listeners.click();
 assert.equal(calls[1][1].method,"PUT");
 assert.equal(calls[1][0],"/api/conversation-notes/17");
 await actions.children[1].listeners.click();
 assert.equal(calls.filter(x=>x[1]?.method==="DELETE").length,0);
 yes=true;await actions.children[1].listeners.click();
 assert.equal(calls.filter(x=>x[1]?.method==="DELETE").length,1);
 assert.equal(fs.readFileSync(path.join(__dirname,"static/conversation-notes.js"),"utf8").includes(".innerHTML"),false);
});
test("no prior conversation means no API; PWA UI hidden until command",async()=>{
 const {document,nodes}=fixture(),calls=[];
 const ui=notes.create({document,getConversationId:()=>"",openMemory:()=>{},
 fetchJson:async(...xs)=>{calls.push(xs);return{};}});
 ui.init();await nodes.previewConversationNote.listeners.click();
 assert.equal(calls.length,0);
 assert.match(nodes.conversationNotesStatus.textContent,/Önce/);
 const html=fs.readFileSync(path.join(__dirname,"static/index.html"),"utf8");
 const sw=fs.readFileSync(path.join(__dirname,"static/sw.js"),"utf8");
 assert.ok(html.includes('id="conversationNotesPanel"'));
 assert.ok(html.includes("conversationNotesController?.runCommand(text)"));
 assert.ok(html.includes("conversationNotesController?.init()"));
 assert.ok(sw.includes("'/static/conversation-notes.js'"));
 const scripts=[...html.matchAll(/<script(?:\s+[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).filter(Boolean);
 for(const code of scripts)assert.doesNotThrow(()=>new vm.Script(code));
});
