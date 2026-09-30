"""LiveVoiceV2 — ULTRON dediğinde anlayan, tam otomatik ses döngüsü.

Akış:
  KeywordSpotter (sürekli) → "ultron" duyuldu → _on_wake()
    → STT ile uzun cümle dinle → Agent.handle() → TTS cevap ver
    → KeywordSpotter dinlemeye devam

Özellikler:
  - Push-to-talk YOKTUR; sadece wake-word tetikler
  - Tamamen yerel: Whisper tiny (keyword) + Whisper small/medium (komut)
  - TTS: Piper-local veya eSpeak-ng
  - Barge-in: TTS konuşurken "ultron" tekrar → konuşmayı kes, dinle
  - Thread-safe: tek komut aynı anda işlenir (lock ile)
"""
from __future__ import annotations

import threading
import time
import logging

logger = logging.getLogger("ultron.live_voice_v2")


class LiveVoiceV2:
    """Wake-word tabanlı sürekli ses döngüsü."""

    def __init__(self, agent, tts, settings: dict) -> None:
        self.agent = agent
        self.tts = tts
        self.settings = settings

        voice_cfg = settings.get("voice", {})
        self.sample_rate: int = int(voice_cfg.get("sample_rate", 16000))
        self.listen_seconds: float = float(voice_cfg.get("listen_seconds", 8))
        self.keyword: str = settings.get("wake_word", "ultron").lower()
        self.stt_model: str = voice_cfg.get("stt_model", "models/whisper-tiny")
        self.language: str = "tr"

        self._running = False
        self._speaking = False      # TTS aktif mi?
        self._busy = False          # Komut işleniyor mu?
        self._lock = threading.Lock()
        self._mic_lock = threading.Lock()  # mikrofon exclusive erişim — çakışma önleme
        self._stt_model = None
        self._spotter: "KeywordSpotter | None" = None

        # WebSocket hub'a proaktif mesaj göndermek için (opsiyonel)
        self._ws_broadcast: "Callable[[str, str], None] | None" = None
        self._runtime_ask = None   # set_runtime_ask() ile bridge bağlanır

    # ── Public API ──────────────────────────────────────────────────────

    def start(self) -> dict:
        """Keyword spotter'ı başlat ve sürekli dinlemeye geç."""
        if self._running:
            return {"ok": True, "note": "already running"}

        from app.voice.keyword_spotter import KeywordSpotter
        self._spotter = KeywordSpotter(
            keyword=self.keyword,
            on_wake=self._on_wake,
            sample_rate=self.sample_rate,
            model_path=self.stt_model,
            language=self.language,
        )
        result = self._spotter.start()
        if not result.get("ok"):
            return result

        self._running = True
        logger.info("[LiveVoiceV2] Başladı — keyword=%s", self.keyword)
        return {"ok": True, "mode": "wake-word", "keyword": self.keyword}

    def stop(self) -> None:
        self._running = False
        if self._spotter:
            self._spotter.stop()

    def status(self) -> dict:
        sp_status = self._spotter.status() if self._spotter else {"available": False, "error": "not started"}
        return {
            "mode": "wake-word-continuous",
            "running": self._running,
            "keyword": self.keyword,
            "speaking": self._speaking,
            "busy": self._busy,
            "spotter": sp_status,
        }

    def set_runtime_ask(self, fn) -> None:
        """runtime.ask() fonksiyonunu bağla — tam bridge pipeline kullanılır."""
        self._runtime_ask = fn

    def set_ws_broadcast(self, fn) -> None:
        """WebSocket mesaj göndericisini bağla (bridge tarafından çağrılır)."""
        self._ws_broadcast = fn

    # ── Internal ────────────────────────────────────────────────────────

    def _broadcast(self, event: str, message: str) -> None:
        if self._ws_broadcast:
            try:
                self._ws_broadcast(event, message)
            except Exception:
                pass

    def _on_wake(self) -> None:
        """KeywordSpotter'dan gelen wake callback."""
        # Zaten meşgulse atla
        if self._busy:
            logger.debug("[LiveVoiceV2] wake geldi ama meşgul, atlandı")
            return

        # TTS konuşuyorsa kes (barge-in)
        if self._speaking:
            try:
                self.tts.stop()
            except Exception:
                pass
            self._speaking = False
            logger.info("[LiveVoiceV2] Barge-in: TTS kesildi")

        # Tek seferde bir komut işle
        with self._lock:
            if self._busy:
                return
            self._busy = True

        try:
            self._handle_wake()
        finally:
            self._busy = False

    def _handle_wake(self) -> None:
        """Wake tetiklendikten sonra: bip → STT → agent → TTS."""
        # Kullanıcıya "seni duydum" sinyali
        self._broadcast("agent", "🎙️ Dinliyorum...")
        self._play_beep()

        # Komutu kaydet
        try:
            pcm = self._record_command()
        except Exception as e:
            logger.warning("[LiveVoiceV2] Ses kaydedilemedi: %s", e)
            self._broadcast("agent", "⚠️ Ses alınamadı.")
            return

        if not pcm:
            return

        # STT
        try:
            text = self._transcribe(pcm)
        except Exception as e:
            logger.warning("[LiveVoiceV2] STT hatası: %s", e)
            self._broadcast("agent", "⚠️ Ses tanınamadı.")
            return

        if not text:
            return

        # "ULTRON" kelimesini komuttan çıkar
        command = text.lower().replace(self.keyword, "").strip(" ,.:;-")
        if not command:
            # Sadece "ultron" denildi, isim yoksa kısa onay ver
            self._speak("Evet, boss?")
            return

        logger.info("[LiveVoiceV2] Komut: %s", command)
        self._broadcast("chat_user", command)

        # Agent
        try:
            # Önce runtime.ask() dene (tam bridge pipeline: tool+memory+LLM)
            if self._runtime_ask is not None:
                answer = self._runtime_ask(command, False)
            else:
                answer = self.agent.handle(command)
        except Exception as e:
            logger.error("[LiveVoiceV2] Agent hatası: %s", e)
            answer = "Bir sorun oluştu, boss. Lütfen tekrar deneyin."

        if not answer:
            answer = "Anladım, boss."

        self._broadcast("chat_ultron", answer)
        self._speak(answer)

    def _play_beep(self) -> None:
        """Kısa bip tonu — 'seni duydum' sinyali."""
        try:
            import sounddevice as sd
            import numpy as np
            sr = self.sample_rate
            t = np.linspace(0, 0.12, int(sr * 0.12), False)
            tone = (np.sin(2 * np.pi * 880 * t) * 0.3).astype("float32")
            sd.play(tone, sr, blocking=True)
        except Exception:
            pass   # beep opsiyonel

    def _record_command(self) -> bytes:
        """Uzun komutu VAD ile kaydet — mic_lock ile keyword_spotter ile çakışmaz."""
        import sounddevice as sd
        import numpy as np

        seconds = self.listen_seconds
        with self._mic_lock:
            frames = sd.rec(
                int(seconds * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1, dtype="int16", blocking=True,
            )
            sd.wait()  # blocking=True ek güvence
        return frames.tobytes()

    def _transcribe(self, pcm: bytes) -> str:
        import io, wave
        if self._stt_model is None:
            from faster_whisper import WhisperModel
            self._stt_model = WhisperModel(
                self.stt_model, device="cpu", compute_type="int8",
                num_workers=1, cpu_threads=2,
            )
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.sample_rate)
            w.writeframes(pcm)
        buf.seek(0)
        segments, _ = self._stt_model.transcribe(
            buf, language=self.language, vad_filter=True, beam_size=3,
        )
        return " ".join(s.text for s in segments).strip()

    def _speak(self, text: str) -> None:
        self._speaking = True
        # Spotter'a TTS aktif olduğunu bildir (echo önleme)
        if self._spotter:
            self._spotter.set_tts_active(True)
        try:
            self.tts.speak(text)
        except Exception as e:
            logger.warning("[LiveVoiceV2] TTS hatası: %s", e)
        finally:
            self._speaking = False
            # TTS bitti — spotter tekrar dinlemeye geçsin
            if self._spotter:
                self._spotter.set_tts_active(False)
