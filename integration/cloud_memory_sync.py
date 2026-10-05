from __future__ import annotations

"""Best-effort startup sync from ULTRON Cloud memory into desktop voice memory.

The desktop text route already talks to Cloud directly. Gemini Live voice,
however, builds its system prompt from memory/long_term.json. This startup sync
copies Cloud memories into that local store before mark_app.py starts so typed,
phone and spoken conversations share the same persistent facts.

Cloud failure must never prevent ULTRON from starting.
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


def sync() -> tuple[bool, str]:
    base = os.getenv("ULTRON_CLOUD_URL", "").strip().rstrip("/")
    token = os.getenv("ULTRON_DEVICE_TOKEN", "").strip()
    if not base or not token:
        return False, "Cloud memory sync skipped: Cloud URL/device token not configured."

    try:
        req = urllib.request.Request(
            base + "/api/memories",
            headers={
                "Authorization": f"Bearer {token}",
                "X-ULTRON-DEVICE": os.getenv(
                    "ULTRON_CLOUD_DEVICE_ID", "desktop-ultron-voice"
                ),
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


def main() -> int:
    _ok, message = sync()
    print(f"[ULTRON] {message}")
    # Always zero: Cloud being asleep/offline must not block desktop startup.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
