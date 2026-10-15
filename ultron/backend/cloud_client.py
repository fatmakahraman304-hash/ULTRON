"""ULTRON desktop client for the shared cloud brain.

Enabled only when both ULTRON_CLOUD_URL and ULTRON_DEVICE_TOKEN are set.
The desktop keeps local tools/voice/Ollama; general chat can use the shared
Render/Supabase service so phone and PC see the same conversation + memory.
"""
from __future__ import annotations

import asyncio
from functools import partial
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any


class CloudTransientError(RuntimeError):
    """Retryable HTTP failure, without exposing provider response bodies."""


class CloudDeliveryRejected(RuntimeError):
    """Cloud says a claimed task's attempt is no longer active.

    404/409 on a leased-task endpoint is terminal for *this worker*; retrying
    the same delivery_attempt cannot regain ownership of a newer claim.
    """

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


def safe_cloud_error(exc: Exception) -> str:
    """Classify cloud failures for status/activity output without echoing details."""
    current = exc
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, CloudTransientError):
            return "cloud_temporarily_unavailable"
        if isinstance(current, CloudDeliveryRejected):
            return "cloud_request_rejected"
        if isinstance(current, (TimeoutError, ConnectionError)):
            return "cloud_temporarily_unavailable"
        status = getattr(current, "status_code", None) or getattr(current, "code", None)
        try:
            status = int(status)
        except (TypeError, ValueError):
            status = None
        if status in (408, 425, 429) or (status is not None and status >= 500):
            return "cloud_temporarily_unavailable"
        if status is not None and 400 <= status < 500:
            return "cloud_request_rejected"
        if isinstance(current, urllib.error.HTTPError):
            return "cloud_request_failed"
        if isinstance(current, urllib.error.URLError):
            return "cloud_temporarily_unavailable"
        class_name = type(current).__name__.lower()
        if any(marker in class_name for marker in ("timeout", "connecterror", "connectionerror")):
            return "cloud_temporarily_unavailable"
        current = current.__cause__ or current.__context__
    return "cloud_request_failed"


class CloudClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("ULTRON_CLOUD_URL", "").strip().rstrip("/")
        self.device_token = os.getenv("ULTRON_DEVICE_TOKEN", "").strip()
        self.device_id = os.getenv("ULTRON_CLOUD_DEVICE_ID", "desktop-ultron").strip() or "desktop-ultron"
        self.timeout_s = max(5.0, min(float(os.getenv("ULTRON_CLOUD_TIMEOUT", "45")), 120.0))
        self.conversation_id = ""
        self.last_error = ""
        self.last_ok_ts = 0.0
        # Cloud I/O deliberately owns its own executor instead of asyncio's
        # default executor. The desktop voice runtime may tear down/rebuild
        # session-scoped executors during reconnects; remote task delivery must
        # keep polling through those transitions.
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ultron-cloud")
        self._local_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ultron-qwen")

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.device_token)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.device_token}",
            "X-ULTRON-DEVICE": self.device_id,
            "Content-Type": "application/json",
        }

    def _sync_request(self, method: str, path: str, json_body: dict | None = None, *, timeout: float | None = None) -> dict[str, Any]:
        url = self.base_url + path
        payload = None
        if json_body is not None:
            payload = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers=self._headers(),
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s if timeout is None else timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    data = json.loads(raw) if raw else {}
                except Exception:
                    data = {"detail": raw[:500]}
                if not isinstance(data, dict):
                    data = {"data": data}
                return data
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw) if raw else {}
            except Exception:
                data = {"detail": raw[:500]}
            if isinstance(data, dict):
                message = data.get("detail") or data.get("error") or f"HTTP {exc.code}"
            else:
                message = f"HTTP {exc.code}"
            if exc.code in (404, 409) and path.startswith("/api/device-commands/"):
                raise CloudDeliveryRejected(exc.code, str(message)) from exc
            if exc.code >= 500 or exc.code == 429:
                raise CloudTransientError(f"Cloud HTTP {exc.code}") from exc
            raise RuntimeError(str(message)) from exc

    async def _request(self, method: str, path: str, *,
                       json_body: dict | None = None,
                       timeout: float | None = None) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("ULTRON Cloud desktop bridge is not configured")
        try:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(
                self._executor,
                (partial(self._sync_request, timeout=timeout)
                 if timeout is not None else self._sync_request),
                method,
                path,
                json_body,
            )
            self.last_error = ""
            self.last_ok_ts = time.time()
            return data
        except Exception as exc:
            self.last_error = safe_cloud_error(exc)
            raise

    def renew_lease_sync(self, command_id: int, *, delivery_attempt: int,
                         timeout: float = 8.0) -> dict[str, Any]:
        """Keep an in-flight command leased even if voice/GUI blocks asyncio.

        Dedicated daemon heartbeat thread calls this directly rather than
        sharing the Cloud request executor or the audio event loop.
        """
        if not self.enabled:
            raise RuntimeError("ULTRON Cloud desktop bridge is not configured")
        return self._sync_request(
            "POST", f"/api/device-commands/{int(command_id)}/progress",
            {"delivery_attempt": int(delivery_attempt), "stage": "lease",
             "message": ""},
            timeout=max(0.1, float(timeout)),
        )

    async def local_chat(self, prompt: str, system: str, turns=None, *, cancellation=None) -> dict:
        """Qwen lifetime is independent of Gemini Live/default executor teardown."""
        from integration.local_cloud_brain import local_chat
        kwargs = {"cancellation": cancellation} if cancellation is not None else {}
        return await asyncio.get_running_loop().run_in_executor(
            self._local_executor, partial(local_chat, prompt, system, turns, **kwargs),
        )

    async def local_listening_analysis(self, prompt: str, system: str, stage: str) -> dict:
        """Private no-tools Qwen transcript analysis; never desktop automation."""
        from integration.local_cloud_brain import local_listening_analysis
        return await asyncio.get_running_loop().run_in_executor(
            self._local_executor,
            partial(local_listening_analysis, prompt, system, stage),
        )

    async def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "enabled": False, "error": "not configured"}
        try:
            data = await self._request("GET", "/health")
            return {"enabled": True, **data}
        except Exception as exc:
            return {"ok": False, "enabled": True, "error": safe_cloud_error(exc)}

    async def chat(self, message: str, *, request_id: str | None = None,
                   request_key: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"message": message}
        if self.conversation_id:
            body["conversation_id"] = self.conversation_id
        if request_id and request_key:
            body.update({"request_id": request_id, "request_key": request_key})
        data = await self._request("POST", "/api/chat", json_body=body)
        if data.get("conversation_id"):
            self.conversation_id = str(data["conversation_id"])
        return data

    async def cancel_chat(self, request_id: str, request_key: str) -> dict[str, Any]:
        """Ask Cloud to suppress this chat's eventual persisted/output reply.

        The current synchronous Gemini `generate_content` call has no confirmed
        provider cancellation API, so this does not claim to stop Gemini.
        """
        data = await self._request(
            "POST", "/api/chat/cancel",
            json_body={"request_id": request_id, "request_key": request_key},
            timeout=8.0,
        )
        if data.get("conversation_id"):
            self.conversation_id = str(data["conversation_id"])
        return data

    async def memories(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/api/memories")
        rows = data.get("memories", [])
        return rows if isinstance(rows, list) else []

    async def live_errors(self, limit: int = 8) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            f"/api/debug/live-errors?limit={max(1, min(int(limit), 20))}",
        )
        rows = data.get("errors", [])
        return rows if isinstance(rows, list) else []

    async def upsert_memory(self, key: str, value: str, category: str = "FACT") -> dict[str, Any]:
        return await self._request(
            "PUT",
            "/api/memories",
            json_body={"key": key[:120], "value": value[:8000], "category": category[:40]},
        )

    async def heartbeat(self, state: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/device-presence/heartbeat",
            json_body={"state": state or {}},
        )

    async def claim_desktop_commands(
        self, *, include_agent_tasks: bool = True,
    ) -> list[dict[str, Any]]:
        # When this desktop is already executing an agent task, keep
        # polling lightweight controls without prematurely claiming another
        # agent task whose lease cannot start until the first has finished.
        data = await self._request(
            "POST",
            "/api/device-commands/claim",
            json_body={"target": "desktop", "include_agent_tasks": include_agent_tasks},
            # An HTTP response may disappear after the Cloud committed the
            # claim. Do not hang for 45 s; Cloud safely requeues only unacked
            # read-only local-chat tasks after 12 s.
            timeout=10.0,
        )
        rows = data.get("commands", [])
        return rows if isinstance(rows, list) else []

    async def report_task_progress(
        self,
        command_id: int,
        *,
        delivery_attempt: int,
        stage: str,
        message: str = "",
        percent: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "delivery_attempt": int(delivery_attempt),
            "stage": str(stage)[:80],
            "message": str(message)[:2000],
        }
        if percent is not None:
            body["percent"] = max(0, min(100, int(percent)))
        return await self._request(
            "POST",
            f"/api/device-commands/{int(command_id)}/progress",
            json_body=body,
        )

    async def save_task_checkpoint(
        self,
        command_id: int,
        *,
        delivery_attempt: int,
        step_index: int,
        state: dict[str, Any] | None = None,
        note: str = "",
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/device-commands/{int(command_id)}/checkpoint",
            json_body={
                "delivery_attempt": int(delivery_attempt),
                "step_index": max(0, int(step_index)),
                "state": state or {},
                "note": str(note)[:2000],
            },
        )

    async def complete_task(
        self,
        command_id: int,
        *,
        delivery_attempt: int,
        ok: bool,
        message: str = "",
        extra: dict[str, Any] | None = None,
        retryable: bool = False,
        retry_after_seconds: int = 30,
    ) -> dict[str, Any]:
        result = {
            "message": str(message)[:8000],
            "retryable": bool(retryable),
            "retry_after_seconds": max(10, min(900, int(retry_after_seconds))),
        }
        if extra:
            result.update(extra)
        body = {"status": "completed" if ok else "failed", "result": result,
                "delivery_attempt": int(delivery_attempt)}
        # Only read-only local completions have the server's same-attempt,
        # same-result replay contract. Never re-execute inference or OS actions.
        local = ok and extra and extra.get("provider") in ("local-ollama", "local-no-image")
        for attempt in range(3 if local else 1):
            try:
                return await self._request(
                    "POST", f"/api/device-commands/{int(command_id)}/complete",
                    json_body=body, timeout=8.0 if local else None,
                )
            except (urllib.error.URLError, TimeoutError, OSError, CloudTransientError):
                if not local or attempt == 2:
                    raise
                await asyncio.sleep(attempt + 1)
