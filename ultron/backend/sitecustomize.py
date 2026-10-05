"""Optional ULTRON Cloud desktop integration.

Python imports ``sitecustomize`` automatically at startup when this directory is
on sys.path (which it is for ``python server.py``). The patch is intentionally
additive and disabled unless ULTRON_CLOUD_URL + ULTRON_DEVICE_TOKEN are set.

Why this lives here instead of replacing the large desktop backend:
- local tools, voice, vision and Ollama remain untouched;
- only GENERAL_CONVERSATION fallback is redirected to ULTRON Cloud;
- if cloud is unavailable, the original local Ollama fallback still runs;
- explicit "remember / hatırla / not et" notes are mirrored to shared memory.
"""
from __future__ import annotations

import time

try:
    from agent import Agent
    from cloud_client import CloudClient
except Exception:
    Agent = None  # type: ignore[assignment]


if Agent is not None and not getattr(Agent, "_ultron_cloud_patch", False):
    _original_init = Agent.__init__
    _original_setattr = Agent.__setattr__
    _original_run = Agent.run

    def _patched_init(self, *args, **kwargs):
        _original_init(self, *args, **kwargs)
        _original_setattr(self, "cloud", CloudClient())

    def _patched_setattr(self, name, value):
        # server.on_startup assigns bridge.run to agent.fallback. Wrap that
        # assignment once so ordinary conversation goes to the shared cloud,
        # while all deterministic/local commands continue through Agent.run.
        if name == "fallback" and callable(value) and not getattr(value, "_ultron_cloud_wrapped", False):
            original_fallback = value

            async def cloud_first_fallback(text: str, approved: bool = False):
                cloud = getattr(self, "cloud", None)
                if cloud is not None and cloud.enabled:
                    try:
                        await self.set_state("THINKING", "ULTRON Cloud ile düşünüyor…")
                        data = await cloud.chat(text)
                        reply = str(data.get("reply", "")).strip()
                        if reply:
                            self.memory.add_session("assistant", reply)
                            await self.set_state("DONE", reply)
                            await self.on_activity("Shared Cloud response received", "success")
                            await self._schedule_idle()
                            return
                    except Exception as exc:
                        await self.on_activity(f"Cloud unavailable, local fallback: {str(exc)[:120]}", "warn")
                return await original_fallback(text, approved)

            cloud_first_fallback._ultron_cloud_wrapped = True  # type: ignore[attr-defined]
            cloud_first_fallback._ultron_local_fallback = original_fallback  # type: ignore[attr-defined]
            value = cloud_first_fallback
        _original_setattr(self, name, value)

    async def _patched_run(self, text: str, approved: bool = False):
        # Let the original state machine preserve all security gates and tools.
        result = await _original_run(self, text, approved)

        # Mirror explicit persistent-memory commands after the local write
        # succeeds. A cloud failure never breaks the local command.
        try:
            intent = self.parse_intent(text)
            cloud = getattr(self, "cloud", None)
            if (
                cloud is not None
                and cloud.enabled
                and isinstance(intent, dict)
                and intent.get("kind") == "remember"
                and isinstance(result, dict)
                and result.get("ok")
            ):
                note = str(intent.get("arg", "")).strip()
                if note:
                    key = f"desktop_note_{int(time.time() * 1000)}"
                    await cloud.upsert_memory(key, note, "NOTE")
                    await self.on_activity("Persistent note mirrored to shared Cloud memory", "success")
        except Exception as exc:
            try:
                await self.on_activity(f"Cloud memory mirror skipped: {str(exc)[:120]}", "warn")
            except Exception:
                pass
        return result

    Agent.__init__ = _patched_init
    Agent.__setattr__ = _patched_setattr
    Agent.run = _patched_run
    Agent._ultron_cloud_patch = True
