"""Connect explicit Cloud research intent to the shared source reader."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from conversation_persona import classify_intent
from live_voice_policy import safe_manual_memory_value

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from ultron.backend.app.cognitive.research_engine import ResearchEngine  # noqa: E402
from ultron.backend.app.cognitive.research_context import (  # noqa: E402
    append_research_sources, build_research_prompt_block, extract_research_query,
)


async def research_for_chat(message: str, *, engine_factory=None) -> dict | None:
    """One explicit research request runs search + page reading, no memory export."""
    if classify_intent(message).kind != "research":
        return None
    query = extract_research_query(message)
    if not safe_manual_memory_value(query):
        return {"ok": False, "status": "research_blocked_sensitive_input",
                "query": "", "evidence_level": "none", "confidence": 0.0,
                "citations": [], "synthesis": {"findings": [], "unread_sources": []}}
    engine = (engine_factory or (lambda: ResearchEngine(db_path=":memory:")))()
    try:
        return await asyncio.to_thread(
            engine.research, query, max_sources=3, store=False
        )
    except Exception:
        return {"ok": False, "status": "research_unavailable",
                "query": "", "evidence_level": "none", "confidence": 0.0,
                "citations": [], "synthesis": {"findings": [], "unread_sources": []}}
    finally:
        close = getattr(engine, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass


__all__ = ["research_for_chat", "append_research_sources",
           "build_research_prompt_block", "extract_research_query"]
