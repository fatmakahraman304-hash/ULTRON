"""ULTRON Fast Brain: zero-cost single-pass conversation and capability routing.

No paid API, second model race, or hidden downloads. All model names are checked
against Ollama's installed model inventory; a missing Qwen3.5 upgrade never
prevents use of the already-installed Qwen3/coder models. Cloud Gemini Live
voice is intentionally *not* modified by this local text/tool router.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ultron.cloud_service.conversation_persona import classify_model_task

_TASKS = frozenset(("GENERAL", "FAST", "CODING", "VISION", "RESEARCH"))


def classify_text(text: str) -> str:
    """Shared Cloud/local task route; no LLM/API round trip."""
    return classify_model_task(text)


_SIMPLE_CHAT = re.compile(
    r"^(?:selam(?:lar)?|merhaba|günaydın|iyi (?:akşamlar|geceler)|"
    r"nasılsın|naber|teşekkür(?:ler)?|sağ ol|görüşürüz|"
    r"bana (?:kısa )?bir şaka anlat)[!?.\s]*$",re.IGNORECASE,
)


def simple_chitchat(text: str) -> bool:
    """Pure greetings only; everything actionable retains normal tool access."""
    return bool(_SIMPLE_CHAT.fullmatch(str(text or "").strip()))


def last_user_intent(messages: list[dict]) -> str:
    for m in reversed(messages or []):
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            return classify_text(m["content"])
    return "GENERAL"


@dataclass(frozen=True)
class FastBrainChoice:
    task: str
    model: str
    inventory_checked: bool
    reason: str


class FastBrainPolicy:
    """Routes based on *installed* models, never guesses availability."""

    def __init__(self, cfg: dict | None):
        self.cfg = cfg if isinstance(cfg, dict) else {}
        self.enabled = bool(self.cfg.get("enabled", False))

    def choose(self, *, task: str, installed: list[str], primary: str) -> FastBrainChoice:
        task = task if task in _TASKS else "GENERAL"
        # Empty inventory means Ollama unavailable/starting, NOT permission to
        # pull an uninstalled model. Preserve the configured legacy primary.
        models = {m for m in installed if isinstance(m, str) and m}
        if not self.enabled:
            return FastBrainChoice(task, primary, bool(models), "disabled")
        if not models:
            return FastBrainChoice(task, primary, False, "inventory_unavailable")
        preference = {
            "FAST": self.cfg.get("conversation_models", [
                "qwen3.5:4b", "qwen3:4b", "qwen3.5:2b", "qwen3:8b",
            ]),
            "GENERAL": self.cfg.get("reasoning_models", [
                "qwen3:8b", "qwen3.5:4b", "qwen3:4b",
            ]),
            "CODING": self.cfg.get("coding_models", [
                "qwen2.5-coder:7b", "qwen3.5:4b", "qwen3:8b",
            ]),
            "RESEARCH": self.cfg.get("research_models", [
                "qwen3:8b", "qwen3.5:4b", "qwen3:4b",
            ]),
            "VISION": self.cfg.get("vision_models", [
                "llava:7b", "qwen3.5:4b",
            ]),
        }.get(task, [])
        if not isinstance(preference, list):
            preference = []
        for model in preference:
            if isinstance(model, str) and model in models:
                return FastBrainChoice(task, model, True, "installed_preference")
        if primary in models:
            return FastBrainChoice(task, primary, True, "installed_primary")
        return FastBrainChoice(task, sorted(models)[0], True, "installed_fallback")

    def avoid_extra_judging(self, task: str) -> bool:
        """The costly two additional models + judge never run in Fast mode."""
        if not self.enabled:
            return False
        # Enable comparative judging only by explicit manual API / tool.
        return bool(self.cfg.get("single_pass_all_interactive", True))

    def runtime_options(self, model: str, *, tools: bool = False) -> dict:
        """Bound output/context; let Ollama manage GPU memory automatically."""
        cap = self.cfg.get("tool_tokens", 512) if tools else self.cfg.get("speech_tokens", 192)
        try:
            cap = max(64, min(1024, int(cap)))
        except (TypeError, ValueError):
            cap = 192
        max_ctx = 8192 if tools else 4096
        return {
            "stream": False,  # tools need one complete JSON response
            "keep_alive": str(self.cfg.get("keep_alive", "10m"))[:12],
            "options": {
                "num_predict": cap, "num_ctx": max_ctx,
                "temperature": 0.3,
            },
            **({"think": False} if model.lower().startswith(("qwen3:", "qwen3.5:")) else {}),
        }
