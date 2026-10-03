# Local hand tracking assets

Runtime: @mediapipe/tasks-vision 1.0.1 (Apache-2.0). WASM files copied from the pinned npm package.
Model: Google MediaPipe Hand Landmarker float16, version 1.
Download: https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
Guide: https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/web_js

These files are bundled locally. Camera frames are passed to an on-device Web Worker, not to a remote server. Camera input is requested only when the user clicks the hand-control button, and released on stop, close or tab hide.

Model SHA256: FBC2A30080C3C557093B5DDFC334698132EB341044CCEE322CCF8BCF3607CDE1

The bundled runtime documents optional performance metrics. This application serves the hand worker with a same-origin Content Security Policy, which blocks external metrics endpoints. No external runtime asset downloads are necessary.
