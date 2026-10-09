"""Safe ULTRON Desktop -> Cloud development-request transport.

ChatGPT user chats cannot be messaged programmatically by this local app.
No automatic VS Code launch, code write, git push, secrets or arbitrary shell.
The Cloud service creates an authenticated owner-scoped request for the
user's deliberate copy/paste handoff to ChatGPT.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .paths import ROOT


def configured() -> bool:
    return bool(os.getenv("ULTRON_CLOUD_URL", "").strip()
                and os.getenv("ULTRON_DEVICE_TOKEN", "").strip())


def cloud_call(path: str, payload: dict | None = None, timeout: int = 12) -> dict[str, Any]:
    base = os.getenv("ULTRON_CLOUD_URL", "").strip().rstrip("/")
    secret = os.getenv("ULTRON_DEVICE_TOKEN", "").strip()
    if not base.startswith("https://") or not secret:
        raise RuntimeError("Cloud HTTPS and paired device token required")
    if not path.startswith("/api/dev-requests") or ".." in path or "://" in path:
        raise ValueError("Only fixed ULTRON development APIs allowed")
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None,
        headers={
            "Authorization": "Bearer " + secret,
            "X-ULTRON-DEVICE": "desktop-ultron-development",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            data = json.loads(res.read(750000))
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected Cloud development response")
        return data
    except urllib.error.HTTPError as exc:
        # Never print the bearer token or private request body in errors.
        raise RuntimeError("Cloud development request HTTP " + str(exc.code)) from exc


def submit(prompt: str, target: str = "both") -> dict:
    text = str(prompt or "").strip()
    if not 12 <= len(text) <= 2000:
        raise ValueError("Request must be 12 to 2000 characters")
    if target not in ("phone", "desktop", "both"):
        raise ValueError("Unsupported development target")
    reply = cloud_call("/api/dev-requests", {"prompt": text, "target": target})
    item = reply.get("request")
    if not isinstance(item, dict) or not item.get("id") or not item.get("handoff"):
        raise RuntimeError("Cloud did not confirm the new request")
    return item


def list_requests() -> list[dict]:
    reply = cloud_call("/api/dev-requests")
    rows = reply.get("requests", [])
    return rows if isinstance(rows, list) else []


def verify_request(request_id: str) -> dict:
    if not re.fullmatch(r"[0-9a-f-]{36}", str(request_id or "").lower()):
        raise ValueError("Invalid development request ID")
    data = cloud_call("/api/dev-requests/" + request_id + "/verify", {})
    if not data.get("ok") or not isinstance(data.get("request"), dict):
        raise RuntimeError("Development verification incomplete")
    return data["request"]


def local_commit() -> str:
    """Read-only git rev-parse. Never check out, merge or run app code."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=6, check=True,
        )
        sha = proc.stdout.strip().lower()
        return sha if re.fullmatch(r"[0-9a-f]{40}", sha) else ""
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return ""


def report_local_checkout(request_id: str, sha: str | None = None) -> bool:
    """Report an observed local SHA only; Cloud verifies ancestry before success."""
    commit = (sha if sha is not None else local_commit()).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        return False
    if not re.fullmatch(r"[0-9a-f-]{36}", request_id.lower()):
        return False
    data = cloud_call("/api/dev-requests/" + request_id + "/desktop-version",
                      {"commit_sha": commit})
    return bool(data.get("desktop_version_recorded"))
