"""Lease ownership monitor for phone-to-desktop agent tasks.

A claim's delivery_attempt is a *fencing token*, not authorization to keep
executing forever. Stop dispatching new work if Cloud reports the attempt as
stale or ownership cannot be refreshed within the configured safety window.

This is a best-effort guard: in-flight, irreversible OS actions cannot be
rolled back. Approval Gate and per-tool permissions are still mandatory.
"""
from __future__ import annotations

import asyncio
import time
from typing import Callable

from cloud_client import CloudDeliveryRejected


class RemoteLeaseGuard:
    def __init__(
        self,
        client,
        command_id: int,
        delivery_attempt: int,
        *,
        interval: float = 5.0,
        request_timeout: float = 8.0,
        max_unconfirmed: float = 15.0,
        log: Callable[[str], None] | None = None,
    ) -> None:
        if command_id <= 0 or delivery_attempt <= 0:
            raise ValueError("Agent task requires a positive command ID and delivery attempt")
        self.client = client
        self.command_id = command_id
        self.delivery_attempt = delivery_attempt
        self.interval = max(0.01, float(interval))
        self.request_timeout = max(0.01, float(request_timeout))
        self.max_unconfirmed = max(self.interval, float(max_unconfirmed))
        self.log = log
        self.lost = asyncio.Event()
        self.reason = ""
        self._last_confirmed = time.monotonic()

    async def run(self) -> None:
        while not self.lost.is_set():
            await asyncio.sleep(self.interval)
            if self.lost.is_set():
                return
            try:
                await asyncio.wait_for(
                    self.client.report_task_progress(
                        self.command_id,
                        delivery_attempt=self.delivery_attempt,
                        stage="lease",
                        message="",
                    ),
                    timeout=self.request_timeout,
                )
                self._last_confirmed = time.monotonic()
            except asyncio.CancelledError:
                raise
            except CloudDeliveryRejected as exc:
                self.reason = f"Cloud rejected attempt {self.delivery_attempt}: {exc}"
                self.lost.set()
                if self.log:
                    self.log(self.reason)
                return
            except Exception as exc:
                elapsed = time.monotonic() - self._last_confirmed
                if self.log:
                    self.log(f"Cloud lease renewal failed: {type(exc).__name__}: {str(exc)[:160]}")
                if elapsed >= self.max_unconfirmed:
                    self.reason = f"Cloud lease unconfirmed for {elapsed:.1f} seconds"
                    self.lost.set()
                    if self.log:
                        self.log(self.reason)
                    return
