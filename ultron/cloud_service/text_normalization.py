"""Match everyday Turkish typed with or without diacritics.

Only classification/search strings are folded. Original user text and saved
conversation content remain unchanged and are what the models receive.
"""
from __future__ import annotations

import re
import unicodedata


def fold_turkish(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(char for char in text if not unicodedata.combining(char)).replace("ı", "i")


def folded_regex(pattern: str, flags: int = 0) -> re.Pattern:
    return re.compile(fold_turkish(pattern), flags)
