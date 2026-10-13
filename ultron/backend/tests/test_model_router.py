"""PHASE 2: model capability registry + router rules (no network needed)."""
from app.core.model_router import ModelRouter, TaskType, fit_messages


class FakeBrain:
    def __init__(self, model="qwen2.5-coder:7b", fail_models=()):
        self.model = model
        self.base_url = "http://127.0.0.1:11434"
        self.fail_models = set(fail_models)
        self.calls = []

    def chat(self, messages, tools=None, model=None):
        m = model or self.model
        self.calls.append(m)
        if m in self.fail_models:
            raise RuntimeError("Ollama API'ye bağlanılamadı")
        return {"message": {"content": "ok"}}

    def ask(self, prompt, system="", model=None):
        m = model or self.model
        self.calls.append(m)
        if m in self.fail_models:
            raise RuntimeError("model down")
        return '{"summary": "s", "files": []}'


def make_router(models, primary="qwen2.5-coder:7b", settings=None, **kw):
    brain = FakeBrain(primary, **kw)
    return ModelRouter(brain, settings or {}, lambda: models)


def test_router_never_switches_when_primary_matches():
    r = make_router(["qwen2.5-coder:7b", "llama3.1:8b"])
    assert r.resolve(TaskType.CODING) == "qwen2.5-coder:7b"


def test_router_never_switches_with_single_model():
    r = make_router(["llama3.1:8b"], primary="llama3.1:8b")
    for t in (TaskType.GENERAL, TaskType.CODING, TaskType.VISION, TaskType.FAST):
        assert r.resolve(t) == "llama3.1:8b"


def test_router_picks_vision_model_for_vision():
    r = make_router(["qwen2.5-coder:7b", "llava:7b"])
    assert r.resolve(TaskType.VISION) == "llava:7b"


def test_router_picks_coding_model_for_coding():
    r = make_router(["llama3.1:8b", "qwen2.5-coder:7b"], primary="llama3.1:8b")
    assert r.resolve(TaskType.CODING) == "qwen2.5-coder:7b"


def test_router_picks_small_model_for_fast():
    r = make_router(["qwen2.5-coder:7b", "llama3.2:3b"], primary="qwen2.5-coder:7b")
    assert r.resolve(TaskType.FAST) == "llama3.2:3b"


def test_router_falls_back_to_primary_when_no_capability_match():
    r = make_router(["mistral:7b"], primary="mistral:7b")
    assert r.resolve(TaskType.VISION) == "mistral:7b"


def test_router_settings_override_honored_only_if_installed():
    st = {"llm": {"routing": {"vision": "llava:13b"}}}
    r = make_router(["llava:7b"], settings=st)
    assert r.resolve(TaskType.VISION) == "llava:7b"
    st2 = {"llm": {"routing": {"vision": "llava:7b"}}}
    r2 = make_router(["llava:7b", "x:1b"], settings=st2)
    assert r2.resolve(TaskType.VISION) == "llava:7b"


def test_router_chat_retries_with_fallback_model():
    r = make_router(["qwen2.5-coder:7b", "llama3.1:8b"], primary="qwen2.5-coder:7b",
                    fail_models={"qwen2.5-coder:7b"})
    res = r.chat(TaskType.GENERAL, [{"role": "user", "content": "hi"}])
    assert res["message"]["content"] == "ok"
    assert r.brain.calls == ["qwen2.5-coder:7b", "llama3.1:8b"]
    h = r.health()
    assert h["qwen2.5-coder:7b"]["failures"] >= 1
    assert h["llama3.1:8b"]["ok"] is True


def test_router_chat_raises_when_all_models_fail():
    r = make_router(["a:1b"], primary="a:1b", fail_models={"a:1b"})
    try:
        r.chat(TaskType.GENERAL, [{"role": "user", "content": "x"}])
        raise AssertionError("must raise")
    except RuntimeError:
        pass


def test_router_health_never_exposes_provider_exception_text():
    class LeakyBrain(FakeBrain):
        def chat(self, messages, tools=None, model=None):
            raise RuntimeError("api_key=private-provider-key user prompt fragment")

    brain = LeakyBrain("a:1b")
    r = ModelRouter(brain, {}, lambda: ["a:1b"])
    try:
        r.chat(TaskType.GENERAL, [{"role": "user", "content": "hi"}])
        raise AssertionError("must raise")
    except RuntimeError:
        pass

    health = r.health()["a:1b"]
    assert health["last_error"] == "provider_request_failed"
    assert "private-provider-key" not in str(health)
    assert "user prompt fragment" not in str(health)


def test_safe_provider_error_classifies_transient_causes_without_echoing_text():
    from app.core.model_router import safe_provider_error
    import urllib.error

    wrapped_timeout = RuntimeError("sensitive request details")
    wrapped_timeout.__cause__ = TimeoutError("credential=private")
    assert safe_provider_error(wrapped_timeout) == "provider_temporarily_unavailable"
    assert safe_provider_error(RuntimeError("api_key=private")) == "provider_request_failed"
    assert safe_provider_error(urllib.error.HTTPError("https://host", 503, "private", {}, None)) == \
        "provider_temporarily_unavailable"
    assert safe_provider_error(urllib.error.HTTPError("https://host", 404, "private", {}, None)) == \
        "provider_request_failed"


def test_merged_local_model_failure_does_not_echo_provider_details(monkeypatch):
    import asyncio
    import base64
    import io
    from types import SimpleNamespace
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer
    from PIL import Image
    from merged_api import install

    monkeypatch.setenv("MARK_ULTRON_TOKEN", "")
    monkeypatch.setenv("ULTRON_CLOUD_URL", "")
    monkeypatch.setenv("ULTRON_DEVICE_TOKEN", "")

    class LeakyBrain(FakeBrain):
        def ask(self, prompt, system="", model=None):
            raise RuntimeError("api_key=private-provider-key prompt=private-user-text")

    class LeakyVision:
        def analyze(self, *_args, **_kwargs):
            raise RuntimeError("api_key=private-vision-key image=private-user-image")

    async def run():
        runtime = SimpleNamespace(brain=LeakyBrain("a:1b"), settings={"llm": {}},
                                  vision_llm=LeakyVision())
        hub = SimpleNamespace(
            bridge=SimpleNamespace(runtime=runtime, available=True),
            ai_status={},
            agent=SimpleNamespace(state="IDLE"),
            async_check=None,
        )

        async def check_ollama():
            return {"status": {"models": ["a:1b"]}}

        async def broadcast(_event):
            return None

        hub.check_ollama = check_ollama
        hub.broadcast = broadcast
        app = web.Application()
        install(app, hub)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.post("/api/merged/invoke", json={"text": "ping", "mode": "coding"})
            payload = await response.json()
            assert response.status == 503
            assert payload["error_code"] == "provider_request_failed"
            assert "private-provider-key" not in str(payload)
            assert "private-user-text" not in str(payload)

            image = Image.new("RGB", (2, 2), color="red")
            image_buffer = io.BytesIO()
            image.save(image_buffer, format="PNG")
            response = await client.post("/api/merged/image", json={
                "data": base64.b64encode(image_buffer.getvalue()).decode("ascii"),
                "mode": "analyze",
            })
            payload = await response.json()
            assert response.status == 502
            assert payload["error_code"] == "provider_request_failed"
            assert "private-vision-key" not in str(payload)
            assert "private-user-image" not in str(payload)
        finally:
            await client.close()

    asyncio.run(run())


def test_router_ask_json_extracts_object():
    r = make_router(["a:1b"], primary="a:1b")
    out = r.ask_json(TaskType.GENERAL, "plan", system="s")
    assert out == {"summary": "s", "files": []}


def test_router_offline_models_empty_uses_primary():
    r = make_router([])
    assert r.resolve(TaskType.VISION) == "qwen2.5-coder:7b"


def test_fit_messages_keeps_system_and_recent():
    msgs = [{"role": "system", "content": "S"}] + [
        {"role": "user", "content": f"message number {i} " + "x" * 50} for i in range(50)
    ]
    out = fit_messages(msgs, max_chars=800)
    assert out[0]["role"] == "system"
    assert len(out) < len(msgs)
    assert out[-1]["content"].startswith("message number 49")


def test_health_report_structure():
    r = make_router(["a:1b"], primary="a:1b")
    r.chat(TaskType.GENERAL, [{"role": "user", "content": "hi"}])
    h = r.health()
    assert set(h["a:1b"]) >= {"ok", "calls", "failures"}


def test_router_local_race_finalizes_tool_free_answer(monkeypatch):
    settings = {"llm": {"local_multi_model": {"enabled": True, "models": ["a:1b", "b:1b"], "judge_model": "a:1b"}}}
    r = make_router(["a:1b"], primary="a:1b", settings=settings)
    calls = []
    monkeypatch.setattr(r, "race_local_and_judge", lambda **kwargs: (
        type("R", (), {"ok": True, "content": "judged"})(), []))
    out = r.chat(TaskType.GENERAL, [{"role": "user", "content": "hi"}], tools=[{"type": "function"}])
    assert out["message"]["content"] == "judged"


# ---------------- PHASE 3: backoff + qwen ailesi yönlendirme ----------------
def test_router_retry_backoff_before_fallback():
    import app.core.model_router as mr
    sleeps = []
    class FlakyBrain:
        model = "qwen3:8b"
        def __init__(self): self.calls = []
        def ask(self, prompt, system="", model=None):
            self.calls.append(model)
            if len(self.calls) == 1:
                raise RuntimeError("boom")
            return "ok"
    b = FlakyBrain()
    r = mr.ModelRouter(b, {}, get_models=lambda: ["qwen3:8b", "qwen2.5-coder:7b"],
                       sleep=sleeps.append)
    out = r.ask(mr.TaskType.GENERAL, "ping")
    assert out == "ok" and len(b.calls) == 2
    assert sleeps == [0.5]


def test_router_qwen_family_capabilities():
    import app.core.model_router as mr
    class B:
        model = "qwen2.5-coder:7b"
    r = mr.ModelRouter(B(), {}, get_models=lambda: ["qwen2.5-coder:7b", "llava:7b",
                                                    "qwen3:4b", "qwen3:8b"])
    assert r.resolve(mr.TaskType.VISION) == "llava:7b"
    assert r.resolve(mr.TaskType.FAST) == "qwen3:4b"
    assert r.resolve(mr.TaskType.CODING) == "qwen2.5-coder:7b"
    assert r.resolve(mr.TaskType.GENERAL) == "qwen2.5-coder:7b"


def test_fit_messages_context_limit():
    from app.core.model_router import fit_messages
    msgs = [{"role": "system", "content": "SYS"},
            {"role": "user", "content": "x" * 500},
            {"role": "assistant", "content": "y" * 500},
            {"role": "user", "content": "z" * 100}]
    out = fit_messages(msgs, max_chars=700)
    assert out[0]["role"] == "system"
    assert out[-1]["content"].startswith("z")
    assert sum(len(m["content"]) for m in out) <= 700 or len(out) == 2
