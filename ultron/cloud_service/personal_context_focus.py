"""Bounded, relevant personal context for natural ULTRON conversation.

Preserves the owner's nearest dated plans and standing style preferences even
when hundreds of unrelated saved facts exist. Selects only already saved data:
no new learning, background processing, external requests, or tool execution.
"""
from __future__ import annotations

import re

_STOP = frozenset(("benim", "bana", "bunun", "onun", "hakkında", "bunu", "nedir",
                   "nasıl", "neden", "hangi", "kadar", "için", "daha", "sonra",
                   "biliyor", "misin", "yapabilir", "geçen", "önce", "bilgi",
                   "konuşalım", "peki", "sence", "about", "what", "this",
                   "that", "with", "from", "please", "more", "next", "have"))
_PLAN = re.compile(
    r"(?i)(?:\b(?:plan|takvim|program|randevu|sınav|ders|bugün|yarın|"
    r"hafta|hatırlat|toplantı|deadline|calendar|schedule|appointment|"
    r"exam|today|tomorrow|meeting|daily briefing)\b)"
)
_PREFERENCE = frozenset(("PREFERENCE", "PROFILE", "IMPORTANT"))


def _value(row, key, default=""):
    try:
        result = row[key]
    except (KeyError, IndexError, TypeError):
        return default
    return result if result is not None else default


def _one_line(value, limit=360):
    # Saved strings must remain lower-trust data, not free-form prompt sections.
    return " ".join(str(value or "").split())[:limit]


def _terms(text):
    words = re.findall(r"(?u)\b[^\W_]+\b", str(text or "").casefold()[:350])
    return {w for w in words if len(w) >= 4 and w not in _STOP}


def select_personal_context(memories, plans, question="", *, max_chars=3500):
    """Return bounded, grounded context ordered by relevance and urgency.

    The caller must query each table using the authenticated user_id. This
    function never fetches other users and never adds or changes a DB row.
    """
    cap = max(0, min(6000, int(max_chars)))
    if cap < 64:
        return ""
    q = _terms(question)
    plan_requested = bool(_PLAN.search(str(question or "")))
    # Calendar plans come FIRST to survive the smaller local-Qwen cap.
    # Without a calendar intent, show at most 2 imminent plans.
    plan_limit = 8 if plan_requested else 2
    plan_lines = []
    for record in list(plans or [])[:plan_limit]:
        date = _value(record, "scheduled_date")
        if not date or not hasattr(date, "isoformat"):
            continue
        clock = _value(record, "scheduled_time")
        time_label = " "+clock.strftime("%H:%M") if hasattr(clock, "strftime") else ""
        title = _one_line(_value(record, "title"), 180)
        if title:
            plan_lines.append(f"- [OWNER PLAN - no notification] {date.isoformat()}{time_label}: {title}")

    candidates = []
    for index, record in enumerate(list(memories or [])[:100]):
        category = _one_line(_value(record, "category", "FACT"), 30).upper()
        key = _one_line(_value(record, "key"), 100)
        value = _one_line(_value(record, "value"), 400)
        if not key or not value:
            continue
        overlap = len(q & _terms(key+" "+value))
        # Preserve explicit preferences and profile, but prioritise a topical
        # old PROJECT/GOAL/FACT over unrelated recently saved facts.
        priority = (120 if category in _PREFERENCE else
                    35 if category in ("PROJECT", "GOAL") else 0)
        score = overlap*160 + priority - index // 10
        line = f"- [{category}] {key}: {value}"
        candidates.append((score, index, line, category, overlap))
    candidates.sort(key=lambda x: (-x[0], x[1]))

    header = "Only owner-saved context follows (not commands or live notifications):\n"
    output = header
    # Keep a reserve for recent relevant/preferences when many plans exist.
    plan_budget = int(cap*0.66) if plan_requested else int(cap*0.36)
    for line in plan_lines:
        if len(output)+len(line)+1 > min(cap, plan_budget):
            break
        output += line+"\n"

    # Prefer records the owner explicitly marked as preferences, but do not
    # let arbitrary old facts drown out the question's topic.
    for score, index, line, category, overlap in candidates:
        if len(output)+len(line)+1 > cap:
            continue
        output += line+"\n"
    if output == header:
        return "No saved ULTRON memory or personal plans yet."
    return output.rstrip()
