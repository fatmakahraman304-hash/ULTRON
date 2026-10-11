"""Regression tests for valid HTTP replies with missing Ollama answer text."""
import pytest
from app.core.model_router import ModelRouter, TaskType


class Brain:
    model = "qwen3:8b"

    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = []

    def chat(self, messages, tools=None, model=None):
        self.calls.append(("chat", model))
        result = self.outputs.get(model)
        return result if isinstance(result, dict) else {"message": {"content": result}}

    def ask(self, prompt, system="", model=None):
        self.calls.append(("ask", model))
        return self.outputs[model]


def router(outputs):
    brain = Brain(outputs)
    return ModelRouter(brain, {}, get_models=lambda: ["qwen3:8b", "qwen3:4b"], sleep=lambda _: None)


def test_empty_content_causes_fallback_to_other_local_model():
    r = router({"qwen3:8b": {"message": {"content": "", "thinking": "..." }},
                "qwen3:4b": {"message": {"content": "Gerçek yanıt"}}})
    result = r.chat(TaskType.GENERAL, [{"role": "user", "content": "Merhaba"}])
    assert result["message"]["content"] == "Gerçek yanıt"
    assert r.brain.calls == [("chat", "qwen3:8b"), ("chat", "qwen3:4b")]
    assert r.health()["qwen3:8b"]["failures"] == 1
    assert r.health()["qwen3:4b"]["ok"] is True


def test_empty_content_with_tool_call_is_valid_and_never_retried():
    tool_call = {"function": {"name": "calculate", "arguments": {"text": "2+2"}}}
    r = router({"qwen3:8b": {"message": {"content": "", "tool_calls": [tool_call]}},
                "qwen3:4b": {"message": {"content": "Wrong second call"}}})
    result = r.chat(TaskType.GENERAL, [{"role": "user", "content": "calculate"}], tools=[{"type": "function"}])
    assert result["message"]["tool_calls"] == [tool_call]
    assert r.brain.calls == [("chat", "qwen3:8b")]


def test_empty_ask_retries_next_installed_model():
    r = router({"qwen3:8b": "  ", "qwen3:4b": "Yanıt geldi"})
    assert r.ask(TaskType.GENERAL, "Kısaca açıkla") == "Yanıt geldi"
    assert r.brain.calls == [("ask", "qwen3:8b"), ("ask", "qwen3:4b")]


def test_all_models_empty_reports_failure_instead_of_fake_success():
    r = router({"qwen3:8b": "", "qwen3:4b": ""})
    with pytest.raises(ValueError, match="Empty local model response"):
        r.chat(TaskType.GENERAL, [{"role": "user", "content": "Konu"}])
    assert len(r.brain.calls) == 2
