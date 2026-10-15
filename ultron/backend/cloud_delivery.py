"""Lease ownership monitor for phone-to-desktop agent tasks.

A claim's delivery_attempt is a *fencing token*, not authorization to keep
executing forever. Stop dispatching new work if Cloud reports the attempt as
stale or ownership cannot be refreshed within the configured safety window.

This is a best-effort guard: in-flight, irreversible OS actions cannot be
rolled back. Approval Gate and per-tool permissions are still mandatory.
"""
from __future__ import annotations

import asyncio
import threading
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
        interrupt_on_lost: Callable[[], None] | None = None,
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
        self.interrupt_on_lost = interrupt_on_lost
        self.lost = asyncio.Event()
        self.reason = ""
        self._last_confirmed = time.monotonic()

    def _run_sync_heartbeats(
        self, stop: threading.Event, loop: asyncio.AbstractEventLoop
    ) -> None:
        """Renew on a dedicated OS thread; Ollama/GUI may stall asyncio.

        Cloud fences expired attempts by delivery_attempt. A disconnected
        desktop still loses its lease after the normal server timeout.
        """
        while not stop.is_set():
            try:
                self.client.renew_lease_sync(
                    self.command_id,
                    delivery_attempt=self.delivery_attempt,
                    timeout=self.request_timeout,
                )
                self._last_confirmed = time.monotonic()
            except CloudDeliveryRejected as exc:
                if stop.is_set():
                    return
                self.reason = f"Cloud rejected attempt {self.delivery_attempt}: {exc}"
                if self.interrupt_on_lost:
                    try:
                        self.interrupt_on_lost()
                    except Exception:
                        pass
                if self.log:
                    self.log(self.reason)
                loop.call_soon_threadsafe(self.lost.set)
                return
            except Exception as exc:
                if stop.is_set():
                    return
                elapsed = time.monotonic() - self._last_confirmed
                if self.log:
                    self.log(
                        f"Cloud lease renewal failed: {type(exc).__name__}: {str(exc)[:160]}"
                    )
                if elapsed >= self.max_unconfirmed:
                    self.reason = f"Cloud lease unconfirmed for {elapsed:.1f} seconds"
                    if self.interrupt_on_lost:
                        try:
                            self.interrupt_on_lost()
                        except Exception:
                            pass
                    if self.log:
                        self.log(self.reason)
                    loop.call_soon_threadsafe(self.lost.set)
                    return
            stop.wait(self.interval)

    async def run(self) -> None:
        # Real CloudClient has a bounded synchronous heartbeat path. It must
        # not depend on the same asyncio scheduler as the local inference UI.
        # Lightweight async test clients retain the original testable path.
        if callable(getattr(self.client, "renew_lease_sync", None)):
            loop = asyncio.get_running_loop()
            stop = threading.Event()
            thread = threading.Thread(
                target=self._run_sync_heartbeats, args=(stop, loop),
                name=f"ultron-cloud-lease-{self.command_id}", daemon=True,
            )
            thread.start()
            try:
                await self.lost.wait()
            finally:
                stop.set()
            return
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
