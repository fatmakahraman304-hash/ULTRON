"""Cheap presentation checks, not an oracle for truth or permission enforcement.

No extra inference, persistence, tool execution or logging of response content.
Code blocks and requested verbatim text are left untouched.
"""
from __future__ import annotations
import re

_LITERAL = re.compile(r'\b(?:aynen|harfi harfine|verbatim|exactly|repeat|tekrarla|şiir|poem)\b', re.I)


def assess_response(text: str, *, prompt: str = '') -> tuple[str, ...]:
    if not isinstance(text, str) or not text.strip():
        return ('empty',)
    flags = []
    if '```' not in text and not _LITERAL.search(prompt):
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text.strip())]
        if any(a == b and len(a) >= 40 for a, b in zip(paragraphs, paragraphs[1:])):
            flags.append('adjacent_duplicate')
    if re.search(r'\b(?:kısaca|tek cümle|briefly|short answer|one sentence)\b', prompt, re.I) and len(text) > 1800:
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
