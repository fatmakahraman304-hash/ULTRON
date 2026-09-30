"""Pure-Python keyword spotter — Porcupine/OWW gerektirmez.

Nasıl çalışır:
1. Sürekli mikrofonu kısa kısa (500ms) parçalar halinde okur
2. Her parçayı EnergyVAD ile filtreler — sessizse atlar
3. Ses varsa Whisper tiny ile hızla transkript alır
4. Transkriptte "ultron" geçiyorsa wake event tetikler
5. Callback'i çağırır → LiveVoiceV2 uzun dinlemeye geçer

Bu yaklaşım:
- Sıfır bağımlılık (sadece faster-whisper + sounddevice)
- Tamamen yerel, bulut yok
- 500ms latency (tiny model) — kabul edilebilir
- CPU: i5'te ~%5-8 idle kullanım
"""
from __future__ import annotations

import threading
import time
from typing import Callable

CHUNK_SECONDS = 0.6          # Her segment uzunluğu (saniye)
ENERGY_THRESHOLD = 0.008     # RMS eşiği (sessiz → atla)
COOLDOWN_SECONDS = 1.5       # Wake sonrası bekleme (çift tetikleme önleme)


class KeywordSpotter:
    """Sürekli çalışan, Whisper tabanlı wake-word dinleyici."""

    def __init__(
        self,
        keyword: str = "ultron",
        on_wake: Callable[[], None] | None = None,
        sample_rate: int = 16000,
        model_path: str = "models/whisper-tiny",
        language: str = "tr",
        energy_threshold: float = ENERGY_THRESHOLD,
        chunk_seconds: float = CHUNK_SECONDS,
    ) -> None:
        self.keyword = keyword.lower().strip()
        self.on_wake = on_wake
        self.sample_rate = sample_rate
        self.model_path = model_path
        self.language = language
        self.energy_threshold = energy_threshold
        self.chunk_seconds = chunk_seconds

        self._model = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_wake = 0.0
        self._error: str | None = None
        self._available: bool | None = None  # None = henüz bilinmiyor
        self._tts_active = False   # TTS konuşurken wake-word tetiklenmesin

    # ── Public API ────────────────────────────────────────────────────────

    def start(self) -> dict:
        """Arka plan dinlemeyi başlat."""
        if self._running:
            return {"ok": True, "note": "already running"}
        if not self._check_dependencies():
            return {"ok": False, "error": self._error}
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="keyword-spotter")
        self._thread.start()
        return {"ok": True, "keyword": self.keyword, "model": self.model_path}

    def stop(self) -> None:
        self._running = False

    def set_tts_active(self, active: bool) -> None:
        """TTS konuşurken True — bu sürede wake tetiklenmiyor (echo önleme)."""
        self._tts_active = active

    def status(self) -> dict:
        deps_ok = self._check_dependencies()
        return {
            "engine": "whisper-keyword",
            "available": deps_ok,
            "running": self._running,
            "keyword": self.keyword,
            "model": self.model_path,
            "language": self.language,
            "error": self._error if not deps_ok else None,
        }

    # ── Internal ─────────────────────────────────────────────────────────

    def _check_dependencies(self) -> bool:
        if self._available is not None:
            return self._available
        errors = []
        try:
            import sounddevice as _sd  # noqa: F401
            # PortAudio kontrolü — import başarılıysa bile cihaz yok olabilir
            _sd.query_devices()
        except OSError as e:
            errors.append(f"sounddevice/PortAudio: {e}")
        except ImportError as e:
            errors.append(f"sounddevice: {e}")
        try:
            from faster_whisper import WhisperModel as _W  # noqa: F401
        except ImportError as e:
            errors.append(f"faster-whisper: {e}")
        if errors:
            self._error = "Eksik bağımlılık: " + "; ".join(errors) + " — pip install faster-whisper sounddevice"
            self._available = False
        else:
            self._available = True
        return self._available

    def _load_model(self):
        if self._model is not None:
            return
        from faster_whisper import WhisperModel
        self._model = WhisperModel(
            self.model_path, device="cpu", compute_type="int8",
            num_workers=1, cpu_threads=2,
        )

    def _rms(self, pcm: bytes) -> float:
        import struct
        samples = struct.unpack(f"{len(pcm)//2}h", pcm)
        if not samples:
            return 0.0
        rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
        return rms / 32768.0

    def _transcribe_chunk(self, pcm: bytes) -> str:
        import io, wave
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.sample_rate)
            w.writeframes(pcm)
        buf.seek(0)
        segments, _ = self._model.transcribe(
            buf, language=self.language,
            vad_filter=False,   # zaten EnergyVAD geçirdik
            beam_size=1,        # hız için
            best_of=1,
            temperature=0,
            condition_on_previous_text=False,
        )
        return " ".join(s.text for s in segments).strip().lower()

    def _loop(self) -> None:
        import sounddevice as sd

        chunk_samples = int(self.sample_rate * self.chunk_seconds)
        try:
            self._load_model()
        except Exception as e:
            self._error = str(e)
            self._running = False
            return

        while self._running:
            try:
                # Kısa parça kaydet
                frames = sd.rec(
                    chunk_samples, samplerate=self.sample_rate,
                    channels=1, dtype="int16", blocking=True,
                )
                pcm = frames.tobytes()

                # Sessizse atla
                if self._rms(pcm) < self.energy_threshold:
                    continue

                # TTS aktifse kendi sesimizi duymasın (echo önleme)
                if self._tts_active:
                    continue
                # Cooldown: yeni wake'den hemen sonra tekrar tetiklenmesin
                if time.monotonic() - self._last_wake < COOLDOWN_SECONDS:
                    continue

                # Transkript al
                text = self._transcribe_chunk(pcm)
                if not text:
                    continue

                # Keyword var mı?
                if self.keyword in text:
                    self._last_wake = time.monotonic()
                    if self.on_wake:
                        threading.Thread(
                            target=self.on_wake, daemon=True, name="wake-callback"
                        ).start()

            except Exception:
                time.sleep(0.1)   # geçici hata — devam et
