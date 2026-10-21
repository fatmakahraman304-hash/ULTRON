/* Exercise the real inline send() implementation with a mocked UI/network. */
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const html=fs.readFileSync(__dirname+'/static/index.html','utf8');
const start=html.indexOf('async function send(fromVoice=');
const end=html.indexOf("$('#sendBtn').onclick",start);
if(start<0||end<start)throw new Error('ULTRON UI send() was not found');
const fn=html.slice(start,end);

function makeUI({message='Sesli oturumdan önemli talimat',fail=false,voiceError=false}={}){
  const box={value:message},busy={textContent:''},button={disabled:false,
    classList:{add(){},remove(){}},setAttribute(){}};
  const logs={api:0,panel:0,dev:0,direct:0,toast:[],messages:[]};
  const sandbox={
    console,AbortController,chatSending:false,chatSendVersion:0,chatRequestGeneration:0,activeChatRequest:null,
    pendingImage:null,pendingPdf:null,voiceEnabled:true,
    document:{hidden:false},conversationId:'thread-test',
    longListenController:{hasSession:()=>false,active:()=>false},
    knownMessageIds:new Set(),messageSignature:'',brainMode:'gemini',brainLastCheck:0,
    localStorage:{setItem(){}},voiceTurnGuard:{cancel(){},current:()=>true},
    $:selector=>selector==='#message'?box:selector==='#busy'?busy:selector==='#sendBtn'?button:undefined,
    isImageCreationRequest:text=>!!require('./static/image-intents.js').resolve(text),
    clearDraft(){},
    rememberPendingVoice(){},
    consumePendingVoice(){},
    addMessage(role,text){logs.messages.push({role,text});return {dataset:{}};},
    async handleSceneIntent(){logs.scene=(logs.scene||0)+1;return false;},
    handlePanelIntent(){logs.panel++;return true;},
    runDirectPhoneCommand(){logs.direct++;return true;},
    window:{
      ULTRONLongListen:{isStart:()=>false,isAnswer:()=>false},
      ULTRONLocalListeningProbe:{isRequest:()=>false},
      ULTRONDevRequests:{async fromText(){logs.dev++;return true;}},
      ULTRONAutoBrain:{safeToFallback:()=>false}
    },
    async refreshAutoBrain(){return 'gemini';},
    async locationForWeather(){return undefined;},
    async api(){logs.api++;if(fail){const e=new Error('offline');e.network=true;throw e;}
      return {reply:'Doğrulanmış asistan cevabı',conversation_id:'thread-test'};},
    speakUltron(){if(voiceError)throw new Error('speaker disconnected');},
    scrollChatToBottom(){},
    toast(msg){logs.toast.push(msg);}
  };
  sandbox.newChatIdentity=()=>({request_id:'test-request',request_key:'a'.repeat(64)});
  sandbox.mayFinalizeChatSend=generation=>generation===sandbox.chatRequestGeneration;
  vm.createContext(sandbox);
  vm.runInContext(fn+'\nthis.__send=send;',sandbox);
  return {send:sandbox.__send,box,busy,button,logs,sandbox};
}
test('long-listen text cannot be treated as a phone command or development task',async()=>{
  const ui=makeUI();
  assert.equal(await ui.send(false,null,{forceChat:true,restoreOnFailure:true}),true);
  assert.equal(ui.logs.api,1);
  assert.equal(ui.logs.scene||0,0);
  assert.equal(ui.logs.panel,0);
  assert.equal(ui.logs.dev,0);
  assert.equal(ui.logs.direct,0);
  assert.equal(ui.box.value,'');
});
test('when network fails, long-session prompt remains as a draft',async()=>{
  const ui=makeUI({fail:true});
  assert.equal(await ui.send(false,null,{forceChat:true,restoreOnFailure:true}),false);
  assert.equal(ui.logs.api,1);
  assert.equal(ui.box.value,'Sesli oturumdan önemli talimat');
  assert.ok(ui.logs.toast.some(text=>text.includes('doğrulanamadı')));
  assert.equal(ui.sandbox.chatSending,false);
  assert.equal(ui.button.disabled,false);
});
test('speaker playback failure does not undo a confirmed text response',async()=>{
  const ui=makeUI({voiceError:true});
  assert.equal(await ui.send(false,null,{forceChat:true,restoreOnFailure:true}),true);
  assert.equal(ui.logs.api,1);
  assert.equal(ui.logs.messages.at(-1).text,'Doğrulanmış asistan cevabı');
});
test('normal chat retains native panel-intent handling',async()=>{
  const ui=makeUI();
  await ui.send(false);
  assert.equal(ui.logs.scene,1);
  assert.equal(ui.logs.panel,1);
  assert.equal(ui.logs.api,0);
});
