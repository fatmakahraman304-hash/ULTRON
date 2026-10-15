"""Owner-scoped, read-only GitHub and Render diagnostic adapters for GÖLGE.

This trusted HOST-side module must never run inside a generated-code sandbox.
It does not grant a model credentials and contains no mutating API operation.
GitHub code publication remains the separately approved GitHubPRPublisher flow.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request

REPOSITORY = "fatmakahraman304-hash/ULTRON"
RENDER_WORKSPACE_ID = "tea-db20gvek1f9s738lb3rg"
RENDER_SERVICE_ID = "srv-db20lmei0phs73crgujg"
RENDER_DEPLOY_BRANCH = "feat/ultron-cloud-shared-memory"
RENDER_API_BASE = "https://api.render.com/v1/"
MAX_RESPONSE_BYTES = 65_536
REQUEST_TIMEOUT_SECONDS = 10
_ALLOWED_RENDER_PATHS = frozenset({
    f"services/{RENDER_SERVICE_ID}",
    f"services/{RENDER_SERVICE_ID}/events?limit=10",
})


class ConnectorUnavailable(RuntimeError):
    """Non-sensitive, bounded failure class surfaced to the owner."""


class _RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        # Do not forward a bearer credential to a redirected host.
        raise ConnectorUnavailable("render_redirect_rejected")


def _render_get(path: str) -> object:
    if path not in _ALLOWED_RENDER_PATHS:
        raise ConnectorUnavailable("render_action_not_allowed")
    key = os.environ.get("GOLGE_RENDER_API_KEY", "")
    if not key or "\r" in key or "\n" in key or len(key) > 512:
        raise ConnectorUnavailable("render_local_key_not_configured")
    request = urllib.request.Request(
        RENDER_API_BASE + path,
        headers={"Accept": "application/json", "Authorization": "Bearer " + key},
        method="GET",
    )
    opener = urllib.request.build_opener(_RejectRedirect)
    try:
        with opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except ConnectorUnavailable:
        raise
    except (OSError, urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        # The exception may contain request or account data. Do not repeat it.
        raise ConnectorUnavailable("render_read_failed") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ConnectorUnavailable("render_response_too_large")
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        raise ConnectorUnavailable("render_response_invalid") from None


def render_service_status() -> dict:
    """Return safe, preselected fields: never the Render environment or secrets."""
    data = _render_get(f"services/{RENDER_SERVICE_ID}")
    if not isinstance(data, dict) or (
        data.get("id") != RENDER_SERVICE_ID
        or data.get("ownerId") != RENDER_WORKSPACE_ID
        or data.get("repo", "").removesuffix(".git")
        != "https://github.com/" + REPOSITORY
        or data.get("branch") != RENDER_DEPLOY_BRANCH
    ):
        raise ConnectorUnavailable("render_service_identity_mismatch")
    details = data.get("serviceDetails")
    details = details if isinstance(details, dict) else {}
    return {
        "service": "GÖLGE",
        "service_id": RENDER_SERVICE_ID,
        "workspace_id": RENDER_WORKSPACE_ID,
        "deploy_branch": RENDER_DEPLOY_BRANCH,
        "auto_deploy": data.get("autoDeploy") == "yes",
        "suspended": data.get("suspended") == "suspended",
        "url": details.get("url") if details.get("url") == "https://ultron-yubh.onrender.com" else None,
        "read_only": True,
    }


def render_recent_events() -> dict:
    """Summarize only event types/times/status; never forward raw logs/details."""
    rows = _render_get(f"services/{RENDER_SERVICE_ID}/events?limit=10")
    if not isinstance(rows, list):
        raise ConnectorUnavailable("render_events_invalid")
    events = []
    for row in rows[:10]:
        event = row.get("event", row) if isinstance(row, dict) else None
        if not isinstance(event, dict) or event.get("serviceId") != RENDER_SERVICE_ID:
            continue
        kind, timestamp = event.get("type"), event.get("timestamp")
        if not isinstance(kind, str) or not re.fullmatch(r"[a-z_]{1,60}", kind):
            continue
        if not isinstance(timestamp, str) or not re.fullmatch(r"[0-9T:Z.+-]{10,40}", timestamp):
            continue
        details = event.get("details")
        details = details if isinstance(details, dict) else {}
        status = details.get("deployStatus", details.get("buildStatus"))
        events.append({
            "type": kind,
            "timestamp": timestamp,
            "status": status if status in {"succeeded", "failed", "canceled", "cancelled"} else None,
        })
    return {"service_id": RENDER_SERVICE_ID, "events": events, "read_only": True}


def github_pr_status(pr_number: int) -> dict:
    """Read exactly one PR from the pinned repo via the owner's local gh login."""
    if type(pr_number) is not int or not 1 <= pr_number <= 1_000_000:
        raise ConnectorUnavailable("github_pr_number_invalid")
    if not shutil.which("gh"):
        raise ConnectorUnavailable("github_cli_missing")
    try:
        result = subprocess.run(
            ["gh", "api", "-X", "GET", f"repos/{REPOSITORY}/pulls/{pr_number}"],
            capture_output=True, text=True, timeout=REQUEST_TIMEOUT_SECONDS, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ConnectorUnavailable("github_read_failed") from None
    if result.returncode or len(result.stdout) > MAX_RESPONSE_BYTES:
        raise ConnectorUnavailable("github_read_failed")
    try:
        data = json.loads(result.stdout)
    except ValueError:
        raise ConnectorUnavailable("github_response_invalid") from None
    if not isinstance(data, dict) or data.get("number") != pr_number:
        raise ConnectorUnavailable("github_pr_identity_mismatch")
    base = data.get("base", {})
    head = data.get("head", {})
    base = base if isinstance(base, dict) else {}
    head = head if isinstance(head, dict) else {}
    return {
        "repository": REPOSITORY,
        "number": pr_number,
        "state": data.get("state") if data.get("state") in {"open", "closed"} else "unknown",
        "draft": data.get("draft") is True,
        "merged": data.get("merged") is True,
        "base_branch": base.get("ref") if isinstance(base.get("ref"), str) else None,
        "head_branch": head.get("ref") if isinstance(head.get("ref"), str) else None,
        "url": f"https://github.com/{REPOSITORY}/pull/{pr_number}",
        "read_only": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only GÖLGE GitHub/Render diagnostics")
    parser.add_argument("action", choices=("render-service", "render-events", "github-pr"))
    parser.add_argument("--pr", type=int, default=46)
    args = parser.parse_args(argv)
    try:
        if args.action == "render-service":
            result = render_service_status()
        elif args.action == "render-events":
            result = render_recent_events()
        else:
            result = github_pr_status(args.pr)
    except ConnectorUnavailable as exc:
        print(json.dumps({"status": "unavailable", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "ok", "result": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
