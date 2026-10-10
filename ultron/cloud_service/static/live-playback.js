/* Lightweight output playback accounting for ULTRON phone Gemini Live.
 * A server turn_complete finalizes transcripts, but any WebAudio buffer
 * already queued is still audible. Only real interrupt/stop must cancel it.
 */
(function(root,factory){
  "use strict";
  const api=factory();
  if(typeof module!=="undefined" && module.exports)module.exports=api;
  if(root)root.ULTRONLivePlayback=api;
})(typeof window!=="undefined"?window:null,function(){
  "use strict";
  function create(opts){
    const onDrained=opts?.onDrained||(()=>{});
    let generation=0,pending=0,completed=false;
    function drained(){
      if(completed&&pending===0)onDrained();
    }
    function enqueue(){
      const mine=generation;
      pending+=1;completed=false;
      let acknowledged=false;
      return function finish(){
        if(acknowledged||mine!==generation)return;
        acknowledged=true;
        pending=Math.max(0,pending-1);
        drained();
      };
    }
    function turnComplete(){
      completed=true;
      const waiting=pending>0;
      drained();
      return waiting;
    }
    function cancel(){
      generation++;
      pending=0;completed=false;
    }
    return {enqueue,turnComplete,cancel,
      get pending(){return pending;},
      get complete(){return completed;}
    };
  }
  return {create};
});
