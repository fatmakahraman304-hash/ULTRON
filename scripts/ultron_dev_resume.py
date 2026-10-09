#!/usr/bin/env python3
"""Read-only ULTRON development resume/status report for Codex.

Uses only stdlib, reads the four project continuation documents, and probes
Git metadata without changing repository files or contacting any service.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTINUATION_FILES = (
    "ULTRON_ROADMAP.md",
    "ULTRON_PROGRESS.md",
    "ULTRON_NEXT_TASKS.md",
    "ULTRON_TEST_RESULTS.md",
)


def git_value(root: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True,
            check=False, timeout=5, encoding="utf-8", errors="replace",
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def extract_next_tasks(markdown: str, limit: int = 8) -> list[str]:
    """Read human-authored priorities; never interpret them as shell commands."""
    in_section = False
    tasks: list[str] = []
    for line in markdown.splitlines():
        if re.match(r"^##\s+", line):
            if in_section:
                break
            in_section = bool(re.search(r"(Hemen yapılacak|Immediately|Next tasks)", line, re.IGNORECASE))
            continue
        if not in_section:
            continue
        match = re.match(r"^\s*(?:\d+\.|[-*])\s+(.+)$", line)
        if match:
            tasks.append(match.group(1).strip())
        if len(tasks) >= limit:
            break
    return tasks


def build_report(root: Path) -> dict[str, Any]:
    root = root.resolve()
    documents: dict[str, str] = {}
    for name in CONTINUATION_FILES:
        documents[name] = "present" if (root / name).is_file() else "missing"
    next_file = root / "ULTRON_NEXT_TASKS.md"
    try:
        next_text = next_file.read_text(encoding="utf-8") if next_file.is_file() else ""
    except (UnicodeError, OSError):
        next_text = ""
        documents["ULTRON_NEXT_TASKS.md"] = "unreadable"
    dirty = git_value(root, "status", "--porcelain")
    return {
        "root": str(root),
        "branch": git_value(root, "branch", "--show-current"),
        "commit": git_value(root, "rev-parse", "--short", "HEAD"),
        "last_commit_subject": git_value(root, "log", "-1", "--format=%s"),
        "working_tree": "unknown" if dirty is None else ("clean" if not dirty else "modified"),
        "documents": documents,
        "next_tasks": extract_next_tasks(next_text),
        "notice": "Git status and documentation only; no test or deployment was run.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="ULTRON read-only development continuation report")
    parser.add_argument("--json", action="store_true", help="Machine-readable report")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository path")
    args = parser.parse_args()
    report = build_report(args.root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    print("ULTRON DEVELOPMENT RESUME")
    print(f"Root: {report['root']}")
    print(f"Branch: {report['branch'] or 'unknown'} | HEAD: {report['commit'] or 'unknown'}")
    print(f"Working tree: {report['working_tree']}")
    for name, status in report["documents"].items():
        print(f"  {name}: {status}")
    print("Next tasks:")
    for i, task in enumerate(report["next_tasks"], 1):
        print(f"  {i}. {task}")
    if not report["next_tasks"]:
        print("  No actionable task list found. Inspect ULTRON_NEXT_TASKS.md.")
    print(report["notice"])


if __name__ == "__main__":
    main()
