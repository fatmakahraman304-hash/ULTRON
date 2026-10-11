"""Pure validation of paired laptop local-chat completions.

Cloud handlers import this function, and lightweight tests can exercise it
without aiohttp, databases or running Ollama.
"""
from __future__ import annotations

from model_identity import is_qwen_model
from response_quality import strip_qwen_thinking


def _validated_local_reply(result: dict) -> tuple[str, str, str] | None:
    """Accept only genuine text and known local-response provenance.

    Desktop can return a no-image notice without ever invoking Ollama.
    That must not be stored as a model-generated answer in conversation logs.
    No network or database access; never stringify arbitrary JSON as prose.
    """
    if not isinstance(result, dict):
        return None
    content = result.get("assistant_reply")
    if not isinstance(content, str):
        return None
    reply = content.strip()[:12000]
    if not reply:
        return None
    provider = result.get("provider", "local-ollama")
    model = result.get("model") or ""
    if not isinstance(model, str) or provider not in (
        "local-ollama", "local-no-image",
    ):
        return None
    if provider == "local-no-image":
        if model:
            return None
        source = "desktop-local-no-image"
    else:
        # Even a legacy desktop sender must name a real Qwen family model.
        # The mobile text queue does not accept arbitrary Ollama/vision models.
        if not is_qwen_model(model):
            return None
        # A legacy desktop may submit unfiltered reasoning. Do not save it
        # into the shared thread or return it as user-visible assistant text.
        reply = strip_qwen_thinking(reply)
        if not reply:
            return None
        source = "desktop-local-ollama"
    return reply, model.strip()[:90], source

