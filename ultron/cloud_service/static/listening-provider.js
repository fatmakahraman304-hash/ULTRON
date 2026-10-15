/* Auditable owner choice before uploading a long transcript to cloud transit. */
(function(root,factory){
  'use strict';
  const api=factory();
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  if(root)root.ULTRONListeningProvider=api;
})(typeof window!=='undefined'?window:null,function(){
  'use strict';
  const choices=['auto','local','gemini'];
  function select(choice, devices) {
    if(!choices.includes(choice))throw Error('Bilinmeyen analiz sağlayıcısı.');
    const desktop=(Array.isArray(devices)?devices:[]).find(d=>d?.device==='desktop');
    const local=desktop?.online===true&&desktop?.state?.local_listening_analysis_ready===true;
    if(choice==='local'&&!local)
      throw Error('Laptop Qwen analiz işçisi hazır değil. Gemini’ye gizlice geçilmeyecek.');
    return choice==='auto'?(local?'local':'gemini'):choice;
  }
  function disclosure(provider, length) {
    if(!['local','gemini'].includes(provider))throw Error('Analiz modeli belirlenmedi.');
    if(!Number.isSafeInteger(length)||length<1||length>300000)
      throw Error('Konuşma metni uzunluğu doğrulanamadı.');
    if(provider==='local')return (
      'Bir saatlik oturumdan yakalanan '+length+' karakterlik konuşma metnini '+
      'parçalar halinde Render üzerinden Windows bilgisayarındaki Qwen modeline '+
      'göndermeyi onaylıyor musun? Render görev veritabanında metin geçici olarak '+
      'tutulur. Kayıtlar terminal durumda temizlenir, normal hafızaya yazılmaz. '+
      'İşlem sırasında Gemini’ye otomatik geçilmez.'
    );
    return (
      'Bir saatlik oturumdan yakalanan '+length+' karakterlik konuşma metnini '+
      'parçalar halinde Gemini Cloud analiz hizmetine göndermeyi onaylıyor musun? '+
      'Özet dışında kalıcı GÖLGE hafızasına yazım yapılmaz. İptal edersen '+
      'konuşma metni cihazındaki açık sekmede kalır.'
    );
  }
  return {select,disclosure};
});
