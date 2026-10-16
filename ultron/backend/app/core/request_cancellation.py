"""In-memory, owner-scoped cancellation state for conversational requests.

This registry coordinates HTTP handlers only. It never claims that a remote
provider stopped unless its transport actually acknowledged cancellation.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import re
import time
from dataclasses import dataclass, field


_REQUEST_ID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")
_REQUEST_KEY = re.compile(r"^[0-9a-f]{64}$")


class ProviderRequestCancelled(Exception):
    """Cancellation raised by the provider adapter with transport-stop proof."""
    def __init__(self, message: str, *, provider_stopped: bool = False):
        super().__init__(message)
        self.provider_stopped = bool(provider_stopped)


def valid_request_id(value: object) -> bool:
    return isinstance(value, str) and bool(_REQUEST_ID.fullmatch(value))


def valid_request_key(value: object) -> bool:
    return isinstance(value, str) and bool(_REQUEST_KEY.fullmatch(value))


@dataclass
class RequestRecord:
    owner: str
    request_id: str
    key_digest: str
    provider: str = "routing"
    provider_cancellable: bool = False
    provider_started: bool = False
    provider_stopped: bool = False
    status: str = "running"
    cancel_requested: bool = False
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    cancel_callback: object = None
    created_at: float = field(default_factory=time.monotonic)
    updated_at: float = field(default_factory=time.monotonic)
    terminal_event: asyncio.Event = field(default_factory=asyncio.Event)


class RequestCancellationRegistry:
    """Bounded request registry keyed by authenticated owner and UUID.

    The per-request key is stored only as a SHA-256 digest. Unknown-ID cancel
    calls create short-lived tombstones so an immediate ESC cannot race ahead
    of the invoke handler's registration.
    """

    def __init__(self, *, max_records: int = 512, ttl_s: float = 180.0) -> None:
        self._records: dict[tuple[str, str], RequestRecord] = {}
        self.max_records = max(16, int(max_records))
        self.ttl_s = max(10.0, float(ttl_s))

    @staticmethod
    def _digest(request_key: str) -> str:
        return hashlib.sha256(request_key.encode("ascii")).hexdigest()

    def _prune(self) -> None:
        now = time.monotonic()
        expired = [key for key, record in self._records.items()
                   if now - record.updated_at > self.ttl_s]
        for key in expired:
            self._records.pop(key, None)
        if len(self._records) >= self.max_records:
            oldest = sorted(self._records.items(), key=lambda item: item[1].updated_at)
            for key, _ in oldest[:len(self._records) - self.max_records + 1]:
                self._records.pop(key, None)

    def register(self, owner: str, request_id: str, request_key: str, *,
                 provider: str = "routing", provider_cancellable: bool = False,
                 cancel_callback=None, started: bool = False) -> RequestRecord:
        if not valid_request_id(request_id) or not valid_request_key(request_key):
            raise ValueError("invalid request identity")
        self._prune()
        lookup = (str(owner), request_id.lower())
        digest = self._digest(request_key)
        record = self._records.get(lookup)
        if record is not None:
            if not hmac.compare_digest(record.key_digest, digest):
                raise ValueError("request identity conflict")
            if record.provider != "pending":
                raise ValueError("request identity already used")
            record.provider = str(provider)[:40]
            record.provider_cancellable = bool(provider_cancellable)
            record.provider_started = bool(started)
            record.cancel_callback = cancel_callback
            record.updated_at = time.monotonic()
            if record.cancel_requested and record.provider_cancellable and callable(cancel_callback):
                cancel_callback()
            elif record.cancel_requested and not record.provider_cancellable:
                record.status = "output_suppressed"
            return record
        record = RequestRecord(owner=lookup[0], request_id=lookup[1], key_digest=digest,
                               provider=str(provider)[:40],
                               provider_cancellable=bool(provider_cancellable),
                               provider_started=bool(started), cancel_callback=cancel_callback)
        self._records[lookup] = record
        return record

    def set_provider(self, record: RequestRecord, provider: str, *,
                     cancellable: bool, started: bool = True,
                     cancel_callback=None) -> None:
        record.provider = str(provider)[:40]
        record.provider_cancellable = bool(cancellable)
        record.provider_started = bool(started)
        record.cancel_callback = cancel_callback
        record.updated_at = time.monotonic()
        if record.cancel_requested and started:
            if cancellable and callable(cancel_callback):
                try:
                    cancel_callback()
                except Exception:
                    pass
            elif not cancellable:
                record.status = "output_suppressed"

    def cancel(self, owner: str, request_id: str, request_key: str) -> dict:
        if not valid_request_id(request_id) or not valid_request_key(request_key):
            return {"status": "not_found", "provider_stopped": False}
        self._prune()
        lookup = (str(owner), request_id.lower())
        digest = self._digest(request_key)
        record = self._records.get(lookup)
        if record is None:
            # Do not let a different authenticated principal create a
            # tombstone for an identifier already owned by another session.
            if any(existing_id == lookup[1] for _existing_owner, existing_id in self._records):
                return {"status": "not_found", "provider_stopped": False}
            record = RequestRecord(owner=lookup[0], request_id=lookup[1],
                                   key_digest=digest, provider="pending")
            record.cancel_requested = True
            record.cancel_event.set()
            record.status = "cancellation_requested"
            self._records[lookup] = record
            return self._result(record)
        if not hmac.compare_digest(record.key_digest, digest):
            return {"status": "not_found", "provider_stopped": False}
        if record.terminal_event.is_set():
            return self._result(record)
        if not record.cancel_requested:
            record.cancel_requested = True
            record.cancel_event.set()
            if record.provider_started and not record.provider_cancellable:
                record.status = "output_suppressed"
            else:
                record.status = "cancellation_requested"
            if record.provider_started and callable(record.cancel_callback):
                try:
                    record.cancel_callback()
                except Exception:
                    pass
        record.updated_at = time.monotonic()
        return self._result(record)

    def finish(self, record: RequestRecord, status: str, *,
               provider_stopped: bool = False) -> None:
        if record.cancel_requested:
            # A local streaming provider raises ProviderRequestCancelled only
            # after its HTTP stream has been closed. Other paths suppress output.
            if status == "cancelled_before_start":
                record.status = "cancelled_before_start"
            elif status == "provider_cancelled" and provider_stopped:
                record.status = "cancelled"
                record.provider_stopped = True
            else:
                record.status = "output_suppressed"
                record.provider_stopped = False
        else:
            record.status = status if status in {"completed", "failed"} else "failed"
        record.updated_at = time.monotonic()
        record.terminal_event.set()

    def lookup(self, owner: str, request_id: str, request_key: str) -> RequestRecord | None:
        if not valid_request_id(request_id) or not valid_request_key(request_key):
            return None
        record = self._records.get((str(owner), request_id.lower()))
        if record is None or not hmac.compare_digest(record.key_digest, self._digest(request_key)):
            return None
        return record

    def describe(self, owner: str, request_id: str, request_key: str) -> dict:
        record = self.lookup(owner, request_id, request_key)
        return self._result(record) if record is not None else {
            "status": "not_found", "provider_stopped": False,
        }

    async def wait_terminal(self, record: RequestRecord, timeout_s: float) -> None:
        if record.terminal_event.is_set():
            return
        try:
            await asyncio.wait_for(record.terminal_event.wait(), timeout=max(0.0, timeout_s))
        except asyncio.TimeoutError:
            pass

    @staticmethod
    def _result(record: RequestRecord) -> dict:
        return {
            "status": record.status,
            "request_id": record.request_id,
            "provider": record.provider,
            "provider_stopped": record.provider_stopped,
            "output_suppressed": record.cancel_requested,
            "operation_continues": record.cancel_requested and not record.provider_cancellable
                and record.provider_started and record.provider not in {"gemini-cloud"},
        }
