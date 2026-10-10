"""Conservative explicit style slots and common-secret detection; no LLM inference."""
import re
import unicodedata

_SECRET = re.compile(
    r'(?:\b(?:sk-(?:proj-)?|gh[pousr]_|github_pat_|AIza)[A-Za-z0-9_-]{12,}'
    r'|-----BEGIN [A-Z ]*PRIVATE KEY-----'
    r'|\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}'
    r'|\bAKIA[A-Z0-9]{16}\b)', re.I)


def normalized_value(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split()).rstrip('.! ')


def contains_common_secret(value):
    return bool(_SECRET.search(unicodedata.normalize('NFKC', value)))


def explicit_style_slots(value):
    """Recognize only unambiguous, non-negated reply-style statements.

    Not a general fact contradiction detector. Ambiguous and mixed values yield
    no slot rather than silently inferring what the owner intended.
    """
    text = normalized_value(value)
    if re.search(r'\b(?:değil|istemiyorum|not|never|no|bazen|sometimes|için|for|when|sadece|only|konusunda)\b', text):
        return {}
    if not re.search(r'\b(?:cevap\w*|yanıt\w*|anlat\w*|answer\w*|repl(?:y|ies)|respond\w*)\b', text):
        return {}
    slots = {}
    short = bool(re.search(r'\b(?:kısa|kısaca|brief|short|concise)\b', text))
    long = bool(re.search(r'\b(?:detaylı|ayrıntılı|uzun|detailed|long)\b', text))
    if short != long:
        slots['length'] = 'brief' if short else 'detailed'
    tr = bool(re.search(r'\b(?:türkçe|turkish)\b', text))
    en = bool(re.search(r'\b(?:ingilizce|english)\b', text))
    if tr != en:
        slots['language'] = 'tr' if tr else 'en'
    return slots
