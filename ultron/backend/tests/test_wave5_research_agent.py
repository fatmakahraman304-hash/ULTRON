"""Local agent research routing uses page evidence in one model pass."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.agent.agent import Agent  # noqa: E402


class _Memory:
    def __init__(self):
        self.rows = []

    def add(self, kind, value):
        self.rows.append((kind, value, 0))

    def recent(self, limit):
        return self.rows[-limit:]


class _Audit:
    def write(self, *args):
        pass


class _Registry:
    def ollama_tools(self, **kwargs):
        return []


class _Brain:
    def __init__(self):
        self.calls = []

    def chat(self, messages, tools=None):
        self.calls.append((messages, tools))
        return {"message": {"role": "assistant", "content": "Ölçülen kapasite 42 kWh."}}


class _Research:
    def __init__(self):
        self.calls = []

    def research(self, query, *, max_sources, store):
        self.calls.append((query, max_sources, store))
        return {"ok": True, "status": "sources_read", "evidence_level": "source_pages_read",
                "citations": ["https://public.example/battery"],
                "synthesis": {"findings": [{"title": "Battery measurements",
                    "url": "https://public.example/battery",
                    "accessed_at": "2026-10-14T00:00:00Z",
                    "excerpt": "The measured capacity is 42 kWh.",
                    "basis": "source_page_excerpt", "page_read": True}]}}


def _agent():
    brain, research, memory = _Brain(), _Research(), _Memory()
    agent = Agent(brain, None, memory, _Registry(), {}, _Audit(), None,
                  research_engine=research)
    return agent, brain, research


def test_local_research_route_reads_pages_and_uses_one_model_call():
    agent, brain, research = _agent()
    answer = agent.handle("GÖLGE, webde pil kapasitesi hakkında kaynakları araştır")
    assert research.calls == [("pil kapasitesi hakkında kaynakları", 3, False)]
    assert len(brain.calls) == 1
    messages, tools = brain.calls[0]
    assert tools is None
    assert "UNTRUSTED_RESEARCH_JSON" in messages[0]["content"]
    assert "42 kWh" in messages[0]["content"]
    assert "https://public.example/battery" in answer


def test_ordinary_local_chat_does_not_start_research():
    agent, brain, research = _agent()
    answer = agent.handle("Selam, nasılsın?")
    assert research.calls == []
    assert len(brain.calls) == 1
    assert "RESEARCH EVIDENCE POLICY" not in brain.calls[0][0][0]["content"]
    assert "Araştırma notu:" not in answer


def test_private_tail_never_reaches_web_or_a_hallucinated_model_answer():
    agent, brain, research = _agent()
    answer = agent.handle("Araştır: " + "public " * 180 + "my password is private-fixture")
    assert research.calls == []
    assert brain.calls == []
    assert "özel bilgi" in answer


def test_offline_research_never_invents_current_price():
    agent, brain, research = _agent()
    research.research = lambda *args, **kwargs: {"ok": False, "status": "search_unavailable"}
    answer = agent.handle("Bugün dolar kaç TL?")
    assert brain.calls == []
    assert "doğrulayamıyorum" in answer
