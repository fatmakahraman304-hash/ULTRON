"""Adaptive Persona — emotion-driven tone modulation with logging & override.

TIRED    → sarcasm down, short & caring
STRESSED → no philosophy, direct solutions ("Nietzsche molada")
ENERGETIC→ light humor, confident and natural
NEUTRAL  → calm, concise GÖLGE
Manual override ("sarkazm aç/kapat") bypasses auto adaptation.
"""
import sqlite3
from app.core.database import transaction as sqlite_transaction
import time
from pathlib import Path

HINTS = {
    "TIRED": "Kullanıcı yorgun görünüyor: mizahı azalt, destekleyici ol ve kısa cevap ver.",
    "STRESSED": "Kullanıcı gergin görünüyor: doğrudan çözüm sun, felsefi alıntı ve şakadan kaçın.",
    "ENERGETIC": "Kullanıcı enerjik: hafif mizah kullan; saygılı ve doğal kal, alaya kaçma.",
    "NEUTRAL": None,
}


class AdaptivePersona:
    def __init__(self, path="data/emotion/emotion_adaptations.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.override = None  # None | "sarkazm-on" | "sarkazm-off"
        with sqlite_transaction(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS emotion_adaptations(
                id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL,
                detected_state TEXT, applied_mode TEXT, confidence REAL)""")

    def set_override(self, mode):
        self.override = mode if mode in ("sarkazm-on", "sarkazm-off", None) else None
        return self.override

    def handle_command(self, text: str):
        t = (text or "").lower()
        if "sarkazm kapat" in t or "sarkazmı kapat" in t:
            return self.set_override("sarkazm-off")
        if "sarkazm aç" in t or "sarkazmı aç" in t:
            return self.set_override("sarkazm-on")
        return None

    def adapt(self, state: str, confidence: float) -> str | None:
        if self.override == "sarkazm-off":
            applied, hint = "override-off", HINTS["TIRED"]
        elif self.override == "sarkazm-on":
            applied, hint = "override-on", HINTS["ENERGETIC"]
        else:
            applied, hint = state, HINTS.get(state)
        try:
            with sqlite_transaction(self.path) as db:
                db.execute("INSERT INTO emotion_adaptations(ts,detected_state,applied_mode,confidence)"
                           " VALUES(?,?,?,?)", (time.time(), state, applied or "none", confidence))
        except Exception:
            pass
        return hint

    def trends(self, limit=50):
        try:
            with sqlite_transaction(self.path) as db:
                rows = db.execute("SELECT ts,detected_state,applied_mode,confidence FROM"
                                  " emotion_adaptations ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [{"ts": r[0], "state": r[1], "applied": r[2], "confidence": r[3]}
                    for r in reversed(rows)]
        except Exception:
            return []
