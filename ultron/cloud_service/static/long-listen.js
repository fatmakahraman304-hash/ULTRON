/* ULTRON one-hour foreground dictation; no automatic cloud submission. */
(function(root){
  'use strict';
  // Keep up to roughly an hour of recognized text in temporary tab memory.
  // The model request is still capped separately; full notes are exportable.
  var MAX_MS=60*60*1000, MAX_LOCAL_CHARS=300000;
  var START=/^(?:ultron[, ]*)?(?:(?:1|bir)\s*saat\s*(?:boyunca\s*)?(?:beni\s*)?dinle(?:\s*beni)?|beni\s*(?:1|bir)\s*saat\s*(?:boyunca\s*)?dinle)(?:\s*(?:lütfen|lutfen))?[\s.!?]*$/i;
  var ANSWER=/^(?:ultron[, ]*)?(?:(?:şimdi|artik|artık)\s*)?cevap ver(?:\s*(?:artık|lütfen|lutfen))?[\s.!?]*$/i;
  function clean(s){return String(s||'').trim();}
  function isStart(s){return START.test(clean(s));}
  function isAnswer(s){return ANSWER.test(clean(s));}
  function create(opts){
    opts=opts||{};
    var host=opts.host||root, doc=opts.document||host.document;
    var Clock=opts.now||function(){return Date.now();};
    var setLater=opts.setTimeout||host.setTimeout.bind(host);
    var clearLater=opts.clearTimeout||host.clearTimeout.bind(host);
    var Constructor=opts.Recognition||host.SpeechRecognition||host.webkitSpeechRecognition;
    var status='idle', deadline=0, noteChunks=[], noteSize=0, dropped=0;
    var recognition=null, deadlineTimer=null, retryTimer=null, generation=0, failures=0;
    function emit(message){if(opts.onState)opts.onState({status:status,message:message||'',secondsLeft:Math.max(0,Math.ceil((deadline-Clock())/1000)),charCount:noteSize,dropped:dropped});}
    function clearTimers(){if(deadlineTimer!==null)clearLater(deadlineTimer);if(retryTimer!==null)clearLater(retryTimer);deadlineTimer=retryTimer=null;}
    function stopEngine(){var old=recognition;recognition=null;if(old){old.onend=null;old.onerror=null;old.onresult=null;try{old.stop();}catch(e){}}}
    function append(text){
      var value=clean(text);
      if(!value)return;
      value=value.slice(0,1200);
      noteChunks.push(value);noteSize+=value.length;
      while(noteSize>MAX_LOCAL_CHARS&&noteChunks.length>2){
        var removed=noteChunks.splice(1,1)[0];noteSize-=removed.length;dropped++;
      }
      emit('Dinleniyor • konuşmalar henüz ULTRON’a gönderilmedi.');
    }
    function finish(send){
      if(status!=='listening'&&status!=='ready'&&status!=='interrupted')return false;
      clearTimers();generation++;stopEngine();status='ready';
      if(!send){emit('Dinleme bitti. “Cevap ver” diyebilir veya düğmeye basabilirsin.');return true;}
      var text=noteChunks.join('\n');
      if(!text){emit('Ses algılanmadı. Yanıt gönderilmedi.');return false;}
      var message='';
      if(text.length<=2350&&!dropped){message=text;}
      else{
        // Sample opening, midpoint and conclusion instead of silently
        // losing every event between the first and last minute.
        var mid=Math.floor(text.length/2);
        var front=text.slice(0,680),middle=text.slice(Math.max(0,mid-340),mid+340);
        var tail=text.slice(-680);
        message='[Başlangıç]\n'+front+'\n[Orta bölümden örnek]\n'+middle+
          '\n[Uzun oturum: aradaki konuşmalar bu isteğe dahil edilmedi.]\n[Son]\n'+tail;
      }
      // This prompt is intentionally truthful about omitted text. The browser
      // may have processed speech remotely, but ULTRON only sees this excerpt.
      var prompt='Dinleme oturumunda söylediklerime, yalnızca aşağıdaki yazıya dayanarak yanıt ver. Eksik bölümleri duymuş gibi davranma:\n'+message;
      // Keep the original transcription until the server confirms a reply.
      // Network timeouts can mean "accepted but response lost"; never submit
      // it automatically a second time without the owner's explicit action.
      status='submitting';
      emit('Yanıt bekleniyor • konuşma metni geçici olarak korunuyor.');
      try{if(opts.onAnswer)opts.onAnswer(prompt);}
      catch(error){failDelivery('Gönderim başlatılamadı. Metin korunuyor.');return false;}
      return true;
    }
    function confirmDelivered(){
      if(status!=='submitting')return false;
      status='submitted';noteChunks=[];noteSize=0;dropped=0;
      emit('Yanıt doğrulandı • geçici konuşma metni temizlendi.');
      return true;
    }
    function failDelivery(reason){
      if(status!=='submitting')return false;
      status='ready';
      emit(reason||'Yanıt doğrulanamadı. Konuşma metni korundu; tekrar göndermeden önce sohbeti kontrol et.');
      return true;
    }
    function interrupt(reason){
      if(status!=='listening')return;
      clearTimers();generation++;stopEngine();status='interrupted';
      emit(reason||'Dinleme kesildi. Kaydedilmiş metin yalnızca bu sekmede tutuluyor.');
    }
    function beginEngine(token){
      if(status!=='listening'||token!==generation)return;
      if(doc&&doc.hidden){interrupt('Ekran arka plana geçtiği için dinleme durdu.');return;}
      if(Clock()>=deadline){finish(false);return;}
      var r=new Constructor();
      recognition=r;
      r.lang='tr-TR';r.continuous=true;r.interimResults=true;
      var lastFinal=-1;
      r.onresult=function(e){
        if(token!==generation||status!=='listening')return;
        failures=0;
        for(var i=e.resultIndex||0;i<e.results.length;i++){
          var record=e.results[i];
          if(!record.isFinal||i<=lastFinal)continue;
          lastFinal=i;
          var spoken=clean(record[0]&&record[0].transcript);
          if(!spoken)continue;
          if(isAnswer(spoken)){finish(true);return;}
          if(/^(?:ultron[, ]*)?(?:dinlemeyi\s*)?(?:iptal et|durdur)[\s.!?]*$/i.test(spoken)){cancel();return;}
          append(spoken);
        }
      };
      r.onerror=function(e){
        if(token!==generation||status!=='listening')return;
        var reason=e&&e.error||'';
        if(reason==='not-allowed'||reason==='service-not-allowed'||reason==='audio-capture'||reason==='network'){
          interrupt('Mikrofon/ses tanıma hatası: '+reason+'. Dinleme durduruldu.');
        }
      };
      r.onend=function(){
        if(token!==generation||status!=='listening')return;
        recognition=null;
        if(Clock()>=deadline){finish(false);return;}
        if(doc&&doc.hidden){interrupt('Ekran kilitlendi veya sayfa arka plana geçti.');return;}
        failures++;
        if(failures>8){interrupt('Ses tanıma art arda durdu. Kalan metin korunuyor.');return;}
        retryTimer=setLater(function(){retryTimer=null;try{beginEngine(token);}catch(e){interrupt('Ses tanıma yeniden başlatılamadı.');}},600);
      };
      try{r.start();}
      catch(e){interrupt('Tarayıcı mikrofonu başlatamadı: '+(e&&e.message||e));}
    }
    function start(){
      if(status==='listening')return true;
      if(status==='submitting'){emit('Yanıt hâlâ bekleniyor; bu sırada kayıt sıfırlanamaz.');return false;}
      if(!Constructor){status='unsupported';emit('Bu tarayıcı uzun süreli konuşmayı metne çevirmeyi desteklemiyor.');return false;}
      clearTimers();stopEngine();generation++;var token=generation;
      status='listening';deadline=Clock()+MAX_MS;noteChunks=[];noteSize=0;dropped=0;failures=0;
      deadlineTimer=setLater(function(){if(token===generation)finish(false);},MAX_MS);
      emit('Dinleme başladı. Uygulamayı açık tut; kilit ekranında dinleyemem.');
      beginEngine(token);
      return status==='listening';
    }
    function resume(){
      if(status!=='interrupted')return false;
      if(doc&&doc.hidden){emit('Devam etmek için uygulamayı ön plana getir.');return false;}
      if(Clock()>=deadline){finish(false);return false;}
      clearTimers();stopEngine();generation++;failures=0;
      var token=generation;
      status='listening';
      deadlineTimer=setLater(function(){if(token===generation)finish(false);},Math.max(0,deadline-Clock()));
      emit('Dinleme yeniden başladı. Kalan süre ilk başlangıçtan hesaplanır.');
      beginEngine(token);
      return status==='listening';
    }
    function pause(){
      if(status!=='listening')return false;
      interrupt('Dinleme duraklatıldı. Devam et veya Cevap ver seç.');
      return true;
    }
    function cancel(){clearTimers();generation++;stopEngine();status='idle';noteChunks=[];noteSize=0;dropped=0;deadline=0;emit('Dinleme iptal edildi; konuşma metni silindi.');}
    function tick(){
      if(status==='listening'||status==='interrupted'){
        if(Clock()>=deadline)finish(false);
        else if(status==='listening')emit('Dinleniyor.');
      }
    }
    if(doc&&doc.addEventListener){
      doc.addEventListener('visibilitychange',function(){
        if(doc.hidden)interrupt('Ekran kapandı veya uygulama arka plana geçti; dinleme durdu.');
      });
    }
    return {start:start,resume:resume,pause:pause,finish:finish,
      confirmDelivered:confirmDelivered,failDelivery:failDelivery,
      cancel:cancel,interrupt:interrupt,tick:tick,
      active:function(){return status==='listening';},
      hasSession:function(){return status==='listening'||status==='ready'||status==='interrupted'||status==='submitting';},
      state:function(){return status;},supported:function(){return !!Constructor;},
      isStart:isStart,isAnswer:isAnswer,
      transcript:function(){return noteChunks.join('\n');},
      omitted:function(){return dropped;}};
  }
  root.ULTRONLongListen={create:create,isStart:isStart,isAnswer:isAnswer};
  if(typeof module!=='undefined'&&module.exports)module.exports=root.ULTRONLongListen;
})(typeof window!=='undefined'?window:globalThis);
