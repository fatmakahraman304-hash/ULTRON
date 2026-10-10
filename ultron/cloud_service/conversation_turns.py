"""Conversation-aware history for more coherent ULTRON dialogue.

Only the authenticated owner's *current conversation* is used. Text from chat
history remains untrusted user/assistant content, never a tool or system role.
Short bounded recent turns fit the small 4GB laptop GPU memory budget.
"""
from __future__ import annotations


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
