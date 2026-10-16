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


def test_merged_invoke_routes_explicit_actions_to_agent_and_returns_verified_result(monkeypatch):
    """Natural action wording must bypass chat and show the actual gated agent result."""
    import asyncio
    from types import SimpleNamespace
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer
    import merged_api

    monkeypatch.setenv("MARK_ULTRON_TOKEN", "")

    class FakeCloud:
        enabled = True

        def __init__(self):
            self.calls = []

        async def chat(self, text, **_identity):
            self.calls.append(text)
            return {"reply": "cloud chat path"}

    cloud_instances = []
    def make_cloud():
        instance = FakeCloud()
        cloud_instances.append(instance)
        return instance

    monkeypatch.setattr(merged_api, "CloudClient", make_cloud)

    class Agent:
        def __init__(self):
            self.state = "IDLE"
            self.message = ""
            self.calls = []

        async def run(self, text, approved=False):
            assert approved is False
            self.calls.append((text, approved))
            if text == "Run the tests":
                self.state = "DONE"
                self.message = "Test result: 3 passed, 0 failed."
                return {"ok": True, "result": "test-run-verified"}
            if text == "Edit this project":
                self.state = "DONE"
                self.message = "No matching intent. Try a supported action."
                return {"ok": True, "result": "no-intent"}
            self.state = "WAITING_APPROVAL"
            self.message = "File edit requires approval."
            return {"ok": True, "result": "waiting-approval", "task_id": "approval-42"}

    async def run():
        hub = SimpleNamespace(
            bridge=SimpleNamespace(runtime=object(), available=True),
            agent=Agent(), pending_task=None,
            memory=SimpleNamespace(add_session=lambda *_args: None),
        )

        async def on_activity(*_args):
            return None

        async def broadcast(*_args):
            return None

        hub.on_activity = on_activity
        hub.broadcast = broadcast
        app = web.Application()
        merged_api.install(app, hub)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.post("/api/merged/invoke", json={
                "text": "Run the tests", "mode": "general",
            })
            payload = await response.json()
            assert response.status == 200
            assert payload["state"] == "DONE"
            assert payload["text"] == "Test result: 3 passed, 0 failed."
            assert payload["result"] == {"ok": True, "result": "test-run-verified"}
            assert hub.agent.calls == [("Run the tests", False)]
            assert cloud_instances[0].calls == []

            response = await client.post("/api/merged/invoke", json={
                "text": "What is a test runner?", "mode": "general",
            })
            payload = await response.json()
            assert payload["source"] == "cloud"
            assert payload["text"] == "cloud chat path"
            assert hub.agent.calls == [("Run the tests", False)]
            assert cloud_instances[0].calls == ["What is a test runner?"]

            response = await client.post("/api/merged/invoke", json={
                "text": "Edit this project", "mode": "general",
            })
            payload = await response.json()
            assert payload["intent"] == "computer_task"
            assert payload["completed"] is False
            assert payload["ok"] is False
            assert "No matching intent" in payload["text"]
            assert cloud_instances[0].calls == ["What is a test runner?"]

            response = await client.post("/api/merged/invoke", json={
                "text": "Edit the file", "mode": "general", "approved": True,
            })
            payload = await response.json()
            assert payload["state"] == "WAITING_APPROVAL"
            assert payload["pending_approval"] is True
            assert payload["completed"] is False
            assert "onayı bekliyor" in payload["text"]
            assert hub.agent.calls[-1] == ("Edit the file", False)
        finally:
            await client.close()

    asyncio.run(run())


def test_desktop_agent_does_not_echo_model_or_vision_provider_errors(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from app.agent.agent import Agent

    class Memory:
        def __init__(self):
            self.rows = []
        def add(self, kind, content):
            self.rows.append((kind, content, 0))
        def recent(self, limit):
            return list(reversed(self.rows[-limit:]))

    class Audit:
        def write(self, *_args):
            return None

    class Registry:
        def ollama_tools(self, **_kwargs):
            return []

    class Executor:
        def execute(self, *_args, **_kwargs):
            return []

    class LeakyRouter:
        fast_policy = SimpleNamespace(enabled=False)
        def chat(self, *_args, **_kwargs):
            raise RuntimeError("api_key=private-chat-key prompt=private-user-prompt")

    class LeakyVision:
        def resolve_model(self, _models):
            return "llava:7b"
        def analyze(self, *_args, **_kwargs):
            raise RuntimeError("token=private-vision-token image=private-user-image")

    class Brain:
        model = "qwen3:4b"
        base_url = "http://127.0.0.1:11434"

    memory = Memory()
    agent = Agent(Brain(), Executor(), memory, Registry(), {}, Audit(), None,
                  max_steps=1, router=LeakyRouter(), vision_llm=LeakyVision())

    answer = agent.handle("Bana kısa bir masal anlat.")
    assert "private-chat-key" not in answer
    assert "private-user-prompt" not in answer
    assert "İsteğini tamamlayamadım" in answer

    image_path = tmp_path / "screen.png"
    image_path.write_bytes(b"synthetic image")
    monkeypatch.setattr("app.tools.ollama_tools.ollama_status",
                        lambda *_args: {"models": ["llava:7b"]})
    vision_answer = agent._vision_pipeline(f"Ekranımda ne var? {image_path}")
    assert "private-vision-token" not in vision_answer
    assert "private-user-image" not in vision_answer
    assert "Görsel analizi tamamlanamadı" in vision_answer


def test_vision_debug_does_not_log_analyzed_user_text(monkeypatch, tmp_path, capsys):
    import app.vision.vision_llm as vision_module
    monkeypatch.setattr(vision_module, "DEBUG", True)

    class Brain:
        base_url = "http://127.0.0.1:11434"
        def _post(self, *_args, **_kwargs):
            return {"model": "llava:7b", "message": {"content": "private screenshot contents"}}

    image_path = tmp_path / "screen.png"
    image_path.write_bytes(b"synthetic image")
    vision_module.VisionLLM(Brain(), {"vision": {"enabled": True, "model": "llava:7b"}}).analyze(
        image_path, available_models=["llava:7b"])
    assert "private screenshot contents" not in capsys.readouterr().out


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


def test_local_system_facts_router_matches_real_owner_requests_not_generic_research():
    from merged_api import _requested_local_system_facts, _format_local_system_facts

    request = ("Windows sürümümü, işlemci modelimi, toplam RAM miktarımı, "
               "saat dilimimi ve varsayılan mikrofonumu söyle. "
               "Bilmediğin hiçbir bilgiyi tahmin etme.")
    assert _requested_local_system_facts(request) == (
        "windows", "cpu", "ram", "timezone", "microphone"
    )
    assert _requested_local_system_facts(
        "Bilgisayarımın RAM kapasitesini ve işlemci modelini söyle."
    ) == ("cpu", "ram")
    assert _requested_local_system_facts(
        "Toplam RAM miktarımı söyle"
    ) == ("ram",)
    for generic in (
        "RAM nedir?", "Windows 11 sistem gereksinimleri nedir?",
        "Windows sürümü nasıl öğrenilir?", "İşlemci nasıl çalışır?",
        "Varsayılan mikrofon nasıl seçilir?", "Dünya saat dilimleri kaç tane?",
        "Bilgisayarımın dosyalarını sil.",
    ):
        assert _requested_local_system_facts(generic) == (), generic

    machine = {
        "os_name": "Windows 11 Pro", "os_version": "26100",
        "cpu_model": "Test CPU 123", "ram_total_gb": 23.8,
        "timezone": "Turkey Standard Time", "default_microphone": None,
        "active_windows": ["PRIVATE WINDOW TITLE"],
        "running_processes": ["PRIVATE PROCESS"],
        "network_interface": "PRIVATE NETWORK",
    }
    answer = _format_local_system_facts(machine, _requested_local_system_facts(request))
    assert "Windows 11 Pro (derleme 26100)" in answer
    assert "Test CPU 123" in answer
    assert "23.8 GB" in answer
    assert "Turkey Standard Time" in answer
    assert "Varsayılan mikrofon: Bilgi okunamadı" in answer
    assert "PRIVATE" not in answer


def test_local_system_facts_router_stays_on_desktop_and_respects_modes(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer
    import merged_api
    from actions import system_monitor

    monkeypatch.setenv("MARK_ULTRON_TOKEN", "")
    models = []
    system_calls = []

    def real_local_facts(*, include_details):
        system_calls.append(include_details)
        return {
            "os_name": "Windows 11", "os_version": "26100",
            "cpu_model": "Local Test CPU", "ram_total_gb": 24.0,
            "timezone": "Turkey Standard Time",
            "default_microphone": "Local Test Microphone",
            "active_windows": ["TOP-SECRET WINDOW"],
        }
    monkeypatch.setattr(system_monitor, "get_system_status", real_local_facts)

    class FakeCloud:
        enabled = True
        def __init__(self):
            self.calls = []
            models.append(self)
        async def chat(self, text, **_):
            self.calls.append(text)
            return {"reply": "Cloud answer (cannot see hardware)."}

    monkeypatch.setattr(merged_api, "CloudClient", FakeCloud)

    async def run():
        hub = SimpleNamespace(
            bridge=SimpleNamespace(runtime=object(), available=True),
            agent=SimpleNamespace(state="IDLE"),
            memory=SimpleNamespace(add_session=lambda *_: None),
        )
        async def broadcast(*_):
            pass
        async def on_activity(*_):
            pass
        hub.broadcast = broadcast
        hub.on_activity = on_activity
        app = web.Application()
        merged_api.install(app, hub)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            query = ("Windows sürümümü, işlemci modelimi, toplam RAM miktarımı, "
                     "saat dilimimi ve varsayılan mikrofonumu söyle. "
                     "Bilmediğin hiçbir bilgiyi tahmin etme.")
            response = await client.post("/api/merged/invoke",
                json={"text": query, "mode": "auto"})
            result = await response.json()
            assert response.status == 200
            assert result["source"] == "desktop-local-read-only"
            assert result["request_id"]
            assert "Windows 11" in result["text"]
            assert "24.0 GB" in result["text"]
            assert "Local Test Microphone" in result["text"]
            assert "TOP-SECRET" not in str(result)
            assert system_calls == [True]
            assert models[0].calls == []

            response = await client.post("/api/merged/invoke",
                json={"text": "RAM nedir?", "mode": "general"})
            result = await response.json()
            assert result["source"] == "cloud"
            assert models[0].calls == ["RAM nedir?"]
            assert system_calls == [True]

            def failed_read(*, include_details):
                raise RuntimeError("secret system exception with private details")
            monkeypatch.setattr(system_monitor, "get_system_status", failed_read)
            response = await client.post("/api/merged/invoke", json={
                "text": "Saat dilimimi söyle", "mode": "general",
            })
            result = await response.json()
            assert response.status == 503
            assert result["error_code"] == "local_system_facts_unavailable"
            assert "private details" not in str(result)
            assert models[0].calls == ["RAM nedir?"]
        finally:
            await client.close()

    asyncio.run(run())
