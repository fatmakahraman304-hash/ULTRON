"""Fast model routing and natural conversational behavior, offline regression tests."""
from app.agent.agent import Agent
from app.agent.hybrid_integration import _looks_like_work
from app.agent.persona_guard import PersonaGuard
from app.core.model_router import ModelRouter, TaskType


class FakeBrain:
    model = "qwen3:8b"

    def __init__(self):
        self.calls = []

    def chat(self, messages, tools=None, model=None):
        self.calls.append(("chat", model))
        return {"message": {"role": "assistant", "content": "Buradayım."}}

    def ask(self, prompt, system="", model=None):
        self.calls.append(("ask", model))
        return "Yanıt."


def _router(settings):
    brain = FakeBrain()
    return ModelRouter(brain, settings, lambda: ["qwen3:8b", "qwen3:4b", "llava:7b"], sleep=lambda _: None)


def test_chat_fast_mode_skips_second_multi_model_inference(monkeypatch):
    r = _router({"llm": {"local_multi_model": {"enabled": True, "chat_strategy": "fast"}}})
    monkeypatch.setattr(r, "race_local_and_judge", lambda **kw: (_ for _ in ()).throw(AssertionError("race should not run")))
    result = r.chat(TaskType.GENERAL, [{"role": "user", "content": "merhaba"}])
    assert result["message"]["content"] == "Buradayım."
    assert r.brain.calls == [("chat", "qwen3:8b")]


def test_chat_optional_race_failure_keeps_successful_answer(monkeypatch):
    r = _router({"llm": {"local_multi_model": {"enabled": True, "chat_strategy": "race"}}})
    monkeypatch.setattr(r, "race_local_and_judge", lambda **kw: (_ for _ in ()).throw(RuntimeError("judge offline")))
    result = r.chat(TaskType.GENERAL, [{"role": "user", "content": "selam"}])
    assert result["message"]["content"] == "Buradayım."
    assert r.brain.calls == [("chat", "qwen3:8b")]


def test_ask_falls_back_if_race_is_unavailable(monkeypatch):
    r = _router({"llm": {"local_multi_model": {"enabled": True, "ask_strategy": "race"}}})
    monkeypatch.setattr(r, "race_local_and_judge", lambda **kw: (_ for _ in ()).throw(RuntimeError("judge offline")))
    assert r.ask(TaskType.GENERAL, "selam") == "Yanıt."
    assert r.brain.calls == [("ask", "qwen3:8b")]


def test_general_fallback_never_chooses_vision_when_text_model_exists():
    r = _router({})
    attempts = r._attempts(TaskType.GENERAL, ["qwen3:8b", "llava:7b", "qwen3:4b"])
    assert attempts == ["qwen3:8b", "qwen3:4b"]


def test_natural_persona_removes_forced_boss_label(tmp_path):
    persona = PersonaGuard(mode="natural", log_path=str(tmp_path / "persona.db"))
    prompt = persona.compose("Sen ULTRON'sun.", 2)
    assert "doğal" in prompt
    assert "Nietzsche" not in prompt
    assert "missing_boss_hitap" not in persona.check("Anladım, şimdi açıklıyorum.")["violations"]
    agent = object.__new__(Agent)
    agent.persona = persona
    assert agent._boss_hitap("Anladım.") == "Anladım."
    assert agent._persona_finalize("Anladım.") == "Anladım."


def test_legacy_persona_retains_explicit_boss_address(tmp_path):
    agent = object.__new__(Agent)
    agent.persona = PersonaGuard(mode="reframe", log_path=str(tmp_path / "persona.db"))
    assert agent._boss_hitap("Tamam.") == "Boss, Tamam."


def test_casual_followup_is_not_executed_as_multistep_plan():
    assert not _looks_like_work("Önce bundan söz etmiştik, sonra ne oldu?")
    assert not _looks_like_work("Önce neden böyle dedin, sonra fikrin mi değişti?")
    assert _looks_like_work("Önce dosyayı bul, sonra içeriğini oku")
