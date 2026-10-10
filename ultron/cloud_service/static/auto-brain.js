/* ULTRON automatic routing: fresh desktop heartbeat + live Ollama probe -> local, otherwise Gemini.
 * Never interpret a browser network error or an already queued local task
 * as proof that resending the same message is safe.
 */
(function(root,factory){
 "use strict";
 const api=factory();
 if(typeof module!=="undefined"&&module.exports)module.exports=api;
 if(root)root.ULTRONAutoBrain=api;
})(typeof window!=="undefined"?window:null,function(){
 "use strict";
 function select(devices) {
  const rows=Array.isArray(devices)?devices:[];
  const desktop=rows.find(item=>item&&item.device==="desktop");
  return desktop?.online===true&&desktop?.state?.local_chat_ready===true?"local":"gemini";
 }
 function safeToFallback(error) {
  return error?.status===409&&error?.data?.error==="desktop_offline";
 }
 return {select,safeToFallback};
});
