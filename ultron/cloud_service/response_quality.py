"""Cheap presentation checks, not an oracle for truth or permission enforcement.

No extra inference, persistence, tool execution or logging of response content.
Code blocks and requested verbatim text are left untouched.
"""
from __future__ import annotations
import re

# Render launches `python app.py` with ultron/cloud_service as the working
# directory; the repository root is not importable as `ultron` there.
# Local desktop/tests may import this module through the package instead.
if __package__:
    from .reply_policy import classify_reply_mode
else:
    from reply_policy import classify_reply_mode

_LITERAL = re.compile(r'\b(?:aynen|harfi harfine|verbatim|exactly|repeat|tekrarla|şiir|poem)\b', re.I)


_QWEN_THINK_START = re.compile(r'(?im)^[ \t]*<think>[ \t]*\r?$')
_QWEN_THINK_END = re.compile(r'(?im)^[ \t]*</think>[ \t]*\r?$')


def strip_qwen_thinking(text: str) -> str:
    """Remove generated thinking prose from Qwen content, not user code.

    Some Ollama/Qwen versions return a thought preamble in message.content
    despite think=False, sometimes without an opening <think> marker.
    Never publish an unfinished think block. Fenced code is preserved.
    """
    if not isinstance(text, str):
        return ""
    answer = text.strip()

    def outside_fence(pos: int) -> bool:
        return answer[:pos].count(chr(96) * 3) % 2 == 0

    closing = [m for m in _QWEN_THINK_END.finditer(answer)
               if outside_fence(m.start())]
    if closing:
        answer = answer[closing[-1].end():].strip()
    if any(outside_fence(m.start()) for m in _QWEN_THINK_START.finditer(answer)):
        return ""
    return answer


def assess_response(text: str, *, prompt: str = '') -> tuple[str, ...]:
    if not isinstance(text, str) or not text.strip():
        return ('empty',)
    flags = []
    if '```' not in text and not _LITERAL.search(prompt):
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text.strip())]
        if any(a == b and len(a) >= 40 for a, b in zip(paragraphs, paragraphs[1:])):
            flags.append('adjacent_duplicate')
    # A negated style phrase ("kısa cevap istemiyorum") is not a brief
    # request. Use the exact same style decision as the model's runtime.
    if classify_reply_mode(prompt) == 'brief' and len(text) > 1800:
        flags.append('possibly_too_long')
    # Signals for evaluation only: these are not reliable semantic verdicts.
    return tuple(flags)


def finalize_response(text: str, *, prompt: str = '') -> str:
    """Only remove identical, adjacent prose paragraphs; never truncate an answer."""
    answer = text.strip()
    if 'adjacent_duplicate' not in assess_response(answer, prompt=prompt):
        return answer
    kept = []
    for paragraph in re.split(r'\n\s*\n', answer):
        paragraph = paragraph.strip()
        if kept and len(paragraph) >= 40 and paragraph == kept[-1]:
            continue
        kept.append(paragraph)
    return '\n\n'.join(kept)
