"""Connect explicit Cloud research intent to the shared source reader."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from ultron.backend.app.cognitive.research_engine import ResearchEngine  # noqa: E402
from ultron.backend.app.cognitive.research_context import (  # noqa: E402
    append_research_sources, build_research_prompt_block, extract_research_query, safe_public_query,
    research_message_for_turn, is_research_followup,
)


async def research_for_chat(message: str, *, engine_factory=None, allow_grounding=True) -> dict | None:
    """One explicit research request runs search + page reading, no memory export."""
    if research_message_for_turn(message) is None:
        if is_research_followup(message):
            return {"ok": False, "status": "research_topic_missing", "citations": [],
                    "synthesis": {"findings": []}}
        return None
    query = extract_research_query(message)
    if not safe_public_query(message):
        return {"ok": False, "status": "research_blocked_sensitive_input",
                "query": "", "evidence_level": "none", "confidence": 0.0,
                "citations": [], "synthesis": {"findings": [], "unread_sources": []}}
    engine = (engine_factory or (lambda: ResearchEngine(db_path=":memory:", allow_grounding=allow_grounding)))()
    def read():
        try:
            return engine.research(query, max_sources=5, store=False)
        finally:
            close = getattr(engine, "close", None)
            if callable(close):
                try: close()
                except Exception: pass
    try:
        return await asyncio.to_thread(read)
    except Exception:
        return {"ok": False, "status": "research_unavailable",
                "query": "", "evidence_level": "none", "confidence": 0.0,
                "citations": [], "synthesis": {"findings": [], "unread_sources": []}}



__all__ = ["research_for_chat", "append_research_sources",
           "build_research_prompt_block", "extract_research_query", "research_message_for_turn"]
