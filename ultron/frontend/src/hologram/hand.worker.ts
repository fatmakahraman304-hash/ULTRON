/// <reference lib="webworker" />
import {FilesetResolver,HandLandmarker} from '@mediapipe/tasks-vision';
let detector:HandLandmarker|null=null;
self.onmessage=async(e:MessageEvent)=>{
  try{
    if(e.data.kind==='init'){
      const files=await FilesetResolver.forVisionTasks(e.data.base+'/wasm',true);
      detector=await HandLandmarker.createFromOptions(files,{baseOptions:{modelAssetPath:e.data.base+'/hand_landmarker.task',delegate:'CPU'},runningMode:'VIDEO',numHands:2,minHandDetectionConfidence:.6,minHandPresenceConfidence:.6,minTrackingConfidence:.6});
      self.postMessage({kind:'ready'});
    }else if(e.data.kind==='frame'){
      const bitmap:ImageBitmap=e.data.bitmap;
      try{const result=detector!.detectForVideo(bitmap,e.data.time);self.postMessage({kind:'hands',hands:result.landmarks});}finally{bitmap.close();}
    }
  }catch(error){self.postMessage({kind:'error',message:error instanceof Error?error.message:String(error)});}
};
