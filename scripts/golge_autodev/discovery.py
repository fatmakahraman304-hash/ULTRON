"""Evidence-led self-discovery for GÖLGE's bounded coding proposal loop.

Discovery is deterministic and read-only. It never calls an LLM, executes
repository code, reads issue bodies, or retains application log messages.
Only evidence that maps to a pre-allowlisted goal can be marked eligible.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import engine

MAX_INPUT_RECORDS = 500
MAX_CANDIDATES = 200
MAX_LOG_RECORDS = 10_000
MIN_APP_ERROR_OCCURRENCES = 3
MIN_PERFORMANCE_SAMPLES = 20
PERFORMANCE_REGRESSION_THRESHOLD = 0.20
REPO = "fatmakahraman304-hash/ULTRON"

GOALS = engine.load_goals()
GOALS_BY_ID = {row["id"]: row for row in GOALS}
GOAL_BY_TEST = {row["test_path"]: row for row in GOALS}
GOAL_BY_PATH = {
    path: row for row in GOALS for path in row["paths"]
}
COMPONENT_TO_GOAL = {
    "voice": "voice-interrupt-contract",
    "conversation": "dialogue-continuity-contract",
}
COMPONENT_LABELS = {
    "component:voice": "voice",
    "component:conversation": "conversation",
    "component:memory": "memory",
    "component:research": "research",
    "component:model": "model",
    "component:coding": "coding",
}
PRIORITY_LABELS = {"priority:p0": 100, "priority:p1": 90,
                   "priority:p2": 70, "priority:p3": 50}
SAFE_EXCEPTION = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]{0,100}$")
SAFE_MODULE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]{0,180}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
TEST_PATH_RE = re.compile(r"(?:^|[\s'\"`])((?:ultron/backend/tests/)?test_[A-Za-z0-9_]+\.py)(?:$|[\s'\"`])")


def score_priority(*, user_impact: int, frequency: int, reliability: int,
                   performance_gain: int, security_risk: int,
                   complexity: int, testability: int,
                   conflict: bool = False) -> int:
    """Score 0–100 with transparent weights; complexity and conflicts reduce it."""
    values = (user_impact, frequency, reliability, performance_gain,
              security_risk, complexity, testability)
    if any(isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5 for value in values):
        raise ValueError("priority_inputs_must_be_in_0_5_range")
    raw = (4 * user_impact + 3 * frequency + 3 * reliability
           + 2 * performance_gain + 2 * security_risk + 3 * testability
           - 2 * complexity)
    # Maximum achievable score under the 0–5 input contract is 73.
    result = max(0, min(100, round(raw * 100 / 73)))
    return max(0, result - (25 if conflict else 0))


def _candidate(*, source: str, source_ref: str, evidence: str, component: str,
               proposed_solution: str, priority: int, risk_level: str,
               success_criteria: list[str], required_tests: list[str],
               status: str = "review_required", goal_id: str | None = None,
               paths: list[str] | None = None, **extra: Any) -> dict[str, Any]:
    evidence = " ".join(str(evidence).split())[:500]
    ref = str(source_ref)[:300]
    fingerprint = "\0".join((source, ref, component, evidence))
    candidate_id = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:20]
    row = {
        "candidate_id": candidate_id,
        "source": source,
        "source_ref": ref,
        "evidence": evidence,
        "component": component,
        "proposed_solution": proposed_solution[:300],
        "priority": max(0, min(100, int(priority))),
        "risk_level": risk_level if risk_level in {"low", "medium", "high"} else "high",
        "success_criteria": [str(item)[:180] for item in success_criteria[:5]],
        "required_tests": [str(item)[:180] for item in required_tests[:5]],
        "status": status,
    }
    if goal_id in GOALS_BY_ID:
        row["goal_id"] = goal_id
        row["affected_files"] = list(GOALS_BY_ID[goal_id]["paths"])
    elif paths:
        row["affected_files"] = [str(path)[:180] for path in paths[:3]]
    row.update(extra)
    return row


def _goal_for_test(path: str) -> dict | None:
    normalized = path.removeprefix("./")
    if normalized.startswith("tests/"):
        normalized = "ultron/backend/" + normalized
    return GOAL_BY_TEST.get(normalized)


def candidates_from_actions(runs: list[dict]) -> list[dict]:
    """Use job/step metadata only; never download logs or retain step text."""
    out = []
    for run in (runs if isinstance(runs, list) else [])[:MAX_INPUT_RECORDS]:
        if not isinstance(run, dict) or run.get("conclusion") != "failure":
            continue
        if run.get("headBranch") != engine.BASE_BRANCH:
            continue
        run_id = run.get("databaseId") or run.get("database_id")
        if not isinstance(run_id, int) and not (isinstance(run_id, str) and run_id.isdigit()):
            continue
        sha = str(run.get("headSha") or run.get("head_sha") or "")
        if sha and not SHA.fullmatch(sha):
            sha = ""
        matched_goal = None
        for job in run.get("jobs", []) if isinstance(run.get("jobs"), list) else []:
            if not isinstance(job, dict) or job.get("conclusion") != "failure":
                continue
            for step in job.get("steps", []) if isinstance(job.get("steps"), list) else []:
                if not isinstance(step, dict) or step.get("conclusion") != "failure":
                    continue
                step_name = str(step.get("name") or "")[:500]
                for match in TEST_PATH_RE.findall(step_name):
                    matched_goal = _goal_for_test(match)
                    if matched_goal:
                        break
                if matched_goal:
                    break
            if matched_goal:
                break
        if matched_goal:
            goal_id = matched_goal["id"]
            out.append(_candidate(
                source="github_actions_failure", source_ref=f"run:{run_id}",
                evidence=f"Production-branch Actions run #{run_id} failed a registered regression test; commit {sha or 'unavailable'}.",
                component="voice" if "voice" in goal_id else "conversation",
                proposed_solution="Inspect the observed failing regression and make the smallest allowlisted correction.",
                priority=score_priority(user_impact=4, frequency=3, reliability=5,
                                        performance_gain=1, security_risk=1,
                                        complexity=2, testability=5),
                risk_level="medium", status="eligible", goal_id=goal_id,
                success_criteria=["The registered failing test passes without weakening existing assertions."],
                required_tests=[matched_goal["test_path"]],
            ))
        else:
            out.append(_candidate(
                source="github_actions_failure", source_ref=f"run:{run_id}",
                evidence=f"Production-branch Actions run #{run_id} has a failed job; failing logs were not fetched.",
                component="unclassified", proposed_solution="Review failed job metadata and identify a safe, testable scope.",
                priority=score_priority(user_impact=3, frequency=2, reliability=4,
                                        performance_gain=0, security_risk=0,
                                        complexity=3, testability=2),
                risk_level="medium", status="review_required", goal_id=None,
                success_criteria=["A maintainer maps the failure to a verified test and allowlisted component."],
                required_tests=["Add or run a focused regression test before code generation."],
            ))
    return out


def candidates_from_issues(issues: list[dict]) -> list[dict]:
    """Issue body/title are intentionally excluded; maintainer labels route work."""
    out = []
    for issue in (issues if isinstance(issues, list) else [])[:MAX_INPUT_RECORDS]:
        if not isinstance(issue, dict):
            continue
        number = issue.get("number")
        url = issue.get("url") or issue.get("html_url")
        expected_url = f"https://github.com/{REPO}/issues/{number}"
        if type(number) is not int or number <= 0 or url != expected_url:
            continue
        labels = []
        for label in issue.get("labels", []) if isinstance(issue.get("labels"), list) else []:
            name = label.get("name") if isinstance(label, dict) else label
            if isinstance(name, str) and name in set(COMPONENT_LABELS) | set(PRIORITY_LABELS) | {"autodev:verified"}:
                labels.append(name)
        component = next((COMPONENT_LABELS[x] for x in labels if x in COMPONENT_LABELS), "unclassified")
        goal_id = COMPONENT_TO_GOAL.get(component) if "autodev:verified" in labels else None
        eligible = goal_id in GOALS_BY_ID
        base_priority = next((PRIORITY_LABELS[x] for x in labels if x in PRIORITY_LABELS), 55)
        if eligible:
            goal = GOALS_BY_ID[goal_id]
            evidence = f"Maintainer-verified issue #{number} is labelled for component {component}; title and body were excluded from model context."
            solution = "Use the existing allowlisted task for this component and validate the reported regression."
            tests = [goal["test_path"]]
            criteria = ["The maintainer-verified issue is covered by a passing focused regression test."]
        else:
            evidence = f"Open issue #{number} was observed; issue content is withheld pending explicit component verification."
            solution = "A maintainer should verify the affected component and provide an allowlisted test target."
            tests = ["Add or run a focused regression test after scope is verified."]
            criteria = ["A maintainer verifies the issue and maps it to an allowlisted component."]
        measured_priority = score_priority(
            user_impact=4 if eligible else 2, frequency=2,
            reliability=5 if eligible else 2, performance_gain=0,
            security_risk=0, complexity=2, testability=4 if eligible else 1,
        )
        issue_priority = round(base_priority * 0.4 + measured_priority * 0.6)
        out.append(_candidate(
            source="github_issue", source_ref=url, evidence=evidence, component=component,
            proposed_solution=solution,
            priority=issue_priority,
            risk_level="medium" if eligible else "low",
            status="eligible" if eligible else "review_required", goal_id=goal_id,
            success_criteria=criteria, required_tests=tests,
        ))
    return out


def candidates_from_app_logs(lines: list[str]) -> list[dict]:
    """Aggregate structured logs by module/exception; discard message/stack."""
    counts: Counter[tuple[str, str]] = Counter()
    for line in (lines if isinstance(lines, list) else [])[:MAX_LOG_RECORDS]:
        if not isinstance(line, str) or len(line) > 64_000:
            continue
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(row, dict) or str(row.get("level", "")).upper() not in {"ERROR", "CRITICAL"}:
            continue
        module = row.get("module") or row.get("logger")
        exception = row.get("exception_type") or row.get("exception")
        if isinstance(exception, dict):
            exception = exception.get("type")
        if not isinstance(module, str) or not SAFE_MODULE.fullmatch(module):
            continue
        if not isinstance(exception, str) or not SAFE_EXCEPTION.fullmatch(exception):
            continue
        counts[(module, exception)] += 1
    out = []
    for (module, exception), count in sorted(counts.items()):
        if count < MIN_APP_ERROR_OCCURRENCES:
            continue
        component = "voice" if "voice" in module or "multimodal" in module else "conversation" if "cognitive" in module else "unclassified"
        goal_id = COMPONENT_TO_GOAL.get(component)
        eligible = goal_id is not None and count >= 5 and module.endswith("voice_runtime")
        goal = GOALS_BY_ID.get(goal_id) if eligible else None
        out.append(_candidate(
            source="application_error_log", source_ref=f"{module}:{exception}",
            evidence=f"Privacy-filtered application error aggregate observed {count} {exception} events in module {module}; log messages and stack data were discarded.",
            component=component, proposed_solution="Inspect the repeated exception using a focused regression and the registered component scope.",
            priority=score_priority(user_impact=3, frequency=4 if count >= 10 else 3,
                                    reliability=4, performance_gain=0, security_risk=0,
                                    complexity=2, testability=4),
            risk_level="medium", status="eligible" if eligible else "review_required",
            goal_id=goal_id if eligible else None,
            success_criteria=["The repeated exception is covered by a passing regression test."],
            required_tests=[goal["test_path"]] if goal else ["Add a focused regression for the observed module error."],
            occurrences=count,
        ))
    return out


def candidates_from_health(report: dict) -> list[dict]:
    if not isinstance(report, dict):
        return []
    rows = report.get("capabilities", report.get("components", []))
    rows = list(rows) if isinstance(rows, list) else []
    # Also accept the existing health.py flat report without copying exception
    # details or database paths into candidate evidence.
    flat_components = {"ollama", "voice_stack", "memory", "semantic_memory", "registry",
                       "planner", "agent", "tts", "vision_llm", "proactive", "wake_word"}
    for name in flat_components:
        state = report.get(name)
        if isinstance(state, str) and (state.lower() in {"unavailable", "offline", "failed", "degraded"}
                                        or state.lower().startswith("error")):
            rows.append({"id": name, "status": state.split(":", 1)[0]})
    databases = report.get("databases")
    if isinstance(databases, dict):
        for name, state in databases.items():
            if isinstance(name, str) and isinstance(state, str) and (state.lower() != "ok"):
                rows.append({"id": "database", "status": "error"})
    out = []
    for row in rows[:MAX_INPUT_RECORDS] if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        component = row.get("id") or row.get("name")
        runtime = row.get("runtime") if isinstance(row.get("runtime"), dict) else {}
        status = str(runtime.get("status") or row.get("status") or "").lower()
        unavailable = runtime.get("available") is False or status in {"error", "unavailable", "offline", "failed", "degraded"}
        if not unavailable or not isinstance(component, str) or not SAFE_MODULE.fullmatch(component):
            continue
        mapped = component if component in COMPONENT_TO_GOAL else "voice" if component in {"tts", "audio", "listening"} else "unclassified"
        out.append(_candidate(
            source="module_health", source_ref=f"component:{component}",
            evidence=f"A supplied module health snapshot marked component {component} unavailable or degraded; raw reason text was excluded.",
            component=mapped, proposed_solution="Reproduce the health failure in a controlled environment and add a focused recovery test.",
            priority=score_priority(user_impact=3, frequency=2, reliability=4,
                                    performance_gain=0, security_risk=0,
                                    complexity=2, testability=3),
            risk_level="medium", status="review_required", goal_id=None,
            success_criteria=["A repeated health check reports the component ready or its limitation is documented."],
            required_tests=["Run the component-specific health and regression checks."],
        ))
    return out


def candidates_from_performance(report: dict) -> list[dict]:
    measurements = report.get("measurements", []) if isinstance(report, dict) else []
    out = []
    for row in measurements[:MAX_INPUT_RECORDS] if isinstance(measurements, list) else []:
        if not isinstance(row, dict):
            continue
        component, metric = row.get("component"), row.get("metric")
        baseline, current, samples = row.get("baseline"), row.get("current"), row.get("samples")
        if (not isinstance(component, str) or not SAFE_MODULE.fullmatch(component)
                or not isinstance(metric, str) or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,50}", metric)
                or isinstance(baseline, bool) or not isinstance(baseline, (int, float)) or baseline <= 0
                or isinstance(current, bool) or not isinstance(current, (int, float)) or current <= 0
                or not math.isfinite(float(baseline)) or not math.isfinite(float(current))
                or isinstance(samples, bool) or not isinstance(samples, int) or samples < MIN_PERFORMANCE_SAMPLES):
            continue
        regression = (current / baseline) - 1
        if not math.isfinite(regression) or regression < PERFORMANCE_REGRESSION_THRESHOLD:
            continue
        percent = round(regression * 100, 1)
        out.append(_candidate(
            source="performance_regression", source_ref=f"{component}:{metric}",
            evidence=f"Measured {metric} regressed {percent}% against baseline over {samples} samples; values are in the supplied benchmark artifact.",
            component=component, proposed_solution="Profile the measured hot path and add a repeatable performance regression test.",
            priority=score_priority(user_impact=3, frequency=4, reliability=3,
                                    performance_gain=5, security_risk=0,
                                    complexity=3, testability=4),
            risk_level="medium", status="review_required", goal_id=None,
            success_criteria=["A repeat benchmark reduces the regression below the configured threshold without failing correctness checks."],
            required_tests=["Run the same benchmark with its declared minimum sample count."],
            measured_regression_percent=percent, sample_count=samples,
        ))
    return out


def candidates_from_roadmap(text: str, filename: str = "ULTRON_NEXT_TASKS.md") -> list[dict]:
    if not isinstance(text, str):
        return []
    if filename not in {"ULTRON_NEXT_TASKS.md", "ULTRON_ROADMAP.md"}:
        raise ValueError("unsupported_roadmap_source")
    # Only the first active section of the continuation file is actionable.
    active = text.split("\n## ", 1)[0][:20_000]
    out = []
    for line_no, line in enumerate(active.splitlines(), start=1):
        match = re.match(r"^\s*[-*]\s+\[ \]\s+(.{1,250})$", line)
        if not match:
            continue
        task = " ".join(match.group(1).split())
        out.append(_candidate(
            source="roadmap_backlog", source_ref=f"{filename}:{line_no}",
            evidence=f"Uncompleted roadmap checklist item: {task}", component="backlog",
            proposed_solution="Prioritize and validate this owner-recorded incomplete task before generation.",
            priority=score_priority(user_impact=2, frequency=1, reliability=2,
                                    performance_gain=0, security_risk=0,
                                    complexity=2, testability=2),
            risk_level="low", status="backlog", goal_id=None,
            success_criteria=["The owner-recorded task has an explicit testable scope and acceptance check."],
            required_tests=["Define focused regression tests before implementation."],
        ))
        if len(out) >= 20:
            break
    return out


def candidates_from_static(report: dict) -> list[dict]:
    issues = report.get("issues", []) if isinstance(report, dict) else []
    out = []
    for issue in issues[:MAX_INPUT_RECORDS] if isinstance(issues, list) else []:
        if not isinstance(issue, dict) or issue.get("severity") not in {"error", "high"}:
            continue
        path = issue.get("file")
        if not isinstance(path, str) or path.startswith(("/", ".")) or ".." in Path(path).parts:
            continue
        goal = GOAL_BY_PATH.get(path)
        kind = issue.get("kind") if issue.get("kind") in {"syntax", "security"} else "verified_static_finding"
        eligible = goal is not None and kind == "syntax" and issue.get("severity") == "error"
        goal_id = goal["id"] if eligible else None
        component = "voice" if eligible and "voice" in goal_id else "conversation" if eligible else "unclassified"
        line = issue.get("line") if isinstance(issue.get("line"), int) and 0 <= issue["line"] < 10_000_000 else 0
        out.append(_candidate(
            source="static_analysis", source_ref=f"{path}:{line}:{kind}",
            evidence=f"Deterministic static analysis reported {issue['severity']} {kind} at repository-relative path {path}, line {line}.",
            component=component, proposed_solution="Reproduce the deterministic finding and add a focused regression before changing code.",
            priority=score_priority(user_impact=4 if eligible else 3, frequency=1,
                                    reliability=5, performance_gain=0,
                                    security_risk=4 if kind == "security" else 0,
                                    complexity=2, testability=5 if eligible else 3),
            risk_level="medium" if eligible else "high" if kind == "security" else "medium",
            status="eligible" if eligible else "review_required", goal_id=goal_id,
            paths=[path], success_criteria=["The deterministic finding is resolved and its focused regression passes."],
            required_tests=[goal["test_path"]] if goal else ["Run the affected module checks and add a regression."],
        ))
    return out


def discover_candidates(*, action_runs: list[dict] | None = None,
                        issues: list[dict] | None = None,
                        app_error_lines: list[str] | None = None,
                        health_report: dict | None = None,
                        performance_report: dict | None = None,
                        static_report: dict | None = None,
                        roadmap_text: str = "",
                        roadmap_sources: dict[str, str] | None = None,
                        open_prs: list[dict] | None = None) -> list[dict]:
    candidates = []
    candidates += candidates_from_actions(action_runs or [])
    candidates += candidates_from_issues(issues or [])
    candidates += candidates_from_app_logs(app_error_lines or [])
    candidates += candidates_from_health(health_report or {})
    candidates += candidates_from_performance(performance_report or {})
    candidates += candidates_from_static(static_report or {})
    candidates += candidates_from_roadmap(roadmap_text, "ULTRON_NEXT_TASKS.md")
    if isinstance(roadmap_sources, dict):
        for filename in ("ULTRON_ROADMAP.md",):
            candidates += candidates_from_roadmap(roadmap_sources.get(filename, ""), filename)
    touched = set()
    for pr in (open_prs if isinstance(open_prs, list) else []):
        for item in pr.get("files", []) if isinstance(pr, dict) and isinstance(pr.get("files", []), list) else []:
            path = item.get("path") if isinstance(item, dict) else item
            if isinstance(path, str):
                touched.add(path.removeprefix("./"))
    dedup: dict[str, dict] = {}
    for row in candidates:
        if set(row.get("affected_files", [])) & touched and row["status"] == "eligible":
            row["status"] = "deferred_conflict"
            row["priority"] = max(0, row["priority"] - 25)
        dedup.setdefault(row["candidate_id"], row)
    return sorted(dedup.values(), key=lambda item: (-item["priority"], item["candidate_id"]))[:MAX_CANDIDATES]


def _gh_json(repo: str, *args: str, timeout: int = 15) -> Any:
    try:
        result = subprocess.run(["gh", *args, "--repo", repo], capture_output=True,
                                text=True, timeout=timeout, check=True)
        value = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise RuntimeError("github_read_failed:" + type(exc).__name__) from None
    return value


def collect_github(repo: str = REPO) -> tuple[list[dict], list[dict], list[dict]]:
    """Read bounded public repository metadata; never fetch Actions log bodies or issue text."""
    runs = _gh_json(repo, "run", "list", "--status", "failure", "--limit", "50",
                    "--json", "databaseId,conclusion,headBranch,headSha")
    issues = _gh_json(repo, "issue", "list", "--state", "open", "--limit", "100",
                      "--json", "number,url,labels")
    open_prs = _gh_json(repo, "pr", "list", "--state", "open", "--limit", "100",
                        "--json", "files")
    if not isinstance(runs, list) or not isinstance(issues, list) or not isinstance(open_prs, list):
        raise RuntimeError("github_read_invalid_shape")
    enriched = []
    for run in runs[:20]:
        if not isinstance(run, dict) or run.get("headBranch") != engine.BASE_BRANCH:
            continue
        run_id = run.get("databaseId")
        if type(run_id) is not int:
            continue
        details = _gh_json(repo, "run", "view", str(run_id), "--json", "jobs")
        enriched.append({**run, "jobs": details.get("jobs", []) if isinstance(details, dict) else []})
    return enriched, issues, open_prs


def _normalize_static_report(raw: dict, root: Path) -> dict:
    normalized = []
    for issue in raw.get("issues", []) if isinstance(raw, dict) else []:
        if not isinstance(issue, dict):
            continue
        value = issue.get("file")
        if not isinstance(value, str) or not value:
            continue
        path = Path(value)
        resolved = (path if path.is_absolute() else root / path).resolve()
        try:
            relative = resolved.relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
        # Keep only the fields needed for candidate classification. CodeIntel
        # messages can include source-derived material and are not persisted.
        normalized.append({
            "severity": issue.get("severity"), "kind": issue.get("kind"),
            "file": relative,
            "line": issue.get("line") if isinstance(issue.get("line"), int) else 0,
        })
    return {"issues": normalized}


def collect_static(root: Path) -> dict:
    backend = (root / "ultron" / "backend").resolve()
    if not backend.is_relative_to(root.resolve()):
        raise RuntimeError("analysis_root_outside_repository")
    sys.path.insert(0, str(backend))
    from app.code_intel.analyzer import CodeIntel
    raw = CodeIntel(str(root)).analyze("ultron/backend")
    return _normalize_static_report(raw, root)


def _read_json(path: Path | None) -> dict:
    if path is None:
        return {}
    if path.is_symlink():
        raise ValueError("input_json_symlink_rejected")
    if path.stat().st_size > 2_000_000:
        raise ValueError("input_json_too_large")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("collect",))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--repo", default="")
    parser.add_argument("--output", type=Path, default=Path("golge-autodev-discovery.json"))
    parser.add_argument("--app-error-jsonl", type=Path)
    parser.add_argument("--health-report", type=Path)
    parser.add_argument("--performance-report", type=Path)
    parser.add_argument("--open-prs", type=Path)
    parser.add_argument("--skip-static", action="store_true")
    parser.add_argument("--skip-roadmap", action="store_true")
    args = parser.parse_args(argv)
    try:
        runs, issues, github_open_prs = collect_github(args.repo) if args.repo else ([], [], [])
        app_lines = []
        if args.app_error_jsonl is not None:
            if args.app_error_jsonl.is_symlink():
                raise ValueError("application_log_symlink_rejected")
            if args.app_error_jsonl.stat().st_size > 4_000_000:
                raise ValueError("application_log_too_large")
            app_lines = args.app_error_jsonl.read_text(encoding="utf-8", errors="replace").splitlines()
        open_prs = json.loads(args.open_prs.read_text(encoding="utf-8")) if args.open_prs else github_open_prs
        static_report = {} if args.skip_static else collect_static(args.root)
        roadmap = ""
        roadmap_sources = {}
        next_tasks = args.root / "ULTRON_NEXT_TASKS.md"
        if not args.skip_roadmap and next_tasks.is_file():
            if next_tasks.is_symlink() or next_tasks.stat().st_size > 1_000_000:
                raise ValueError("next_tasks_source_rejected")
            roadmap = next_tasks.read_text(encoding="utf-8", errors="replace")
        roadmap_file = args.root / "ULTRON_ROADMAP.md"
        if not args.skip_roadmap and roadmap_file.is_file():
            if roadmap_file.is_symlink() or roadmap_file.stat().st_size > 1_000_000:
                raise ValueError("roadmap_source_rejected")
            roadmap_sources["ULTRON_ROADMAP.md"] = roadmap_file.read_text(
                encoding="utf-8", errors="replace"
            )
        candidates = discover_candidates(
            action_runs=runs, issues=issues, app_error_lines=app_lines,
            health_report=_read_json(args.health_report),
            performance_report=_read_json(args.performance_report),
            static_report=static_report, roadmap_text=roadmap,
            roadmap_sources=roadmap_sources, open_prs=open_prs,
        )
        result = {"schema_version": 1, "source_counts": {
            "actions_failures": len(runs), "open_issues": len(issues),
            "open_pull_requests": len(open_prs),
            "application_log_lines": len(app_lines),
            "static_findings": len(static_report.get("issues", [])) if isinstance(static_report, dict) else 0,
            "roadmap_sources": 1 + len(roadmap_sources) if roadmap else len(roadmap_sources),
        }, "candidates": candidates}
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "ok", "candidates": len(candidates),
                          "eligible": sum(row["status"] == "eligible" for row in candidates),
                          "output": str(args.output)}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": type(exc).__name__ + ":" + str(exc)[:120]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
