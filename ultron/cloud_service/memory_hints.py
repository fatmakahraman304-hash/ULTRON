"""Consent-based memory suggestions: when the owner states a lasting personal fact, offer to remember it — never save it silently.

"kedimin adı Pamuk", "en sevdiğim renk mavi", "alerjim var: fıstık", "29 yaşındayım", "İzmir'de oturuyorum", "vejetaryenim"
→ the reply gets one extra line: “🧠 İstersen hatırlayayım: hatırla: …”. Questions, secrets and long messages never trigger it.
"""
from __future__ import annotations

import re

if __package__:
    from .text_normalization import fold_turkish
    from .memory_safety import contains_common_secret
else:
    from text_normalization import fold_turkish
    from memory_safety import contains_common_secret

_PATTERNS = (
    re.compile(r"^(?:benim\s+)?\w+(?:im|in|um|un|ım|ün|üm)\s+(?:adi|ismi)\s+[\w ]{2,30}$"),                       # kedimin adı Pamuk
    re.compile(r"^(?:benim\s+)?en\s+sevdigim\s+\w+(?:\s+\w+)?\s+[\w ]{2,30}$"),                                    # en sevdiğim renk mavi
    re.compile(r"^(?:benim\s+)?alerjim\s+var\b.{0,40}$|^[\w ]{2,30}\s+alerjim\s+var$"),                            # alerjim var: fıstık
    re.compile(r"^\d{1,2}\s+yasindayim$"),                                                                          # 29 yaşındayım
    re.compile(r"^[\w ]{2,25}'?(?:de|da|te|ta)\s+(?:oturuyorum|yasiyorum|calisiyorum)$"),                           # İzmir'de oturuyorum
    re.compile(r"^(?:ben\s+)?(?:vejetaryen|vegan|diyabet|glutensiz)\w*$"),                                        # vejetaryenim
    re.compile(r"^(?:benim\s+)?(?:esimin|annemin|babamin|kardesimin|cocugumun|ogrencimin)\s+[\w ]{2,40}$"),     # eşimin adı …
)
_QUESTION = re.compile(r"\?|\b(?:mi|mu|midir|nedir|nasil|neden|kim|kac)\b")


def hint(text: str) -> str:
    """Empty string, or the one-line suggestion to append to the reply."""
    raw = " ".join(str(text or "").split())
    if not 6 <= len(raw) <= 120:
        return ""
    folded = fold_turkish(raw).strip(" .!")
    if _QUESTION.search(folded) or contains_common_secret(raw):
        return ""
    if not any(p.match(folded) for p in _PATTERNS):
        return ""
    return f"\n\n🧠 İstersen bunu aklımda tutayım: “hatırla: {raw.strip(' .!')}” de, kaydederim (izin vermeden kaydetmiyorum)."
