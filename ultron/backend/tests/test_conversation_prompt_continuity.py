"""Conversation prompt regression tests: no duplicated current user turn.

These tests use in-memory fakes. They never contact Ollama/Gemini or a real PC.
"""
from app.agent.agent import Agent


class Memory:
    def __init__(self, suppress_latest=False):
        self.rows = []
        self.suppress_latest = suppress_latest

    def add(self, category, content):
        self.rows.append((category, content, 0))

    def recent(self, limit=20):
        rows = list(reversed(self.rows))[:limit]
        return rows[1:] if self.suppress_latest else rows


class Brain:
    def __init__(self):
        self.calls = []

    def chat(self, messages, tools=None):
        self.calls.append([dict(m) for m in messages])
        return {"message": {"content": "Yanıt alındı."}}


class Registry:
    def ollama_tools(self, include_dangerous=False):
        return []


class Audit:
    def write(self, *args):
        pass


class Persona:
    threshold = 0.5
    mode = "reframe"

    def compose(self, system, history_len):
        return system

    def check(self, answer):
        return {"score": 1.0, "violations": []}


def make_agent(suppress_latest=False):
    agent = object.__new__(Agent)
    agent.memory = Memory(suppress_latest=suppress_latest)
    agent.brain = Brain()
    agent.registry = Registry()
    agent.audit = Audit()
    agent.persona = Persona()
    agent.redact_fn = None
    agent.adaptive = None
    agent.semantic_memory = None
    agent.router = None
    agent.world_fn = None
    agent.max_steps = 1
    agent._direct = lambda text: None
    agent._browser = lambda text: None
    return agent


def test_first_turn_appears_once_in_model_context():
    agent = make_agent()
    assert agent.handle("Merhaba") == "Yanıt alındı."
    sent = agent.brain.calls[-1]
    assert [(m["role"], m["content"]) for m in sent[1:]] == [
        ("user", "Merhaba"),
    ]


def test_follow_up_has_ordered_history_without_duplicate_current_turn():
    agent = make_agent()
    agent.handle("Adım Deniz")
    agent.handle("Az önce ne söyledim?")
    sent = agent.brain.calls[-1]
    assert [(m["role"], m["content"]) for m in sent[1:]] == [
        ("user", "Adım Deniz"),
        ("assistant", "Yanıt alındı."),
        ("user", "Az önce ne söyledim?"),
    ]


def test_unsynchronized_memory_includes_current_turn_once():
    agent = make_agent(suppress_latest=True)
    agent.handle("Bugün hava nasıl?")
    sent = agent.brain.calls[-1]
    assert [m["content"] for m in sent if m["role"] == "user"] == [
        "Bugün hava nasıl?"
    ]
