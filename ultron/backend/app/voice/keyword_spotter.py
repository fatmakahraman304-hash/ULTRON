"""Acoustic keyword spotting only; never searches an STT transcript."""
from pathlib import Path
import os
import queue
import threading
import time

class KeywordSpotter:
    def __init__(self, keyword='ultron', on_wake=None, sample_rate=16000,
                 model_path=None, language='tr', energy_threshold=0.008, chunk_seconds=0.6):
        self.keyword=keyword
        self.on_wake=on_wake
        self.sample_rate=sample_rate
        self._running=False
        self._tts_active=False
        self._thread=None
        self._model=None
        self._error=None
        self._stream=None
        self._queue=queue.Queue(maxsize=32)
        self._last_wake=0.0

    def _load_model(self):
        from openwakeword.model import Model
        root=Path(__file__).resolve().parents[2]/'data/voice/wake'
        custom=root/'ultron.onnx'
        if not custom.is_file():
            raise FileNotFoundError('Custom ULTRON wake model missing: ultron.onnx')
        selected=str(custom)
        self._model=Model(wakeword_models=[selected],inference_framework='onnx')
        self.keyword='ultron'

    def start(self):
        if os.environ.get('MARK_AUDIO_OWNER')=='mark':
            return {'ok':False,'error':'OWNED_BY_MARK'}
        if self._running:
            return {'ok':True,'keyword':self.keyword}
        try:
            import sounddevice as sd
            self._load_model()
            def callback(data, frames, timing, status):
                if self._tts_active: return
                try: self._queue.put_nowait(bytes(data))
                except queue.Full: return
            self._stream=sd.RawInputStream(samplerate=16000,channels=1,dtype='int16',blocksize=1280,callback=callback)
            self._stream.start()
        except Exception as exc:
            self._error=str(exc)
            if self._stream: self._stream.close(); self._stream=None
            return {'ok':False,'error':self._error}
        self._running=True
        self._thread=threading.Thread(target=self._loop,daemon=True,name='acoustic-wake')
        self._thread.start()
        return {'ok':True,'keyword':self.keyword,'engine':'openwakeword'}

    def stop(self):
        self._running=False
        if self._stream:
            self._stream.stop();self._stream.close();self._stream=None
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)
        self._model=None

    def set_tts_active(self,active):
        self._tts_active=active

    def status(self):
        return {'engine':'openwakeword','available':self._model is not None,'running':self._running,
                'keyword':self.keyword,'error':self._error,
                'custom_model':(Path(__file__).resolve().parents[2]/'data/voice/wake/ultron.onnx').is_file()}

    def _loop(self):
        import numpy as np
        while self._running:
            try:
                data=self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                scores=self._model.predict(np.frombuffer(data,dtype=np.int16))
                if max(scores.values(),default=0)>=0.5 and time.monotonic()-self._last_wake>1.5:
                    self._last_wake=time.monotonic()
                    self._model.reset()
                    if self.on_wake:
                        threading.Thread(target=self.on_wake,daemon=True).start()
            except Exception as exc:
                self._error=str(exc)
                self._running=False
        if self._stream:
            self._stream.stop();self._stream.close();self._stream=None
