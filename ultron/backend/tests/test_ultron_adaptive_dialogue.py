"""Adaptive local Qwen tiers: no speculative execution, no extra network calls."""
import pytest

from app.agent.agent import Agent
from app.core.dialogue_routing import classify_dialogue
from app.core.model_router import TaskType


@pytest.mark.parametrize("message,task", [
    ("Merhaba!", TaskType.FAST),
    ("ULTRON merhaba", TaskType.FAST),
    ("Teşekkür ederim.", TaskType.FAST),
    ("Nasılsın?", TaskType.FAST),
    ("Bana Python kodu yaz", TaskType.CODING),
    ("React fonksiyonunu geliştir", TaskType.CODING),
    ("GitHub commit kontrolünü yap", TaskType.CODING),
    ("Az önce konuştuğumuz konuyu hatırlıyor musun?", TaskType.GENERAL),
    ("Tamam", TaskType.GENERAL),
    ("Laptopumdaki dosyayı sil", TaskType.GENERAL),
    ("Bütün projenin mimarisini değerlendir", TaskType.GENERAL),
])
def test_conservative_tier_selection(message, task):
    assert classify_dialogue(message) == task


class Memory:
    def __init__(self):
        self.rows = []

    def add(self, kind, content):
        self.rows.append((kind, content, "today"))

    def recent(self, limit=20):
        return list(reversed(self.rows))[:limit]


class Registry:
    def ollama_tools(self, include_dangerous=True):
        return [{"type": "function", "function": {"name": "example_tool"}}]


class Router:
    def __init__(self):
        self.calls = []

    def chat(self, task, messages, tools=None):
        self.calls.append({"task": task, "messages": messages, "tools": tools})
        return {"message": {"content": "Yanıt."}}


class Persona:
    mode = "natural"
    threshold = 0.5

    def compose(self, system, count):
        return system

    def check(self, answer):
        return {"violations": [], "score": 1.0}


class Audit:
    def write(self, *args):
        pass


def make_agent():
    a = object.__new__(Agent)
    a.memory = Memory()
    a.registry = Registry()
    a.router = Router()
    a.persona = Persona()
    a.audit = Audit()
    a.redact_fn = None
    a.adaptive = None
    a.semantic_memory = None
    a.world_fn = None
    a.settings = {}
    a.max_steps = 1
    a._direct = lambda text: None
    a._browser = lambda text: None
    return a


def test_fast_turn_uses_fast_model_tier_without_exposing_tools():
    agent = make_agent()
    assert agent.handle("Merhaba!") == "Yanıt."
    call = agent.router.calls[-1]
    assert call["task"] == TaskType.FAST
    assert call["tools"] == []


def test_coding_turn_selects_coder_and_keeps_tools_available():
    agent = make_agent()
    assert agent.handle("Python kodu yaz") == "Yanıt."
    call = agent.router.calls[-1]
    assert call["task"] == TaskType.CODING
    assert call["tools"] and call["tools"][0]["type"] == "function"


def test_follow_up_does_not_lose_tool_access_or_previous_context():
    agent = make_agent()
    agent.handle("Merhaba!")
    agent.handle("Az önce ne konuşmuştuk?")
    call = agent.router.calls[-1]
    assert call["task"] == TaskType.GENERAL
    assert call["tools"]
    assert [(m["role"], m["content"]) for m in call["messages"][1:]] == [
        ("user", "Merhaba!"), ("assistant", "Yanıt."),
        ("user", "Az önce ne konuşmuştuk?"),
    ]
