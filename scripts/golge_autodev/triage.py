"""Deterministically verify discovery candidates before model planning.

Only repository-registered regression tests are executed. Raw test output is
used transiently for infrastructure classification and is never returned or
stored. Candidate/source text remains untrusted data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import engine

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_STATUS = {"eligible", "review_required", "deferred_conflict", "backlog"}


def _touched_paths(open_prs: list[dict]) -> set[str]:
    touched = set()
    for pr in open_prs[:200] if isinstance(open_prs, list) else []:
        if not isinstance(pr, dict):
            continue
        files = pr.get("files", pr.get("paths", []))
        for entry in files if isinstance(files, list) else []:
            path = entry.get("path") if isinstance(entry, dict) else entry
            if isinstance(path, str) and len(path) <= 240 and not path.startswith("/"):
                touched.add(path.removeprefix("./"))
    return touched


def run_registered_tests(candidates: list[dict], *, root: Path,
                         timeout_seconds: int = 180) -> dict[str, dict]:
    """Run unique tests only when a candidate maps to a fixed registered goal."""
    if not 1 <= timeout_seconds <= 240:
        raise ValueError("test_timeout_out_of_range")
    registered = {goal["test_path"] for goal in engine.load_goals()}
    requested = set()
    for candidate in candidates if isinstance(candidates, list) else []:
        if not isinstance(candidate, dict) or candidate.get("status") != "eligible":
            continue
        goal = next((g for g in engine.load_goals() if g["id"] == candidate.get("goal_id")), None)
        tests = candidate.get("required_tests", [])
        if not goal or goal["test_path"] not in tests or goal["test_path"] not in registered:
            continue
        requested.add(goal["test_path"])
    results = {}
    for test_path in sorted(requested):
        file = root / test_path
        if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(root.resolve()):
            results[test_path] = {"state": "no_registered_test", "returncode": 2}
            continue
        try:
            run = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "--disable-warnings", "--tb=no", test_path],
                cwd=root, capture_output=True, text=True, timeout=timeout_seconds,
                env={k: v for k, v in __import__("os").environ.items()
                     if not re.search(r"(?i)(token|secret|api.?key|password|credential)", k)},
            )
            output = (run.stdout + "\n" + run.stderr)[-6000:]
            if run.returncode == 0:
                state = "passed"
            elif not engine.failure_is_repairable(output):
                state = "infrastructure_failure"
            else:
                state = "failed_code"
            results[test_path] = {"state": state, "returncode": int(run.returncode)}
        except subprocess.TimeoutExpired:
            results[test_path] = {"state": "infrastructure_failure", "returncode": 124}
        except OSError:
            results[test_path] = {"state": "infrastructure_failure", "returncode": 2}
    return results


def triage_candidates(candidates: list[dict], *, base_sha: str,
                      open_prs: list[dict] | None = None,
                      test_results: dict[str, dict] | None = None) -> list[dict]:
    if not SHA_RE.fullmatch(base_sha):
        raise ValueError("invalid_source_sha")
    tests = test_results or {}
    touched = _touched_paths(open_prs or [])
    goals = {g["id"]: g for g in engine.load_goals()}
    out = []
    for original in candidates if isinstance(candidates, list) else []:
        if not isinstance(original, dict):
            continue
        candidate = dict(original)
        old_status = candidate.get("status")
        goal = goals.get(candidate.get("goal_id"))
        required = candidate.get("required_tests")
        exact_test = goal["test_path"] if goal and isinstance(required, list) and goal["test_path"] in required else None
        files = candidate.get("affected_files", [])
        conflicts = bool(set(files if isinstance(files, list) else []) & touched)
        evidence = candidate.get("evidence")
        source = candidate.get("source")
        source_ref = candidate.get("source_ref")
        candidate_fingerprint = "\0".join((str(source or ""), str(source_ref or ""),
                                            str(candidate.get("component") or ""), str(evidence or "")))
        expected_candidate_id = hashlib.sha256(candidate_fingerprint.encode()).hexdigest()[:20]
        evidence_ok = False
        source_ref_ok = False
        if source == "github_actions_failure":
            run_match = re.fullmatch(r"run:([1-9][0-9]{0,12})", str(source_ref))
            source_ref_ok = bool(run_match)
            if run_match:
                evidence_match = re.fullmatch(
                    r"Production-branch Actions run #([1-9][0-9]{0,12}) failed a registered regression test; commit ([0-9a-f]{40}|unavailable)\.",
                    str(evidence))
                generic_match = re.fullmatch(
                    r"Production-branch Actions run #([1-9][0-9]{0,12}) has a failed job; failing logs were not fetched\.",
                    str(evidence))
                evidence_ok = bool((evidence_match and evidence_match.group(1) == run_match.group(1))
                                   or (generic_match and generic_match.group(1) == run_match.group(1)))
        elif source == "github_issue":
            issue_match = re.fullmatch(
                r"https://github\.com/fatmakahraman304-hash/ULTRON/issues/([1-9][0-9]{0,8})", str(source_ref))
            source_ref_ok = bool(issue_match)
            if issue_match:
                evidence_ok = str(evidence) == (
                    f"Maintainer-verified issue #{issue_match.group(1)} is labelled for component "
                    f"{candidate.get('component')}; title and body were excluded from model context.")
        elif source == "static_analysis":
            static_match = re.fullmatch(
                r"(ultron/backend/[A-Za-z0-9_./-]+):([0-9]{1,8}):([a-z_]{3,40})", str(source_ref))
            source_ref_ok = bool(static_match)
            if static_match:
                severity = "error" if static_match.group(3) == "syntax" else "high"
                evidence_ok = str(evidence) == (
                    f"Deterministic static analysis reported {severity} {static_match.group(3)} at repository-relative "
                    f"path {static_match.group(1)}, line {static_match.group(2)}.")
        elif source == "roadmap_backlog":
            source_ref_ok = bool(re.fullmatch(r"ULTRON_(?:NEXT_TASKS|ROADMAP)\.md:[1-9][0-9]{0,7}", str(source_ref)))
        elif source in {"application_error_log", "health_report", "performance_report"}:
            source_ref_ok = bool(re.fullmatch(r"[A-Za-z0-9_.:-]{1,180}", str(source_ref)))
        source_ok = (source in {
            "github_actions_failure", "github_issue", "static_analysis", "application_error_log",
            "health_report", "performance_report", "roadmap_backlog"}
            and source_ref_ok
            and isinstance(candidate.get("candidate_id"), str)
            and re.fullmatch(r"[a-f0-9]{20}", candidate["candidate_id"])
            and candidate["candidate_id"] == expected_candidate_id
            and isinstance(evidence, str) and len(evidence) <= 500
            and (evidence_ok or source not in {"github_actions_failure", "github_issue", "static_analysis"}))
        verification = "no_registered_test"
        result = tests.get(exact_test) if exact_test else None
        if conflicts:
            state, verification = "blocked", "conflict"
        elif not source_ok:
            state, verification = "insufficient_evidence", "source_unverified"
        elif old_status not in ALLOWED_STATUS or not exact_test:
            state = "insufficient_evidence" if candidate.get("source") == "github_actions_failure" else "review_required"
        elif candidate.get("risk_level") == "high":
            state = "review_required"
        elif not result:
            state, verification = "insufficient_evidence", "not_run"
        elif result.get("state") == "no_registered_test":
            state, verification = "insufficient_evidence", "no_registered_test"
        elif result.get("state") == "passed":
            state, verification = "already_addressed", "passed"
        elif result.get("state") == "infrastructure_failure":
            state, verification = "blocked", "infrastructure_failure"
        elif result.get("state") == "failed_code":
            state, verification = "eligible", "reproduced"
        else:
            state, verification = "insufficient_evidence", "source_unverified"
        candidate["status"] = state
        candidate["verification_status"] = verification
        candidate["verified_test"] = exact_test
        candidate["verification_sha"] = base_sha
        candidate["test_returncode"] = result.get("returncode") if result else None
        out.append(candidate)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--open-pr-paths", type=Path)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--test-timeout", type=int, default=180)
    args = parser.parse_args(argv)
    if args.input.is_symlink() or args.input.stat().st_size > 2_000_000:
        parser.error("discovery_input_rejected")
    data = json.loads(args.input.read_text(encoding="utf-8"))
    candidates = data.get("candidates", [])
    open_prs = []
    if args.open_pr_paths:
        open_prs = json.loads(args.open_pr_paths.read_text(encoding="utf-8"))
    test_results = run_registered_tests(candidates, root=args.root.resolve(),
                                        timeout_seconds=args.test_timeout)
    data["candidates"] = triage_candidates(candidates, base_sha=args.base_sha,
                                           open_prs=open_prs, test_results=test_results)
    data["triage"] = {"base_sha": args.base_sha, "tests_run": test_results,
                       "eligible": sum(c.get("status") == "eligible" for c in data["candidates"]),
                       "review_required": sum(c.get("status") == "review_required" for c in data["candidates"]),
                       "insufficient_evidence": sum(c.get("status") == "insufficient_evidence" for c in data["candidates"]),
                       "already_addressed": sum(c.get("status") == "already_addressed" for c in data["candidates"]),
                       "blocked": sum(c.get("status") == "blocked" for c in data["candidates"])}
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"candidates": len(data["candidates"]), **data["triage"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
