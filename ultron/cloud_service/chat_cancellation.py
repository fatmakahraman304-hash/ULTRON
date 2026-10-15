"""Short-lived owner/device-scoped suppression state for Cloud chat turns.

Gemini's synchronous `generate_content` call has no confirmed per-request
cancel handle in this project. This registry suppresses and avoids persisting a
late assistant reply; it does not claim to stop provider inference.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import time
import uuid


_KEY = re.compile(r"^[0-9a-f]{64}$")


class ChatCancellationRegistry:
    def __init__(self, *, limit: int = 512, ttl_s: float = 300.0):
        import asyncio
        self.completion_lock = asyncio.Lock()
        self._records: dict[tuple[str, str, str], dict] = {}
        self.limit = max(16, int(limit))
        self.ttl_s = max(30.0, float(ttl_s))

    @staticmethod
    def _key_digest(key: str) -> str:
        return hashlib.sha256(key.encode("ascii")).hexdigest()

    def _prune(self):
        now = time.monotonic()
        for ident, row in list(self._records.items()):
            if now - row["updated"] > self.ttl_s:
                self._records.pop(ident, None)
        if len(self._records) >= self.limit:
            oldest = sorted(self._records.items(), key=lambda item: item[1]["updated"])
            for ident, _ in oldest[:len(self._records) - self.limit + 1]:
                self._records.pop(ident, None)

    def begin(self, owner: str, device: str, request_id: str, request_key: str) -> dict:
        ident = str(uuid.UUID(request_id))
        if not _KEY.fullmatch(request_key):
            raise ValueError("invalid request key")
        self._prune()
        lookup = (str(owner), str(device), ident)
        digest = self._key_digest(request_key)
        existing = self._records.get(lookup)
        if existing is not None:
            if not hmac.compare_digest(existing["key_digest"], digest):
                raise ValueError("request identity conflict")
            if not existing.get("pending"):
                raise ValueError("request identity already used")
            existing["pending"] = False
            existing["updated"] = time.monotonic()
            return existing
        row = {"key_digest": digest, "cancel_requested": False,
               "provider_stopped": False, "pending": False, "completed": False,
               "conversation_id": None, "updated": time.monotonic()}
        self._records[lookup] = row
        return row

    def cancel(self, owner: str, device: str, request_id: str, request_key: str) -> dict:
        try:
            ident = str(uuid.UUID(request_id))
        except (TypeError, ValueError, AttributeError):
            return {"status": "not_found", "provider_stopped": False}
        if not isinstance(request_key, str) or not _KEY.fullmatch(request_key):
            return {"status": "not_found", "provider_stopped": False}
        self._prune()
        lookup = (str(owner), str(device), ident)
        digest = self._key_digest(request_key)
        row = self._records.get(lookup)
        if row is None:
            if any(existing_id == ident for _owner, _device, existing_id in self._records):
                return {"status": "not_found", "provider_stopped": False}
            # A tombstone closes the cancel-before-chat-registration race.
            # Authentication and the unguessable request key bind it to owner.
            row = {"key_digest": digest, "cancel_requested": True,
                   "provider_stopped": False, "pending": True,
                   "completed": False, "conversation_id": None,
                   "updated": time.monotonic()}
            self._records[lookup] = row
        elif not hmac.compare_digest(row["key_digest"], digest):
            return {"status": "not_found", "provider_stopped": False}
        else:
            if row.get("completed"):
                return {"status": "already_completed", "provider_stopped": False,
                        "conversation_id": row.get("conversation_id")}
            row["cancel_requested"] = True
            row["updated"] = time.monotonic()
        return {"status": "output_suppressed", "provider_stopped": False,
                "conversation_id": row.get("conversation_id")}

    def mark_completed(self, owner: str, device: str, request_id: str,
                       request_key: str) -> None:
        """Record successful persistence so a later stop cannot relabel it."""
        ident = str(uuid.UUID(request_id))
        row = self._records.get((str(owner), str(device), ident))
        if row is None or not hmac.compare_digest(
                row["key_digest"], self._key_digest(request_key)):
            return
        row["completed"] = True
        row["updated"] = time.monotonic()

