"""Pure, shared response-length policy for Cloud persona and local Qwen.

Explicit last *affirmative* request wins; negated style words are ignored.
No model calls, personal data, I/O, background monitoring or memory writes.
"""
from __future__ import annotations
import re
if __package__:
    from .text_normalization import fold_turkish, folded_regex
else:
    from text_normalization import fold_turkish, folded_regex

_BRIEF = folded_regex(
    r"(?:\b(?:kısaca|kısa (?:cevap|anlat|tut|tutalım|yaz|söyle|olsun|özet)|özetle|tek cümle(?:yle)?|"
    r"briefly|short answer|in one sentence)\b)", re.I
)
_DEEP = folded_regex(
    r"(?:\b(?:detaylı(?:ca)?|ayrıntılı(?:ca)?|adım adım|en ince ayrıntısına|"
    r"derinlemesine|thoroughly|in detail|step by step)\b)", re.I
)

# The latest affirmative request wins. A phrase such as "kısa cevap
# istemiyorum, detaylı anlat" is NOT a request for a short reply.
_NEGATED_AFTER = folded_regex(
    r"^(?:değil|degil|istemiyorum|istemem|istemedim|olmasın|olmasin|"
    r"verme|anlatma|yapma|olmasın|not|no)\b", re.I
)
_NEGATED_BEFORE = folded_regex(r"\b(?:not|no|without)\s+$", re.I)

def classify_reply_mode(message: str) -> str:
    """One-turn preference for response length, independent of stored memory."""
    text = fold_turkish(message).strip()
    requests = []
    for pattern, mode in ((_BRIEF, "brief"), (_DEEP, "detailed")):
        for hit in pattern.finditer(text):
            before = text[max(0, hit.start() - 16):hit.start()]
            after = text[hit.end():hit.end() + 40].lstrip()
            if _NEGATED_AFTER.match(after) or _NEGATED_BEFORE.search(before):
                continue
            requests.append((hit.start(), mode))
    # Prefer the final *affirmative* instruction, not a negated earlier one.
    return max(requests, default=(-1, "natural"))[1]
