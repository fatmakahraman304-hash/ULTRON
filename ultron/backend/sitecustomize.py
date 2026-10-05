"""Optional ULTRON Cloud desktop integration.

Python imports ``sitecustomize`` automatically at startup when this directory is
on sys.path. The patch is intentionally additive and disabled unless the Cloud
URL + device token are configured.

Desktop behavior:
- normal backend conversation can use ULTRON Cloud first;
- local tools, voice, vision and Ollama stay available;
- explicit local remember commands are mirrored to shared Cloud memory;
- MARK/Gemini Live voice receives the same shared Cloud memory snapshot in its
  system prompt, so typed and spoken conversations know the same persistent facts.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path


# ---------------------------------------------------------------------------
# Backend Agent patch: normal fallback chat -> Cloud first, local Ollama second
# ---------------------------------------------------------------------------
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
        result = await _original_run(self, text, approved)
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


# ---------------------------------------------------------------------------
# MARK / Gemini Live voice patch
# ---------------------------------------------------------------------------
def _is_mark_voice_process() -> bool:
    try:
        # START.bat launches main.py, which then imports/runs mark_app.py.
        # Accept both entrypoints so the voice memory patch is installed in the
        # real desktop launch path as well as direct mark_app.py runs.
        return Path(sys.argv[0]).name.lower() in {"main.py", "mark_app.py"}
    except Exception:
        return False


def _shared_cloud_memory_text() -> str:
    """Fetch the persistent Cloud memory without exposing credentials."""
    base = os.getenv("ULTRON_CLOUD_URL", "").strip().rstrip("/")
    token = os.getenv("ULTRON_DEVICE_TOKEN", "").strip()
    if not base or not token:
        return ""
    try:
        request = urllib.request.Request(
            base + "/api/memories",
            headers={
                "Authorization": f"Bearer {token}",
                "X-ULTRON-DEVICE": os.getenv("ULTRON_CLOUD_DEVICE_ID", "desktop-ultron-voice"),
                "Accept": "application/json",
            },
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rows = payload.get("memories", [])
        if not isinstance(rows, list) or not rows:
            return ""
        lines = [
            "[SHARED ULTRON CLOUD MEMORY — persistent across phone, typed desktop and voice]",
            "These facts are authoritative persistent memory for this user.",
            "If the user asks about a fact listed below, answer from it directly.",
            "Never say a listed fact is unknown or unsaved.",
            "Match keys semantically across underscores, spaces, casing and Turkish/English wording.",
        ]
        for row in rows[:100]:
            if not isinstance(row, dict):
                continue
            key = str(row.get("key", "")).strip()
            value = str(row.get("value", "")).strip()
            category = str(row.get("category", "FACT")).strip() or "FACT"
            if key and value:
                lines.append(f"- [{category}] {key}: {value}")
        return "\n".join(lines) + "\n" if len(lines) > 5 else ""
    except Exception:
        return ""


if _is_mark_voice_process():
    try:
        project_root = Path(__file__).resolve().parents[2]
        root_text = str(project_root)
        inserted = False
        if root_text not in sys.path:
            sys.path.insert(0, root_text)
            inserted = True
        try:
            from memory import memory_manager as _voice_memory
        finally:
            if inserted:
                try:
                    sys.path.remove(root_text)
                except ValueError:
                    pass

        if not getattr(_voice_memory, "_ultron_cloud_voice_patch", False):
            _local_formatter = _voice_memory.format_memory_for_prompt

            def _cloud_voice_formatter(memory):
                local_text = _local_formatter(memory)
                cloud_text = _shared_cloud_memory_text()
                if cloud_text:
                    return local_text + ("\n" if local_text else "") + cloud_text
                return local_text

            _voice_memory.format_memory_for_prompt = _cloud_voice_formatter
            _voice_memory._ultron_cloud_voice_patch = True
    except Exception:
        pass
