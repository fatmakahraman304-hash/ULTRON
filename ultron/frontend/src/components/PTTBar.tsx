import { Mic, MicOff, Radio } from "lucide-react";
import { useApp, setState } from "../lib/store";
import { useEffect, useRef, useState } from "react";

export type PhaseLabel = "IDLE" | "LISTENING" | "THINKING" | "SPEAKING";

export function derivePhase(): PhaseLabel {
  const s = {
    mic: useApp((x) => x.mic),
    agent: useApp((x) => x.agentState),
    tts: useApp((x) => x.ttsSpeaking),
  };
  if (s.tts) return "SPEAKING";
  if (s.mic === "listening" || s.agent === "LISTENING") return "LISTENING";
  if (["THINKING", "PLANNING", "EXECUTING", "VERIFYING"].includes(s.agent)) return "THINKING";
  return "IDLE";
}

const API = location.protocol === "file:" ? "http://127.0.0.1:8000" : "";

/**
 * WakeWordBar — "ULTRON de, konuş" modunu aç/kapat.
 *
 * Butona bir kez tıklayınca backend wake-word dinlemeyi başlatır.
 * Tekrar tıklayınca durdurur. PTT butonu kaldırıldı.
 */
export function PTTBar({ onVoice }: { onVoice?: () => void }) {
  const phase = derivePhase();
  const mic = useApp((x) => x.mic);
  const [wakeActive, setWakeActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const toggleWake = async () => {
    setLoading(true);
    setError(null);
    const nextState = !wakeActive;
    try {
      const res = await fetch(`${API}/api/voice/live`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ on: nextState }),
      });
      const data = await res.json();
      if (!mountedRef.current) return;
      if (data.ok) {
        setWakeActive(nextState);
        setState({ mic: nextState ? "armed" : "idle" });
      } else {
        setError(data.error ?? "Bilinmeyen hata");
      }
    } catch (e: unknown) {
      if (!mountedRef.current) return;
      setError("Backend bağlantısı yok");
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  };

  const phaseLabel = (() => {
    if (wakeActive) {
      if (phase === "LISTENING") return "DİNLİYORUM";
      if (phase === "THINKING") return "DÜŞÜNÜYORUM";
      if (phase === "SPEAKING") return "KONUŞUYORUM";
      return "ULTRON DE...";
    }
    return "UYKU";
  })();

  const isLive = wakeActive && phase !== "IDLE";

  return (
    <div className="ptt-bar">
      {/* Ana wake-word butonu */}
      <button
        className={"ptt-btn wake-btn" + (wakeActive ? " live" : "") + (loading ? " loading" : "")}
        title={wakeActive ? "'ULTRON' diyerek konuş — kapatmak için tıkla" : "Sesle konuşmak için tıkla (ULTRON de)"}
        onClick={toggleWake}
        disabled={loading}
        aria-label={wakeActive ? "Sesi kapat" : "Sesle konuşmayı başlat"}
      >
        {loading
          ? <span className="spinner" />
          : wakeActive
            ? <Radio size={18} className={isLive ? "pulse-icon" : ""} />
            : <MicOff size={18} />
        }
      </button>

      {/* Durum metni */}
      <div className="ptt-meta">
        <div className="ptt-label">
          {wakeActive ? "WAKE-WORD AKTİF" : "SES KAPALI"}
        </div>
        <div className={"ptt-phase p-" + (wakeActive ? phase.toLowerCase() : "idle")}>
          {phaseLabel}
        </div>
      </div>

      {/* Hata */}
      {error && (
        <div className="ptt-error" title={error}>
          ⚠️ {error.length > 30 ? error.slice(0, 30) + "…" : error}
        </div>
      )}

      {/* Aktif göstergesi — yeşil halka */}
      {wakeActive && <span className="wake-indicator" aria-label="Dinliyor" />}
    </div>
  );
}
