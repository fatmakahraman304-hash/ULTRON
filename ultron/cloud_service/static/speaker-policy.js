/* Owner-scoped phone/desktop single-speaker arbitration.
 * Visual/voice routing only. No permissions, device commands or new audio APIs.
 */
(function(root,factory){
  "use strict";
  const api=factory();
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  if(root)root.ULTRONSpeakerPolicy=api;
})(typeof window!=="undefined"?window:null,function(){
  "use strict";
  function desktopEligible(online,state){
    const s=state&&typeof state==="object"&&!Array.isArray(state)?state:{};
    return online===true && s.speaking===true && s.voice_active===true &&
      s.voice_output!==false && s.muted!==true;
  }
  function phoneOwnsVoice(session){
    const p=session&&typeof session==="object"?session:{};
    return p.liveDesired===true || p.voiceListening===true ||
      p.localVoiceActive===true;
  }
  function desktopMayLead(online,state,session){
    return !phoneOwnsVoice(session)&&desktopEligible(online,state);
  }
  return {desktopEligible,phoneOwnsVoice,desktopMayLead};
});
