"""Pure identity check shared by real Qwen evaluations and local chat.

Not a model availability probe: only the installed Ollama inventory can
establish availability. Reject unrelated or visual-only fallback families.
"""
from __future__ import annotations
import re

_QWEN_ID = re.compile(
    r"(?:[a-z0-9_.-]+/)*qwen(?:[0-9]|[-:.])[a-z0-9_.:-]*",
    re.I,
)


def is_qwen_model(model: str) -> bool:
    return (isinstance(model, str)
            and _QWEN_ID.fullmatch(model.strip()) is not None)
