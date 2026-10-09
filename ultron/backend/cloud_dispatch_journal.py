"""Crash-conservative dispatch journal for phone-originated desktop tasks.

Reserve a Cloud command ID durably BEFORE Gemini sees the task. A reclaimed
Cloud delivery must never implicitly replay a command that MAY already have
run local tools. This protects only this installation and its local database;
it does NOT provide per-tool exactly-once execution or distributed consensus.

Do not store plaintext user tasks, responses, or device credentials.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


class JournalUnavailable(RuntimeError):
    """The durable fence cannot be trusted. Refuse remote execution."""


class RemoteDispatchJournal:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def reserve(
        self,
        *,
        service_url: str,
        device_id: str,
        command_id: int,
        delivery_attempt: int,
        payload: dict[str, Any],
    ) -> bool:
        """Atomically reserve one Cloud command on this laptop.

        Returns False if any delivery attempt previously reserved the command.
        A crash after reservation but before dispatch is intentionally treated
        as uncertain and blocked on retry. Only a new Cloud command ID may be
        sent automatically. This safety tradeoff requires manual review.
        """
        try:
            command_id = int(command_id)
            delivery_attempt = int(delivery_attempt)
            if command_id <= 0 or delivery_attempt <= 0:
                raise ValueError("invalid Cloud delivery identity")
            if not service_url or not device_id or not isinstance(payload, dict):
                raise ValueError("missing Cloud device identity or payload")

            scope = hashlib.sha256(
                (service_url.rstrip("/") + "\0" + device_id).encode("utf-8")
            ).hexdigest()
            payload_hash = hashlib.sha256(
                json.dumps(
                    payload, sort_keys=True, ensure_ascii=False,
                    separators=(",", ":"), allow_nan=False
                ).encode("utf-8")
            ).hexdigest()

            # No plaintext task contents or tokens are persisted in this file.
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(self.path), timeout=3.0, isolation_level=None) as db:
                db.execute("PRAGMA synchronous=FULL")
                db.execute("BEGIN IMMEDIATE")
                try:
                    db.execute(
                        """CREATE TABLE IF NOT EXISTS remote_dispatch (
                            scope TEXT NOT NULL,
                            command_id INTEGER NOT NULL,
                            first_attempt INTEGER NOT NULL,
                            payload_sha256 TEXT NOT NULL,
                            reserved_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (scope, command_id)
                        )"""
                    )
                    cursor = db.execute(
                        """INSERT OR IGNORE INTO remote_dispatch
                           (scope, command_id, first_attempt, payload_sha256)
                           VALUES (?, ?, ?, ?)""",
                        (scope, command_id, delivery_attempt, payload_hash),
                    )
                    reserved = cursor.rowcount == 1
                    db.execute("COMMIT")
                    return reserved
                except BaseException:
                    db.execute("ROLLBACK")
                    raise
        except (OSError, sqlite3.Error, ValueError, TypeError, OverflowError) as exc:
            raise JournalUnavailable(
                f"Desktop dispatch journal unavailable: {type(exc).__name__}"
            ) from exc
