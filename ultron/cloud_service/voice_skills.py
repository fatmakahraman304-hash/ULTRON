"""Live-voice gateway to the instant skills (the `golge_skill` tool).

The voice model can ask GÖLGE's exact skills (weather, clock, calculator, reminders, lists …)
instead of guessing. Only a fixed set of low-risk writing skills is allowed by voice; smart home,
memory edits, plan deletion, alert cancel and laptop delegation keep their own dedicated, explicit paths.
Everything is owner-scoped and replies are made speakable (no URLs, no markdown).
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

if __package__:
    from . import instant_skills, followups
else:
    import instant_skills
    import followups

# Writing skills a spoken request may trigger. Anything not listed only answers read-only.
VOICE_WRITE_SKILLS = frozenset({"reminder", "reminders", "habits", "lists", "expenses", "focus", "birthdays", "style", "journal", "routines"})
MAX_UTTERANCE = 220
_URL = re.compile(r"https?://\S+")
_MARKUP = re.compile(r"[*_`#>]+")
MAX_SPOKEN = 700

TOOL_DECLARATION = {
    "name": "golge_skill",
    "description": (
        "Ask GÖLGE's exact built-in skills in the owner's own words (Turkish): time/date, calculator, unit and currency "
        "conversion, weather, news, prayer times, reminders and timers, shopping lists, expenses, habits, pomodoro, "
        "birthdays, agenda, 'what do you know about X' and 'what did we talk about yesterday'. Use it BEFORE guessing "
        "any live fact or when the owner wants something scheduled or saved. Pass the owner's request verbatim. "
        "If the result says handled=false, answer normally yourself. Never claim an action was done unless the reply says so."
    ),
    "parameters": {"type": "OBJECT", "properties": {"request": {"type": "STRING", "description": "The owner's request, verbatim, at most 200 characters."}},
                   "required": ["request"]},
}


def speakable(reply: str) -> str:
    """Strip links/markdown so the voice does not read URLs aloud."""
    text = _URL.sub("(bağlantıyı sohbet ekranına yazdım)", str(reply))
    text = _MARKUP.sub("", text)
    text = re.sub(r"\n+", ". ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text[:MAX_SPOKEN]


async def run(request: str, *, pool: Any, user_id: str, conv_uuid=None, fetch_json=None, location=None,
              fetch_text=None, now: datetime | None = None) -> dict:
    text = " ".join(str(request or "").split())[:MAX_UTTERANCE]
    if not text:
        return {"handled": False, "reason": "empty_request"}
    result = await instant_skills.instant_reply(
        text, pool=pool, user_id=user_id, fetch_json=fetch_json, now=now, location=location,
        fetch_text=fetch_text, allow=VOICE_WRITE_SKILLS)
    if not result:
        return {"handled": False, "reason": "not_a_builtin_skill"}
    reply = result["reply"]
    has_link = bool(_URL.search(reply))
    if conv_uuid is not None:
        try:  # the full text (with links) is kept in the conversation so the owner can read it
            await pool.execute(
                "INSERT INTO messages(conversation_id,user_id,role,content,device_id) VALUES($1,$2,'assistant',$3,$4)",
                conv_uuid, user_id, reply, followups.SKILL_PREFIX + result["skill"])
        except Exception:
            pass
    return {"handled": True, "skill": result["skill"], "spoken": speakable(reply), "has_link": has_link}
