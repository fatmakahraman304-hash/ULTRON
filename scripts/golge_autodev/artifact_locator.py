"""Select a recent engineering-memory artifact from the exact repository workflow."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ARTIFACT_NAME = "golge-autodev-engineering-memory"
MAX_AGE_DAYS = 90


def _artifact_rows(payload: object) -> list[dict]:
    if isinstance(payload, dict) and isinstance(payload.get("artifacts"), list):
        return payload["artifacts"]
    if isinstance(payload, list):
        rows = []
        for item in payload:
            if isinstance(item, dict) and isinstance(item.get("artifacts"), list):
                rows.extend(item["artifacts"])
            elif isinstance(item, dict):
                rows.append(item)
        return rows
    raise ValueError("artifact_listing_invalid")


def select_latest(payload: object, *, repository_id: str, workflow_id: str,
                  source_branch: str, current_run_id: str,
                  now: str | None = None) -> dict | None:
    if (not re.fullmatch(r"[0-9]{1,20}", str(repository_id))
            or not re.fullmatch(r"[0-9]{1,20}", str(workflow_id))
            or not re.fullmatch(r"[1-9][0-9]{0,19}", str(current_run_id))
            or not re.fullmatch(r"[A-Za-z0-9_./-]{1,150}", str(source_branch))):
        raise ValueError("artifact_query_identity_invalid")
    moment = datetime.fromisoformat((now or datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))
    cutoff = moment - timedelta(days=MAX_AGE_DAYS)
    accepted = []
    for artifact in _artifact_rows(payload):
        if not isinstance(artifact, dict) or artifact.get("name") != ARTIFACT_NAME or artifact.get("expired") is not False:
            continue
        run = artifact.get("workflow_run")
        if not isinstance(run, dict):
            continue
        if (str(run.get("repository_id")) != str(repository_id)
                or (run.get("workflow_id") is not None and str(run.get("workflow_id")) != str(workflow_id))
                or str(run.get("id")) == str(current_run_id)
                or run.get("head_branch") not in {"main", source_branch}):
            continue
        try:
            created = datetime.fromisoformat(str(artifact.get("created_at", "")).replace("Z", "+00:00"))
            expiry = datetime.fromisoformat(str(artifact.get("expires_at", "")).replace("Z", "+00:00"))
        except ValueError:
            continue
        artifact_id = artifact.get("id")
        run_id = run.get("id")
        if (created < cutoff or created > moment + timedelta(minutes=5) or expiry <= moment
                or not re.fullmatch(r"[0-9]{1,20}", str(artifact_id))
                or not re.fullmatch(r"[1-9][0-9]{0,19}", str(run_id))):
            continue
        accepted.append({"artifact_id": str(artifact_id), "run_id": str(run_id),
                         "created_at": created.isoformat(), "run_branch": run["head_branch"],
                         "workflow_id": str(workflow_id), "source_branch": source_branch,
                         "head_sha": str(run.get("head_sha", ""))[:40]})
    return max(accepted, key=lambda row: row["created_at"]) if accepted else None


def validate_run_details(selected: dict, details: dict, *, repository_id: str,
                         workflow_id: str, source_branch: str,
                         current_run_id: str) -> bool:
    """Bind artifact metadata to GitHub's authoritative workflow-run record."""
    if not isinstance(selected, dict) or not isinstance(details, dict):
        return False
    repository = details.get("repository")
    if not isinstance(repository, dict):
        return False
    if (str(details.get("id")) != selected.get("run_id")
            or str(details.get("workflow_id")) != str(workflow_id)
            or str(repository.get("id")) != str(repository_id)
            or details.get("head_branch") not in {"main", source_branch}
            or details.get("head_branch") != selected.get("run_branch")
            or not re.fullmatch(r"[0-9a-fA-F]{40}", str(selected.get("head_sha", "")))
            or str(details.get("head_sha", "")).lower() != str(selected.get("head_sha", "")).lower()
            or str(details.get("id")) == str(current_run_id)
            or details.get("path") != ".github/workflows/golge-autodev.yml"
            or details.get("event") == "pull_request"):
        return False
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--current-run-id", required=True)
    parser.add_argument("--now", default=None)
    parser.add_argument("--selected", type=Path,
                        help="Selected artifact JSON; when set, verify --run-details against GitHub REST API data.")
    parser.add_argument("--run-details", type=Path)
    args = parser.parse_args(argv)
    if ((args.selected and args.selected.is_symlink()) or (args.run_details and args.run_details.is_symlink())
            or args.input.is_symlink() or args.input.stat().st_size > 8_000_000):
        parser.error("artifact_listing_rejected")
    if args.selected:
        if not args.run_details or args.selected.stat().st_size > 20_000 or args.run_details.stat().st_size > 100_000:
            parser.error("selected_artifact_or_run_details_missing")
        result = json.loads(args.selected.read_text(encoding="utf-8"))
        details = json.loads(args.run_details.read_text(encoding="utf-8"))
        if not validate_run_details(result, details, repository_id=args.repository_id,
                                    workflow_id=args.workflow_id, source_branch=args.source_branch,
                                    current_run_id=args.current_run_id):
            print("memory artifact workflow provenance mismatch; fail closed")
            return 2
    else:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        result = select_latest(payload, repository_id=args.repository_id, workflow_id=args.workflow_id,
                               source_branch=args.source_branch, current_run_id=args.current_run_id,
                               now=args.now)
    if result is None:
        print("memory artifact missing or expired; fail closed")
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
