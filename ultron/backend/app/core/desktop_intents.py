"""Only unambiguous desktop requests may bypass the conversational model.

This is deliberately a tiny allowlist. Other commands stay in the existing
approval-gated agent; do not convert free text into arbitrary shell commands.
"""
from __future__ import annotations

import re

_NOTEPAD_OPEN = re.compile(
    r"^(?:(?:gölge|golge)[,:! ]+)?(?:lütfen\s+)?"
    r"(?:not\s+defteri(?:['’]?ni)?|notepad(?:['’]i)?)\s+"
    r"(?:aç|açar\s+mısın|açabilir\s+misin)\s*[.!?]*$",
    re.IGNORECASE,
)
_ENGLISH_NOTEPAD_OPEN = re.compile(
    r"^(?:please\s+)?open\s+(?:the\s+)?notepad\s*[.!?]*$",
    re.IGNORECASE,
)
_MODEL_STATUS = re.compile(
    r"\bhangi\s+model(?:i|le)?\b.{0,80}\b"
    r"(?:kullan\w*|çalış\w*|calis\w*|yanıt\w*|yanit\w*)",
    re.IGNORECASE,
)


def safe_app_open_alias(text: str) -> str | None:
    """Return an allowlisted Windows application alias, never a command line."""
    if not isinstance(text, str) or len(text) > 180:
        return None
    value = text.strip()
    if _NOTEPAD_OPEN.fullmatch(value) or _ENGLISH_NOTEPAD_OPEN.fullmatch(value):
        return "notepad"
    return None


def asks_live_model_status(text: str) -> bool:
    """Separate runtime model facts from a language model's self-description."""
    if not isinstance(text, str) or len(text) > 240:
        return False
    return bool(_MODEL_STATUS.search(text.strip()))
