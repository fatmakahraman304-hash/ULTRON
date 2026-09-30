"""ULTRON V16 sağlık kontrolü — her bileşen ayrı, None-safe."""
import logging
import time
from pathlib import Path

logger = logging.getLogger("ultron.health")


def tts_backend_name(tts=None) -> str:
    """TTS backend adını döndürür — None veya hata durumunda 'unavailable'."""
    if tts is None:
        try:
            from app.voice.tts import TextToSpeech
            tts = TextToSpeech()
        except Exception:
            return "unavailable"
    try:
        # backend_str() varsa kullan, yoksa backend() + None kontrolü
        if hasattr(tts, 'backend_str'):
            return tts.backend_str()
        result = tts.backend()
        return result if result is not None else "unavailable"
    except Exception:
        return "unavailable"


def _db_health(db_paths: list[str]) -> dict:
    """Her db dosyasını kontrol et — açık olsa bile PRAGMA quick_check."""
    import sqlite3
    results = {}
    for path in db_paths:
        p = Path(path)
        if not p.exists():
            results[p.name] = "missing"
            continue
        try:
            conn = sqlite3.connect(str(p), timeout=2)
            conn.execute("PRAGMA quick_check")
            conn.close()
            results[p.name] = "ok"
        except Exception as e:
            results[p.name] = f"error: {e}"
    return results


def build_health(
    stack=None,
    runtime=None,
    ollama_connected: bool = False,
    persona_mode: str = "reframe",
    db_paths: list[str] | None = None,
) -> dict:
    h: dict = {
        "ts": time.time(),
        "ollama": "connected" if ollama_connected else "offline",
        "persona_mode": persona_mode,
        "databases": _db_health(db_paths or []),
    }

    # Voice stack
    if stack is not None:
        try:
            h["vad"] = getattr(stack, "vad_kind", "unknown")
            h["voice_stack"] = "ok"
        except Exception as e:
            h["voice_stack"] = f"error: {e}"
    else:
        h["voice_stack"] = "unavailable"

    # Runtime bileşenleri
    if runtime is not None:
        components = [
            "memory", "semantic_memory", "registry", "planner",
            "agent", "tts", "vision_llm", "proactive",
        ]
        for c in components:
            h[c] = "ok" if getattr(runtime, c, None) is not None else "unavailable"

        # TTS backend adı
        h["tts_backend"] = tts_backend_name(getattr(runtime, "tts", None))

        # Wake word
        wm = getattr(runtime, "wake_manager", None)
        if wm is not None:
            try:
                ws = wm.status()
                h["wake_word"] = ws.get("active_engine", "configured")
            except Exception:
                h["wake_word"] = "error"
        else:
            h["wake_word"] = "unavailable"
    else:
        h["runtime"] = "unavailable"

    # Genel durum
    critical = ["ollama", "memory", "agent"]
    if all(h.get(c) not in ("offline", "unavailable", None) for c in critical if c in h):
        h["overall"] = "ok"
    else:
        h["overall"] = "degraded"

    return h


def log_health(health: dict) -> None:
    status = health.get("overall", "?")
    ollama = health.get("ollama", "?")
    tts = health.get("tts_backend", "?")
    wake = health.get("wake_word", "?")
    dbs = health.get("databases", {})
    db_summary = ", ".join(f"{k}={v}" for k, v in dbs.items()) if dbs else "none"
    logger.info(
        "[HEALTH] overall=%s ollama=%s tts=%s wake=%s dbs=[%s]",
        status, ollama, tts, wake, db_summary,
    )
    print(
        f"[ULTRON-HEALTH] overall={status} | ollama={ollama} | tts={tts} | wake={wake}",
        flush=True,
    )
