"""ULTRON desktop client for the shared cloud brain.

Enabled only when both ULTRON_CLOUD_URL and ULTRON_DEVICE_TOKEN are set.
The desktop keeps local tools/voice/Ollama; general chat can use the shared
Render/Supabase service so phone and PC see the same conversation + memory.
"""
from __future__ import annotations

import os
import time
from typing import Any

import aiohttp


class CloudClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("ULTRON_CLOUD_URL", "").strip().rstrip("/")
        self.device_token = os.getenv("ULTRON_DEVICE_TOKEN", "").strip()
        self.device_id = os.getenv("ULTRON_CLOUD_DEVICE_ID", "desktop-ultron").strip() or "desktop-ultron"
        self.timeout_s = max(5.0, min(float(os.getenv("ULTRON_CLOUD_TIMEOUT", "45")), 120.0))
        self.conversation_id = ""
        self.last_error = ""
        self.last_ok_ts = 0.0

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.device_token)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.device_token}",
            "X-ULTRON-DEVICE": self.device_id,
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, *, json_body: dict | None = None) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("ULTRON Cloud desktop bridge is not configured")
        timeout = aiohttp.ClientTimeout(total=self.timeout_s)
        url = self.base_url + path
        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=self._headers()) as session:
                async with session.request(method, url, json=json_body) as resp:
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {"detail": (await resp.text())[:500]}
                    if resp.status >= 400:
                        raise RuntimeError(str(data.get("detail") or data.get("error") or f"HTTP {resp.status}"))
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

    async def complete_task(
        self,
        command_id: int,
        *,
        ok: bool,
        message: str = "",
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = {"message": str(message)[:8000]}
        if extra:
            result.update(extra)
        return await self._request(
            "POST",
            f"/api/device-commands/{int(command_id)}/complete",
            json_body={"status": "completed" if ok else "failed", "result": result},
        )
