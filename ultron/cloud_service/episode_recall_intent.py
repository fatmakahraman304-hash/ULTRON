"""Lightweight episode-recall intent detection shared by cloud and desktop."""
from __future__ import annotations

import re

if __package__:
    from .text_normalization import fold_turkish
else:
    from text_normalization import fold_turkish


_EPISODE_RECALL = re.compile(fold_turkish(
    r"\b(?:geçen\s+(?:hafta|ay|sefer|yıl)|dün|bir\s+hafta\s+önce|"
    r"son\s+(?:[1-9]\d?|[12]\d{2}|3[0-5]\d|36[0-5])\s+gün|"
    r"yesterday|last\s+(?:week|month|year|time)|"
    r"a\s+week\s+ago|(?:past|last)\s+(?:(?:[1-9]\d?|[12]\d{2}|3[0-5]\d|36[0-5])|seven|thirty)\s+days)\b.{0,120}\b(?:"
    r"ne(?:ler|yi)?\s+(?:konuş\w*|yap\w*|geliştir\w*|çalış\w*|kararlaştır\w*|ol\w*)|"
    r"hangi\s+(?:görev|proje|karar|konu)\w*|hatırla|hatırlıyor|"
    r"what\s+(?:did|were|happened)|which\s+(?:task|project|decision)|remember|recall)\b|"
    r"\b(?:what\s+(?:did|were|happened)|which\s+(?:task|project|decision))\b"
    r".{0,100}\b(?:yesterday|last\s+(?:week|month|year)|a\s+week\s+ago|"
    r"past\s+(?:7|seven|30|thirty)\s+days)\b|"
    r"\b(?:son|önceki)\s+(?:proje|görev|toplantı|konu)\w*\s+(?:karar|gelişme)\w*\b|"
    r"\b(?:what\s+was\s+my|which\s+was\s+the)\b.{0,60}\b(?:last|previous)\b"
    r".{0,40}\b(?:project|task|meeting|topic|idea)\b.{0,30}\b(?:decision|update|work)\b",
), re.I)


def is_episode_recall_request(question: str) -> bool:
    """Route explicit retrospective questions to saved episodes, never general chat."""
    text = str(question or "").strip()
    return len(text) <= 600 and bool(_EPISODE_RECALL.search(fold_turkish(text)))
