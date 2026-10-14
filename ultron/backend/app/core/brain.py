import json
import urllib.request
import urllib.error
import asyncio
import contextlib
import aiohttp
from app.core.fast_brain import FastBrainPolicy
from app.core.request_cancellation import ProviderRequestCancelled

class Brain:
    """Local Ollama chat adapter with native tool-calling support."""
    def __init__(self, settings):
        cfg = settings["llm"]
        self.provider = cfg.get("provider", "ollama")
        self.model = cfg.get("model", "qwen2.5-coder:7b")
        self.base_url = cfg.get("base_url", "http://127.0.0.1:11434")
        self.timeout = int(cfg.get("timeout_seconds", 180))
        self.fast_policy = FastBrainPolicy(cfg.get("fast_brain", {}))
        from app.security import sovereign_privacy as sov
        sov.configure(settings)
        if bool(settings.get("sovereign_mode", False)) and not sov.is_local(self.base_url):
            raise ValueError(f"Sovereign mode aktif: uzak LLM endpoint'i reddedildi: {self.base_url}")
        # diagnostics (V17.1 debug): last wire-level facts, read by /api/debug/*
        self.last_http_status = None
        self.last_response_model = None
        self.last_error = None

    def _post(self, endpoint, payload):
        from app.security import sovereign_privacy as sov
        sov.assert_local(self.base_url)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.base_url.rstrip("/") + endpoint,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                self.last_http_status = getattr(r, "status", None)
                parsed = json.loads(r.read().decode("utf-8"))
            self.last_response_model = parsed.get("model") if isinstance(parsed, dict) else None
            self.last_error = None
            return parsed
        except urllib.error.URLError as e:
            self.last_http_status = None
            self.last_error = str(e)
            raise RuntimeError(
                "Ollama API'ye bağlanılamadı. Ollama'nın çalıştığından ve modelin kurulu olduğundan emin ol."
            ) from e

    def ask(self, prompt: str, system: str = "", history=None, model=None) -> str:
        messages = [{"role": "system", "content": system}] if system else []
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        selected = model or self.model
        payload = {"model": selected, "messages": messages, "stream": False}
        if self.fast_policy.enabled:
            payload.update(self.fast_policy.runtime_options(selected))
        data = self._post("/api/chat", payload)
        return data.get("message", {}).get("content", "").strip()

    async def ask_cancellable(self, prompt: str, system: str = "", history=None,
                              model=None, *, cancel_event: asyncio.Event) -> str:
        """Stream Ollama NDJSON and close the HTTP request when this turn stops.

        Ollama's chat handler derives its generation context from the HTTP
        request context. Closing this streaming response therefore propagates
        cancellation to the runner; cancelling a Python worker thread does not.
        This method intentionally returns no partial answer on interruption.
        """
        from app.security import sovereign_privacy as sov
        sov.assert_local(self.base_url)
        if cancel_event.is_set():
            raise ProviderRequestCancelled("request cancelled before provider start",
                                           provider_stopped=False)
        messages = [{"role": "system", "content": system}] if system else []
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        selected = model or self.model
        payload = {"model": selected, "messages": messages, "stream": True}
        if self.fast_policy.enabled:
            payload.update(self.fast_policy.runtime_options(selected))

        timeout = aiohttp.ClientTimeout(total=max(1, self.timeout))
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.base_url.rstrip("/") + "/api/chat", json=payload) as response:
                self.last_http_status = response.status
                response.raise_for_status()
                pieces: list[str] = []
                cancel_wait = asyncio.create_task(cancel_event.wait())
                read_line = asyncio.create_task(response.content.readline())
                try:
                    while True:
                        done, _ = await asyncio.wait(
                            (read_line, cancel_wait), return_when=asyncio.FIRST_COMPLETED)
                        if cancel_wait in done and cancel_event.is_set():
                            # Closing the response tears down the Ollama HTTP
                            # request; the API handler binds generation to it.
                            response.close()
                            read_line.cancel()
                            with contextlib.suppress(asyncio.CancelledError, Exception):
                                await read_line
                            raise ProviderRequestCancelled("Ollama stream closed on interruption",
                                                           provider_stopped=True)
                        raw = read_line.result()
                        if not raw:
                            break
                        try:
                            chunk = json.loads(raw)
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue
                        if isinstance(chunk, dict) and chunk.get("error"):
                            raise RuntimeError("Ollama streaming request failed")
                        message = chunk.get("message", {}) if isinstance(chunk, dict) else {}
                        content = message.get("content", "") if isinstance(message, dict) else ""
                        if isinstance(content, str) and content:
                            pieces.append(content)
                        if isinstance(chunk, dict) and chunk.get("done"):
                            self.last_response_model = chunk.get("model") or selected
                            break
                        read_line = asyncio.create_task(response.content.readline())
                finally:
                    cancel_wait.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await cancel_wait
                if cancel_event.is_set():
                    raise ProviderRequestCancelled("Ollama stream ended after interruption",
                                                   provider_stopped=False)
                answer = "".join(pieces).strip()
                if not answer:
                    raise RuntimeError("Ollama returned an empty streamed reply")
                self.last_error = None
                return answer

    def chat(self, messages, tools=None, model=None):
        selected = model or self.model
        payload = {"model": selected, "messages": messages, "stream": False}
        if self.fast_policy.enabled:
            payload.update(self.fast_policy.runtime_options(selected, tools=bool(tools)))
        if tools:
            payload["tools"] = tools
        return self._post("/api/chat", payload)
