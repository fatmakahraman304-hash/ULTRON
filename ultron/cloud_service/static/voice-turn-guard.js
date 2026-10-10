/* ULTRON: a cancelled mobile voice turn may finish its text reply, but must
 * never start reading that stale reply aloud. This does not cancel an already
 * queued desktop/Cloud task and therefore cannot duplicate its execution.
 */
(function(root,factory){
  "use strict";
  const api=factory();
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  if(root)root.ULTRONVoiceTurnGuard=api;
})(typeof window!=="undefined"?window:null,function(){
  "use strict";
  function create(){
    let epoch=0;
    function begin(){epoch+=1;return epoch;}
    function cancel(){epoch+=1;}
    function current(token){return Number.isSafeInteger(token)&&token>0&&token===epoch;}
    return {begin,cancel,current};
  }
  return {create};
});
