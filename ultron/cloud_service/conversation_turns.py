"""Conversation-aware history for more coherent ULTRON dialogue.

Only the authenticated owner's *current conversation* is used. Text from chat
history remains untrusted user/assistant content, never a tool or system role.
Short bounded recent turns fit the small 4GB laptop GPU memory budget.
"""
from __future__ import annotations

import re


def prepare_turns(rows, *, max_chars: int = 3200, max_turns: int = 14) -> list[dict[str, str]]:
    """Return recent chronological user/assistant turns, with newest priority."""
    cap = max(0, min(int(max_chars), 7200))
    count = max(0, min(int(max_turns), 20))
    if count == 0 or cap == 0:
        return []
    kept: list[dict[str, str]] = []
    remaining = cap
    for record in reversed(list(rows)[-count:]):
        if not hasattr(record, "get"):
            continue
        role = record.get("role")
        text = record.get("content")
        if role not in ("user", "assistant") or not isinstance(text, str):
            continue
        text = text.strip()
        if not text or remaining < 24:
            continue
        # Preserve the end of the latest short answer if an old turn was huge.
        size = min(1000, remaining)
        text = text[:size].strip()
        if not text:
            continue
        kept.append({"role": role, "content": text})
        remaining -= len(text)
    kept.reverse()
    return kept


async def load_thread_turns(pool, user_id: str, conversation_id, *,
                            before_id: int | None = None,
                            max_chars: int = 3200, limit: int = 14) -> list[dict[str, str]]:
    """Fetch only prior turns in one conversation, never cross-owner or current."""
    n = max(1, min(int(limit), 20))
    rows = await pool.fetch(
        "SELECT role,content FROM messages "
        "WHERE user_id=$1 AND conversation_id=$2 "
        "AND ($3::bigint IS NULL OR id < $3) AND role IN ('user','assistant') "
        "ORDER BY id DESC LIMIT $4",
        user_id, conversation_id, before_id, n,
    )
    return prepare_turns(list(reversed(rows)), max_chars=max_chars, max_turns=n)


def ollama_messages(system: str, turns, current: str) -> list[dict[str, str]]:
    """Create only system/user/assistant roles; history never becomes system."""
    result = [{"role": "system", "content": str(system or "")[:5400]}]
    result.extend(prepare_turns(turns, max_chars=2600, max_turns=12))
    result.append({"role": "user", "content": str(current or "")[:3000]})
    return result


def gemini_turns(turns, current: str) -> list[dict[str, str]]:
    result = [{"role": "model" if t["role"] == "assistant" else "user",
               "content": t["content"]}
              for t in prepare_turns(turns, max_chars=5200, max_turns=16)]
    result.append({"role": "user", "content": str(current or "")[:16000]})
    return result


# Match explicit topic names in long-running chats, without using a second LLM,
# another account's data, or storing implicit memories. Pronoun-only followups
# deliberately rely on the immediate thread, not a guessed old subject.
_COMMON_TERMS = frozenset((
    "biraz", "bunu", "bunun", "nasıl", "nasil", "nedir", "neden", "hangi",
    "hakkında", "hakkinda", "konu", "konuşma", "konusma", "önceki", "onceki",
    "söyle", "soyle", "anlat", "detaylı", "detayli", "devam", "eder", "peki",
    "onun", "olan", "sence", "fiyatı", "fiyati", "kaç", "kadar", "nasıldı",
    "hatırlıyor", "hatirliyor", "hatırla", "hatirla", "geçen", "gecen",
    "message", "about", "which", "could", "would", "where", "what",
    "previous", "remember", "please", "tell", "more", "that", "this",
    "than", "then", "continue", "conversation",
))


def _topic_terms(text: str) -> set[str]:
    if not isinstance(text, str):
        return set()
    tokens = re.findall(r"(?u)\b[^\W_]+\b", text.casefold()[:280])
    return {word for word in tokens
            if (len(word) >= 5 or (len(word) >= 3 and any(c.isdigit() for c in word)))
            and word not in _COMMON_TERMS and not word.isdigit()}


def select_contextual_turns(rows, question: str, *, max_chars: int = 3200,
                            max_turns: int = 14) -> list[dict[str, str]]:
    """Keep immediate chat plus a small chronological selection of older matches.

    Older recall requires a distinctive explicit question term. It never
    becomes a system instruction or a persisted user profile.
    """
    cap = max(0, min(int(max_chars), 7200))
    count = max(0, min(int(max_turns), 20))
    if cap == 0 or count == 0:
        return []
    clean = [
        {"role": row.get("role"), "content": row.get("content")}
        for row in rows
        if hasattr(row, "get")
        and row.get("role") in ("user", "assistant")
        and isinstance(row.get("content"), str)
    ]
    if len(clean) <= count:
        return prepare_turns(clean, max_chars=cap, max_turns=count)
    terms = _topic_terms(question)
    if not terms:
        return prepare_turns(clean, max_chars=cap, max_turns=count)
    # Always reserve most history for the latest back-and-forth, even when an
    # ancient message matches a word in the latest question.
    recent_count = max(2, count - 4)
    recent = clean[-recent_count:]
    earlier = clean[:-recent_count]
    ranked = [
        (len(terms & _topic_terms(message["content"])), index, message)
        for index, message in enumerate(earlier)
    ]
    ranked = [item for item in ranked if item[0] > 0]
    if not ranked:
        return prepare_turns(clean, max_chars=cap, max_turns=count)
    # Prefer multiple distinctive matches and newer examples on ties.
    chosen = sorted(
        sorted(ranked, key=lambda item: (item[0], item[1]), reverse=True)[:4],
        key=lambda item: item[1],
    )
    older_budget = max(120, cap // 4)
    old_turns = prepare_turns(
        [item[2] for item in chosen],
        max_chars=older_budget, max_turns=min(4, count - recent_count),
    )
    recent_turns = prepare_turns(
        recent, max_chars=cap - sum(len(x["content"]) for x in old_turns),
        max_turns=recent_count,
    )
    return old_turns + recent_turns



# An explicit on-demand recap spans the beginning, middle and end of only the
# currently selected conversation. Normal follow-ups keep recency priority.
_RECAP_PATTERNS = (
    re.compile(r"^(?:ultron[,.!? ]+)?(?:bu |bizim )?(?:sohbeti|sohbetimizi|konuşmayı|konuşmamızı|"
               r"konuştuklarımızı) (?:kısaca |bana )?(?:özetle|özetler misin|özetini çıkar|"
               r"özetini çıkart)(?: lütfen| lütfen)?[.?!]*$", re.I),
    re.compile(r"^(?:az önce|bu sohbette|bu konuşmada|şimdiye kadar) "
               r"(?:ne |neler )?(?:konuştuk|konuşmuştuk|konuştuklarımız nelerdi)"
               r"(?:\?)?$", re.I),
    re.compile(r"^(?:please )?(?:summarize|recap) (?:our|this|the) (?:chat|conversation)"
               r"(?: please)?[.?!]*$", re.I),
    re.compile(r"^what (?:did|have) we (?:discuss|talked about) "
               r"(?:in this chat|so far)[.?!]*$", re.I),
)


def is_thread_recap_request(question: str) -> bool:
    if not isinstance(question, str) or len(question) > 180:
        return False
    text = " ".join(question.strip().split())
    return any(pattern.fullmatch(text) is not None for pattern in _RECAP_PATTERNS)


def select_recap_turns(rows, *, max_chars: int = 3200,
                       max_turns: int = 14) -> list[dict[str, str]]:
    """Read-only recap context sampled chronologically across one old thread.

    This does not generate a summary, store anything, or grant tool permissions.
    The model sees ordinary untrusted conversation roles only.
    """
    cap = max(0, min(int(max_chars), 7200))
    count = max(0, min(int(max_turns), 20))
    if cap == 0 or count == 0:
        return []
    clean = [
        {"role": row.get("role"), "content": row.get("content")}
        for row in rows
        if hasattr(row, "get")
        and row.get("role") in ("user", "assistant")
        and isinstance(row.get("content"), str)
        and row.get("content").strip()
    ]
    if len(clean) <= count or count < 4:
        return prepare_turns(clean, max_chars=cap, max_turns=count)

    beginning_count = max(1, count // 4)
    middle_count = max(1, count // 6) if count >= 6 else 0
    recent_count = count - beginning_count - middle_count
    beginning = clean[:beginning_count]
    midpoint = (len(clean) - middle_count) // 2
    middle = clean[midpoint:midpoint + middle_count] if middle_count else []
    recent = clean[-recent_count:]

    beginning_turns = prepare_turns(
        beginning, max_chars=cap // 4, max_turns=beginning_count,
    )
    middle_turns = prepare_turns(
        middle, max_chars=cap // 5, max_turns=middle_count,
    ) if middle_count else []
    used = sum(len(t["content"]) for t in beginning_turns + middle_turns)
    recent_turns = prepare_turns(
        recent, max_chars=cap - used, max_turns=recent_count,
    )
    return beginning_turns + middle_turns + recent_turns


async def load_contextual_thread_turns(pool, user_id: str, conversation_id,
                                       *, question: str, before_id: int | None = None,
                                       max_chars: int = 3200,
                                       limit: int = 14, lookback: int = 80
                                       ) -> list[dict[str, str]]:
    """Look back only in the authenticated owner's named conversation.

    No global cross-conversation search, automatic facts or extra model calls.
    SQL LIMIT and output caps bound database and model usage.
    """
    n = max(1, min(int(limit), 20))
    if is_thread_recap_request(question):
        window = max(n, min(int(lookback), 80))
        rows = await pool.fetch(
            "SELECT role,content FROM messages "
            "WHERE user_id=$1 AND conversation_id=$2 "
            "AND ($3::bigint IS NULL OR id < $3) "
            "AND role IN ('user','assistant') "
            "ORDER BY id DESC LIMIT $4",
            user_id, conversation_id, before_id, window,
        )
        return select_recap_turns(
            list(reversed(rows)), max_chars=max_chars, max_turns=n,
        )
    terms = _topic_terms(question)
    if not terms:
        return await load_thread_turns(
            pool, user_id, conversation_id, before_id=before_id,
            max_chars=max_chars, limit=n,
        )
    lookback = max(n, min(int(lookback), 80))
    rows = await pool.fetch(
        "SELECT role,content FROM messages "
        "WHERE user_id=$1 AND conversation_id=$2 "
        "AND ($3::bigint IS NULL OR id < $3) AND role IN ('user','assistant') "
        "ORDER BY id DESC LIMIT $4",
        user_id, conversation_id, before_id, lookback,
    )
    return select_contextual_turns(
        list(reversed(rows)), question,
        max_chars=max_chars, max_turns=n,
    )
