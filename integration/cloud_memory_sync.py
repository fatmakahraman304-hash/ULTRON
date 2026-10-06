from __future__ import annotations

"""Best-effort two-way bridge between ULTRON Cloud and desktop voice memory.

At startup, Cloud memories are copied into memory/long_term.json so Gemini Live
can recall facts learned on the phone or desktop chat. During a voice session,
save_memory mirrors newly learned facts back to Cloud.

Cloud failure must never prevent ULTRON from starting or saving locally.
"""

import json
import os
import urllib.request


def _category(name: str) -> str:
    value = (name or "FACT").strip().upper()
    return {
        "PROFILE": "identity",
        "IDENTITY": "identity",
        "PREFERENCE": "preferences",
        "PREFERENCES": "preferences",
        "PROJECT": "projects",
        "PROJECTS": "projects",
        "RELATIONSHIP": "relationships",
        "RELATIONSHIPS": "relationships",
        "WISH": "wishes",
        "WISHES": "wishes",
        "NOTE": "notes",
        "NOTES": "notes",
        "FACT": "notes",
        "IMPORTANT": "notes",
        "DEVICE": "notes",
        "TASK": "notes",
    }.get(value, "notes")


def _cloud_category(name: str) -> str:
    value = (name or "notes").strip().lower()
    return {
        "identity": "PROFILE",
        "preferences": "PREFERENCE",
        "projects": "PROJECT",
        "relationships": "RELATIONSHIP",
        "wishes": "WISH",
        "notes": "NOTE",
    }.get(value, "NOTE")


def _cloud_settings() -> tuple[str, str, str]:
    base = os.getenv("ULTRON_CLOUD_URL", "").strip().rstrip("/")
    token = os.getenv("ULTRON_DEVICE_TOKEN", "").strip()
    device = os.getenv("ULTRON_CLOUD_DEVICE_ID", "desktop-ultron-voice").strip()
    return base, token, device or "desktop-ultron-voice"


def upsert_cloud_memory(category: str, key: str, value: str) -> tuple[bool, str]:
    """Mirror one locally saved voice-memory fact to ULTRON Cloud."""
    base, token, device = _cloud_settings()
    key = str(key or "").strip()
    value = str(value or "").strip()
    if not base or not token:
        return False, "Cloud mirror skipped: Cloud URL/device token not configured."
    if not key or not value:
        return False, "Cloud mirror skipped: empty key/value."

    try:
        body = json.dumps(
            {
                "category": _cloud_category(category),
                "key": key,
                "value": value,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        req = urllib.request.Request(
            base + "/api/memories",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "X-ULTRON-DEVICE": device,
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            response.read()
        return True, f"Cloud memory mirror OK: {key}"
    except Exception as exc:
        return False, f"Cloud memory mirror skipped: {type(exc).__name__}: {str(exc)[:160]}"


def sync() -> tuple[bool, str]:
    base, token, device = _cloud_settings()
    if not base or not token:
        return False, "Cloud memory sync skipped: Cloud URL/device token not configured."

    try:
        req = urllib.request.Request(
            base + "/api/memories",
            headers={
                "Authorization": f"Bearer {token}",
                "X-ULTRON-DEVICE": device,
                "Accept": "application/json",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rows = payload.get("memories", [])
        if not isinstance(rows, list):
            rows = []

        # Import only after the network read. This module is run from project
        # root, where `memory` resolves to the desktop voice memory package.
        from memory.memory_manager import update_memory

        updates: dict[str, dict[str, dict[str, str]]] = {}
        count = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = str(row.get("key", "")).strip()
            value = str(row.get("value", "")).strip()
            if not key or not value:
                continue
            cat = _category(str(row.get("category", "FACT")))
            updates.setdefault(cat, {})[key] = {"value": value}
            count += 1

        if updates:
            update_memory(updates)
        return True, f"Cloud memory sync OK: {count} memories copied to desktop voice memory."
    except Exception as exc:
        return False, f"Cloud memory sync skipped: {type(exc).__name__}: {str(exc)[:160]}"



def heartbeat(state: dict | None = None) -> tuple[bool, dict]:
    """Publish desktop presence to ULTRON Cloud.

    Best-effort only: presence loss must never interrupt local voice.
    """
    base, token, device = _cloud_settings()
    if not base or not token:
        return False, {}

    try:
        body = json.dumps({"state": state or {}}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            base + "/api/device-presence/heartbeat",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "X-ULTRON-DEVICE": device,
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return True, payload if isinstance(payload, dict) else {}
    except Exception:
        return False, {}


def main() -> int:
    _ok, message = sync()
    print(f"[ULTRON] {message}")
    # Always zero: Cloud being asleep/offline must not block desktop startup.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
