"""Conversation-aware history for more coherent ULTRON dialogue.

Only the authenticated owner's *current conversation* is used. Text from chat
history remains untrusted user/assistant content, never a tool or system role.
Short bounded recent turns fit the small 4GB laptop GPU memory budget.
"""
from __future__ import annotations

import re
if __package__:
    from .text_normalization import fold_turkish, folded_regex
else:
    from text_normalization import fold_turkish, folded_regex


def _bounded_excerpt(text: str, size: int) -> str:
    """Preserve an older message's opening AND its final correction.

    Previous head-only truncation silently dropped constraints at the end of
    long messages. Excerpt boundaries stay explicit, within the old cap.
    """
    if len(text) <= size:
        return text
    if size <= 0:
        return ""
    marker = " … [middle omitted] … "
    if size < 80:
        return text[-size:]
    available = size - len(marker)
    front = available * 3 // 5
    return text[:front].rstrip() + marker + text[-(available-front):].lstrip()


def bounded_user_request(prompt: str, size: int) -> str:
    """Preserve the opening *and latest correction* of an overlong user turn.

    A request is never expanded beyond the caller's original provider limit.
    Normal short questions remain byte-for-byte unchanged after outer trim.
    """
    return _bounded_excerpt(str(prompt or "").strip(), size).strip()


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
        text = _bounded_excerpt(text, size).strip()
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
    result.append({"role": "user", "content": bounded_user_request(current, 3000)})
    return result


def gemini_turns(turns, current: str) -> list[dict[str, str]]:
    result = [{"role": "model" if t["role"] == "assistant" else "user",
               "content": t["content"]}
              for t in prepare_turns(turns, max_chars=5200, max_turns=16)]
    result.append({"role": "user", "content": bounded_user_request(current, 16000)})
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
    "demiştik", "konuşmuştuk", "hatırlat", "söylediklerimi",
    "konuştuklarımız", "previously", "earlier", "discussed", "discuss",
    "remember", "remind", "said", "talked",
))

# Meaningful short acronyms are worth recalling, but generic 3-4 letter
# Turkish/English words would create many irrelevant keyword matches.
_TOPIC_SHORT = frozenset((
    "daü", "ydü", "kktc", "qwen", "siri", "wifi", "ios", "rtx",
    "gpu", "cpu", "api", "usb", "ram", "ssd", "llm", "pdf", "pwa",
))


def _topic_terms(text: str) -> set[str]:
    if not isinstance(text, str):
        return set()
    normalized = text.casefold()
    # Topic names can occur at the end of a long request, not just its start.
    # Avoid a full scan of arbitrarily large pasted documents.
    excerpt = (normalized if len(normalized) <= 1200
               else normalized[:600] + " " + normalized[-600:])
    tokens = re.findall(r"(?u)\b[^\W_]+\b", excerpt)
    return {word for word in tokens
            if (len(word) >= 5 or (len(word) >= 3 and any(c.isdigit() for c in word))
                or word in _TOPIC_SHORT)
            and word not in _COMMON_TERMS and not word.isdigit()}


_TOPIC_SWITCH = folded_regex(
    r"(?:\b(?:konuyu|konumuzu|mevzuyu)\s+değiştir(?:elim|mek)?\b|"
    r"\b(?:başka|yeni)(?: bir)? konuya geç(?:elim|mek)?\b|"
    r"\b(?:bu konuyu|bunu)\s+bırak(?:alım)?\b|"
    r"\bswitch (?:the )?topic\b|\bchange the subject\b|"
    r"\bnew topic\b|\b(?:let's|lets) talk about something else\b|"
    r"\bmove on to (?:a )?(?:new|another) topic\b)",
    re.I,
)


def is_topic_switch_request(question: str) -> bool:
    """Only explicit topic-change intent suppresses older topic retrieval."""
    return (isinstance(question, str) and len(question) <= 320 and
            bool(_TOPIC_SWITCH.search(fold_turkish(" ".join(question.strip().split())))))


_OLD_TURN_CORRECTION = folded_regex(
    r"^(?:hayır\b|yok\b(?!\s+(?:mu|mı|mi|mü)\b)|"
    r"yanlış anladın\b|onu demedim\b|düzeltme\s*:|"
    r"aslında\b.{0,95}\b(?:kastettim|demiştim|istiyorum|olacak|olsun)\b|"
    r"no[,!:]\s|no,?\s+i meant\b|"
    r"actually,?\s+i meant\b|correction\s*:)",
    re.I | re.S,
)


def is_explicit_turn_correction(text: str) -> bool:
    """A clear owner correction directly after an old assistant response."""
    return isinstance(text, str) and bool(
        _OLD_TURN_CORRECTION.match(fold_turkish(text.strip()[:180]))
    )


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
    if len(clean) <= count or count < 4 or is_topic_switch_request(question):
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
    # Recall evidence as an adjacent exchange, not disconnected keyword hits.
    indices = set()
    for _, index, message in sorted(ranked, key=lambda item: (item[0], item[1]), reverse=True):
        pair = {index}
        if message["role"] == "user" and index + 1 < len(earlier) and earlier[index + 1]["role"] == "assistant":
            pair.add(index + 1)
        elif message["role"] == "assistant" and index > 0 and earlier[index - 1]["role"] == "user":
            pair.add(index - 1)
        # A corrected exchange is one evidence unit: never recall the old
        # answer without the owner's immediately following correction merely
        # because the correction does not repeat the topic name.
        following = max(pair) + 1
        if (following < len(earlier)
                and earlier[following]["role"] == "user"
                and is_explicit_turn_correction(earlier[following]["content"])):
            pair.add(following)
        if len(indices | pair) <= min(4, count - recent_count):
            indices.update(pair)
    chosen = [earlier[index] for index in sorted(indices)]
    older_budget = cap // 4
    # A verbose answer must not consume its question's entire evidence budget.
    # Reserve a share for each selected role before newest-first truncation.
    share = older_budget // max(1, len(chosen))
    # The old exchange may end with the actual answer or a user correction.
    # Head-only truncation misrepresented such evidence as if the ending had
    # never been stated. Keep opening and conclusion under the SAME cap.
    evidence = [
        {"role": row["role"], "content": _bounded_excerpt(row["content"], share)}
        for row in chosen
    ]
    old_turns = prepare_turns(
        evidence,
        max_chars=older_budget, max_turns=min(4, count - recent_count),
    )
    recent_turns = prepare_turns(
        recent, max_chars=cap - sum(len(x["content"]) for x in old_turns),
        max_turns=recent_count,
    )
    return old_turns + recent_turns




# A long-running project often contains dozens of short "devam et" turns.
# The original concrete request must not disappear merely because the latest
# 12-16 turns are all status updates. Never make an invented task anchor.
_BARE_CONTINUATION = folded_regex(
    r"^(?:(?:gölge|golge|ultron)[,!: ]+)?"
    r"(?:devam(?: et)?|aynen devam et|devam o zaman|"
    r"kaldığın yerden devam(?: et)?|kaldig(in)? yerden devam(?: et)?|"
    r"devam et büyük aşamaya|büyük aşamaya devam et|"
    r"continue|go on|keep going|carry on)"
    r"[.! ]*$", re.I,
)


def is_bare_continuation_request(question: str) -> bool:
    """A short go-ahead, not an explicit named new task or reminder."""
    return isinstance(question, str) and len(question) <= 140 and bool(
        _BARE_CONTINUATION.fullmatch(fold_turkish(" ".join(question.strip().split())))
    )


def select_continuation_turns(rows, *, max_chars: int = 3200,
                              max_turns: int = 14) -> list[dict[str, str]]:
    """Carry the last explicit *owner* goal through a sea of 'continue' turns.

    Return only original user/assistant roles, never instructions synthesized
    from model outputs. A topic switch or a substantive recent owner request
    prevents an older project from being revived. Read-only, bounded, no extra
    model request or memory writes.
    """
    cap = max(0, min(int(max_chars), 7200))
    count = max(0, min(int(max_turns), 20))
    if cap == 0 or count == 0:
        return []
    clean = [
        {"role": row.get("role"), "content": row.get("content").strip()}
        for row in rows
        if hasattr(row, "get") and row.get("role") in ("user", "assistant")
        and isinstance(row.get("content"), str) and row.get("content").strip()
    ]
    if len(clean) <= count or count < 4:
        return prepare_turns(clean, max_chars=cap, max_turns=count)

    recent_count = count - 2
    recent = clean[-recent_count:]
    # A recent *correction* is a constraint on an earlier task, not an
    # independent replacement goal. Keep the older goal when the last short
    # user messages contain only continuations and corrections.
    # An actual concrete new request or a topic switch still supersedes it.
    if any(row["role"] == "user" and
           (is_topic_switch_request(row["content"]) or
            (not is_bare_continuation_request(row["content"])
             and not is_explicit_turn_correction(row["content"])))
           for row in recent):
        return prepare_turns(clean, max_chars=cap, max_turns=count)

    earlier = clean[:-recent_count]
    # Do not recover a task from before the most recent topic switch.
    switch_index = max(
        (i for i, row in enumerate(earlier)
         if row["role"] == "user" and is_topic_switch_request(row["content"])),
        default=-1,
    )
    task = None
    correction = None
    for row in reversed(earlier[switch_index + 1:]):
        if row["role"] != "user" or is_bare_continuation_request(row["content"]):
            continue
        if is_explicit_turn_correction(row["content"]):
            if correction is None:
                correction = row
            continue
        task = row
        break
    if task is None:
        # A correction alone ("Hayır, onu değil") must not conjure an older task.
        return prepare_turns(clean, max_chars=cap, max_turns=count)

    # Prioritize the actual owner's goal and their latest correction. Both
    # remain ordinary user turns and keep original chronology.
    anchors = [task]
    if correction is not None:
        anchors.append(correction)
    allowance = max(64, cap // 3)
    share = max(24, allowance // len(anchors))
    originals = [
        {"role": "user", "content": _bounded_excerpt(item["content"], share)}
        for item in anchors
    ]
    anchors_ready = prepare_turns(originals, max_chars=allowance,
                                  max_turns=len(originals))
    remaining = cap - sum(len(x["content"]) for x in anchors_ready)
    tail = prepare_turns(recent, max_chars=remaining,
                         max_turns=count - len(anchors_ready))
    return anchors_ready + tail


# An explicit on-demand recap spans the beginning, middle and end of only the
# currently selected conversation. Normal follow-ups keep recency priority.
_RECAP_PATTERNS = (
    folded_regex(r"^(?:ultron[,.!? ]+)?(?:bu |bizim )?(?:sohbeti|sohbetimizi|konuşmayı|konuşmamızı|"
               r"konuştuklarımızı) (?:kısaca |bana )?(?:özetle|özetler misin|özetini çıkar|"
               r"özetini çıkart)(?: lütfen| lütfen)?[.?!]*$", re.I),
    folded_regex(r"^(?:az önce|bu sohbette|bu konuşmada|şimdiye kadar) "
               r"(?:ne |neler )?(?:konuştuk|konuşmuştuk|konuştuklarımız nelerdi)"
               r"(?:\?)?$", re.I),
    folded_regex(r"^(?:please )?(?:summarize|recap) (?:our|this|the) (?:chat|conversation)"
               r"(?: please)?[.?!]*$", re.I),
    folded_regex(r"^what (?:did|have) we (?:discuss|talked about) "
               r"(?:in this chat|so far)[.?!]*$", re.I),
)


def is_thread_recap_request(question: str) -> bool:
    if not isinstance(question, str) or len(question) > 180:
        return False
    text = fold_turkish(" ".join(question.strip().split()))
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


_FIRST_RETURN = folded_regex(
    r"^(?:ilk (?:söylediğine|söylediğime|söylediğimize|konuya|konuştuğumuz konuya)|"
    r"başlangıçtaki konuya) (?:geri )?dön(?:elim)?[.!?]*$|"
    r"^(?:go |let's go )?back to (?:the |our )?first (?:topic|thing we discussed)[.!?]*$",
    re.I,
)


def is_first_topic_return(question: str) -> bool:
    return isinstance(question, str) and len(question) <= 180 and bool(
        _FIRST_RETURN.fullmatch(fold_turkish(" ".join(question.strip().split()))))


_REMINDER_VERB = folded_regex(
    r"\b(?:hatırlat|hatirlat|anımsat|animsat|remind me)\b", re.I
)
_FUTURE_REMINDER = folded_regex(
    r"\b(?:yarın|yarin|öbür gün|haftaya|gelecek hafta|"
    r"tomorrow|tonight|next week|"
    r"saat\s*[0-2]?\d(?::[0-5]\d)?|"
    r"at\s+\d{1,2}(?::[0-5]\d)?\s*(?:am|pm)?|"
    r"in\s+\d+\s+(?:minutes?|hours?|days?)|"
    r"\d+\s+(?:dakika|saat|gün)\s+sonra)\b", re.I
)


def is_future_reminder_request(question: str) -> bool:
    """Do not mistake a scheduled reminder for a past-conversation recall."""
    return isinstance(question, str) and len(question) <= 320 and bool(
        _REMINDER_VERB.search(fold_turkish(question)) and
        _FUTURE_REMINDER.search(fold_turkish(question))
    )


_NAMED_RECALL = folded_regex(
    r"\b(?:ne demiştik|ne konuşmuştuk|ne konuştuk|"
    r"(?:konuştuğumuzu|konuşmamızı|sohbetimizi|konuştuklarımızı)\s+hatırlat|"
    r"hatırlıyor musun|daha önce ne|"
    r"what did we (?:say|discuss|decide)|remind me what|"
    r"what (?:have|did) we discussed|previously discussed)\b",
    re.I,
)


def is_named_recall_request(question: str) -> bool:
    """Only explicit old-topic recall warrants an older-than-window SQL lookup."""
    return isinstance(question, str) and len(question) <= 280 and bool(
        _NAMED_RECALL.search(fold_turkish(" ".join(question.strip().split())))
    ) and not is_future_reminder_request(question)


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
    if is_future_reminder_request(question):
        # Scheduling is an action request, not an instruction to recover
        # old plans. Keep only bounded recent context; no memory writes.
        return await load_thread_turns(
            pool, user_id, conversation_id, before_id=before_id,
            max_chars=max_chars, limit=n,
        )
    if is_topic_switch_request(question):
        # Explicit change of subject should not scan 80 old turns and revive
        # prior discussion simply because its name appears in this request.
        return await load_thread_turns(
            pool, user_id, conversation_id, before_id=before_id,
            max_chars=max_chars, limit=n,
        )
    if is_bare_continuation_request(question):
        # The last explicit owner goal may be older than the latest small
        # Qwen/Gemini window after repeated short continuations. Fetch a
        # bounded single-thread slice and reserve two turns for owner intent.
        window = max(n, min(int(lookback), 80))
        rows = await pool.fetch(
            "SELECT id,role,content FROM messages "
            "WHERE user_id=$1 AND conversation_id=$2 "
            "AND ($3::bigint IS NULL OR id < $3) "
            "AND role IN ('user','assistant') "
            "ORDER BY id DESC LIMIT $4",
            user_id, conversation_id, before_id, window,
        )
        return select_continuation_turns(
            list(reversed(rows)), max_chars=max_chars, max_turns=n
        )
    if is_first_topic_return(question):
        # Explicit first-topic requests need the true start, even beyond 80 rows.
        # Fetch IDs solely for chronological deduplication; never expose them.
        query = (
            "SELECT id,role,content FROM messages "
            "WHERE user_id=$1 AND conversation_id=$2 "
            "AND ($3::bigint IS NULL OR id < $3) AND role IN ('user','assistant') "
            "ORDER BY id "
        )
        first = await pool.fetch(query + "ASC LIMIT $4", user_id, conversation_id, before_id, 4)
        latest = await pool.fetch(query + "DESC LIMIT $4", user_id, conversation_id, before_id, n)
        cap = max(0, min(int(max_chars), 7200))
        start_count = min(4, max(1, n // 3))
        start = prepare_turns(first[:start_count], max_chars=cap // 3, max_turns=start_count)
        first_ids = {row.get("id") for row in first[:start_count] if row.get("id") is not None}
        tail = [row for row in reversed(latest) if row.get("id") not in first_ids]
        return start + prepare_turns(tail, max_chars=cap - sum(len(t["content"]) for t in start),
                                     max_turns=n - len(start))
    if is_thread_recap_request(question):
        # Ordinary chats use one bounded fetch. For long conversations the
        # most recent 80 rows are NOT a representative whole-chat recap.
        window = max(n, min(int(lookback), 80))
        scope = (
            "WHERE user_id=$1 AND conversation_id=$2 "
            "AND ($3::bigint IS NULL OR id < $3) "
            "AND role IN ('user','assistant') "
        )
        rows = await pool.fetch(
            "SELECT id,role,content FROM messages " + scope
            + "ORDER BY id DESC LIMIT $4",
            user_id, conversation_id, before_id, window,
        )
        if len(rows) < window or n < 4 or max_chars <= 0:
            return select_recap_turns(
                list(reversed(rows)), max_chars=max_chars, max_turns=n,
            )
        total = await pool.fetchval(
            "SELECT COUNT(*) FROM messages " + scope,
            user_id, conversation_id, before_id,
        )
        if total <= window:
            return select_recap_turns(
                list(reversed(rows)), max_chars=max_chars, max_turns=n,
            )

        # Retrieve actual beginning/midpoint/end, not the start and midpoint
        # of the latest 80 messages. All three slices are owner/thread scoped.
        start_count = max(1, n // 4)
        middle_count = max(1, n // 6) if n >= 6 else 0
        recent_count = n - start_count - middle_count
        beginning = await pool.fetch(
            "SELECT id,role,content FROM messages " + scope
            + "ORDER BY id ASC LIMIT $4",
            user_id, conversation_id, before_id, start_count,
        )
        middle = []
        if middle_count:
            offset = max(start_count, (int(total) - middle_count) // 2)
            middle = await pool.fetch(
                "SELECT id,role,content FROM messages " + scope
                + "ORDER BY id ASC LIMIT $4 OFFSET $5",
                user_id, conversation_id, before_id, middle_count, offset,
            )
        tail = list(reversed(rows[:recent_count]))
        cap = max(0, min(int(max_chars), 7200))
        first_turns = prepare_turns(
            beginning, max_chars=cap // 4, max_turns=start_count,
        )
        mid_turns = prepare_turns(
            middle, max_chars=cap // 5, max_turns=middle_count,
        ) if middle_count else []
        used = sum(len(t["content"]) for t in first_turns + mid_turns)
        last_turns = prepare_turns(
            tail, max_chars=cap - used, max_turns=recent_count,
        )
        return first_turns + mid_turns + last_turns
    terms = _topic_terms(question)
    if not terms:
        return await load_thread_turns(
            pool, user_id, conversation_id, before_id=before_id,
            max_chars=max_chars, limit=n,
        )
    lookback = max(n, min(int(lookback), 80))
    rows = await pool.fetch(
        "SELECT id,role,content FROM messages "
        "WHERE user_id=$1 AND conversation_id=$2 "
        "AND ($3::bigint IS NULL OR id < $3) AND role IN ('user','assistant') "
        "ORDER BY id DESC LIMIT $4",
        user_id, conversation_id, before_id, lookback,
    )
    selected = list(reversed(rows))
    # An incidental mention in recent chat is NOT evidence that we retained
    # the owner's original question and its answer. Explicit named historical
    # recall may inspect earlier same-thread messages even if every query term
    # also appears in the most recent 80 turns. Ordinary chat never does.
    if (is_named_recall_request(question) and len(rows) == lookback
            and max_chars > 0 and n >= 4):
        earliest = rows[-1].get("id")
        if isinstance(earliest, int) and earliest > 0:
            # Bounded, parameterized lexical candidates; never interpolate
            # message text into SQL or search another account/conversation.
            patterns = ["%" + term + "%" for term in
                        sorted(terms, key=lambda t: (-len(t), t))[:4]]
            # A recent-only keyword sample misses the real original exchange
            # when the same topic was mentioned dozens of times in old chat.
            # Sample both chronological ends of the *older* segment. Only an
            # explicit recall request adds these two bounded SQL lookups.
            search_sql = (
                "SELECT id,role,content FROM messages "
                "WHERE user_id=$1 AND conversation_id=$2 "
                "AND ($3::bigint IS NULL OR id < $3) "
                "AND id < $4 AND role IN ('user','assistant') "
                "AND content ILIKE ANY($5::text[]) "
            )
            args = (user_id, conversation_id, before_id, earliest, patterns, 16)
            newer_candidates = await pool.fetch(
                search_sql + "ORDER BY id DESC LIMIT $6", *args,
            )
            older_candidates = await pool.fetch(
                search_sql + "ORDER BY id ASC LIMIT $6", *args,
            )

            def best_match(candidates, *, prefer_oldest):
                valid = [
                    row for row in candidates
                    if row.get("role") in ("user", "assistant")
                    and isinstance(row.get("content"), str)
                    and isinstance(row.get("id"), int)
                ]
                if not valid:
                    return None
                ranked = sorted(
                    valid,
                    key=lambda row: (
                        len(terms & _topic_terms(row["content"])),
                        row["role"] == "user",
                        -row["id"] if prefer_oldest else row["id"],
                    ),
                    reverse=True,
                )
                return ranked[0] if (terms & _topic_terms(ranked[0]["content"])) else None

            oldest_match = best_match(older_candidates, prefer_oldest=True)
            newest_match = best_match(newer_candidates, prefer_oldest=False)
            matches = []
            for match in (oldest_match, newest_match):
                if match is not None and not any(
                    item["id"] == match["id"] for item in matches
                ):
                    matches.append(match)
            evidence = {row["id"]: row for row in matches}
            original_exchange_end = None
            for match in matches:
                after_user = match["role"] == "user"
                nearby = await pool.fetch(
                    "SELECT id,role,content FROM messages "
                    "WHERE user_id=$1 AND conversation_id=$2 "
                    "AND ($3::bigint IS NULL OR id < $3) "
                    "AND id < $4 AND role IN ('user','assistant') "
                    "AND id " + (">" if after_user else "<") + " $5 "
                    "ORDER BY id " + ("ASC" if after_user else "DESC")
                    + " LIMIT 1",
                    user_id, conversation_id, before_id, earliest, match["id"],
                )
                if nearby and nearby[0]["role"] == (
                    "assistant" if after_user else "user"
                ):
                    partner = nearby[0]
                    evidence[partner["id"]] = partner
                    # The earliest question/answer is often immediately
                    # followed by a user correction without repeating the
                    # topic's name. A keyword-only search misses that change.
                    if (match is oldest_match and isinstance(partner["id"], int)
                            and partner["role"] == "assistant"):
                        original_exchange_end = partner["id"]
                    elif (match is oldest_match and match["role"] == "assistant"):
                        original_exchange_end = match["id"]

            if original_exchange_end is not None and n >= 5:
                # Only the immediately following same-thread message may
                # qualify; never scan for an unrelated later correction.
                following = await pool.fetch(
                    "SELECT id,role,content FROM messages "
                    "WHERE user_id=$1 AND conversation_id=$2 "
                    "AND ($3::bigint IS NULL OR id < $3) "
                    "AND id < $4 AND role IN ('user','assistant') "
                    "AND id > $5 ORDER BY id ASC LIMIT 1",
                    user_id, conversation_id, before_id,
                    earliest, original_exchange_end,
                )
                if (following and following[0]["role"] == "user"
                        and is_explicit_turn_correction(following[0]["content"])):
                    evidence[following[0]["id"]] = following[0]
            if evidence:
                # Reserve the same total character budget for earlier Q&A.
                # A fifth slot is allowed only when evidence includes an
                # explicit follow-up correction, so a newer pair can coexist.
                cap = max(0, min(int(max_chars), 7200))
                max_old = min(5 if original_exchange_end is not None else 4, n - 2)
                old_rows = [evidence[key] for key in sorted(evidence)][:max_old]
                old_budget = cap // 4
                per_turn = min(1000, old_budget // len(old_rows))
                old_excerpts = [
                    {"role": row["role"],
                     "content": _bounded_excerpt(row["content"].strip(), per_turn)}
                    for row in old_rows
                ]
                old_turns = prepare_turns(
                    old_excerpts, max_chars=old_budget, max_turns=max_old,
                )
                if old_turns:
                    remaining = cap - sum(len(t["content"]) for t in old_turns)
                    new_turns = select_contextual_turns(
                        selected, question, max_chars=remaining,
                        max_turns=n - len(old_turns),
                    )
                    return old_turns + new_turns
    return select_contextual_turns(
        selected, question,
        max_chars=max_chars, max_turns=n,
    )
