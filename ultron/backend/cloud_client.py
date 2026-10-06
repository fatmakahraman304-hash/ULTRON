"""ULTRON desktop client for the shared cloud brain.

Enabled only when both ULTRON_CLOUD_URL and ULTRON_DEVICE_TOKEN are set.
The desktop keeps local tools/voice/Ollama; general chat can use the shared
Render/Supabase service so phone and PC see the same conversation + memory.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any


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

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.device_token)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.device_token}",
            "X-ULTRON-DEVICE": self.device_id,
            "Content-Type": "application/json",
        }

    def _sync_request(self, method: str, path: str, json_body: dict | None = None) -> dict[str, Any]:
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
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
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
            raise RuntimeError(str(message)) from exc

    async def _request(self, method: str, path: str, *, json_body: dict | None = None) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("ULTRON Cloud desktop bridge is not configured")
        try:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(
                self._executor,
                self._sync_request,
                method,
                path,
                json_body,
            )
            self.last_error = ""
            self.last_ok_ts = time.time()
            return data
        except Exception as exc:
            self.last_error = str(exc)[:500]
            raise

    async def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "enabled": False, "error": "not configured"}
        try:
            data = await self._request("GET", "/health")
            return {"enabled": True, **data}
        except Exception as exc:
            return {"ok": False, "enabled": True, "error": str(exc)}

    async def chat(self, message: str) -> dict[str, Any]:
        body: dict[str, Any] = {"message": message}
        if self.conversation_id:
            body["conversation_id"] = self.conversation_id
        data = await self._request("POST", "/api/chat", json_body=body)
        self.conversation_id = str(data.get("conversation_id", "") or self.conversation_id)
        return data

    async def memories(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/api/memories")
        rows = data.get("memories", [])
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

    async def claim_desktop_commands(self) -> list[dict[str, Any]]:
        data = await self._request(
            "POST",
            "/api/device-commands/claim",
            json_body={"target": "desktop"},
        )
        rows = data.get("commands", [])
        return rows if isinstance(rows, list) else []

    async def report_task_progress(
        self,
        command_id: int,
        *,
        stage: str,
        message: str = "",
        percent: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
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
        step_index: int,
        state: dict[str, Any] | None = None,
        note: str = "",
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/device-commands/{int(command_id)}/checkpoint",
            json_body={
                "step_index": max(0, int(step_index)),
                "state": state or {},
                "note": str(note)[:2000],
            },
        )

    async def complete_task(
        self,
        command_id: int,
        *,
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
        return await self._request(
            "POST",
            f"/api/device-commands/{int(command_id)}/complete",
            json_body={"status": "completed" if ok else "failed", "result": result},
        )
