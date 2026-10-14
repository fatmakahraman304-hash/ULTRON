"""GÖLGE autonomous *proposal* generator.

A scheduled/desktop worker can select a bounded development goal, call a real
coding model and produce a full-file replacement patch. This module never
merges, deploys, authorizes tool execution or edits a live working tree during
generation. Generated Python is executed only in a separate, no-secret CI job.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOALS = Path(__file__).with_name("goals.json")
BASE_BRANCH = "feat/ultron-cloud-shared-memory"
MAX_FILES = 3
MAX_SINGLE_BYTES = 48_000
MAX_TOTAL_BYTES = 84_000
MAX_CONTEXT_CHARS = 18_000
MAX_MODEL_CHARS = 140_000
ALLOWED_ROOTS = (
    "ultron/backend/app/cognitive/",
    "ultron/backend/app/multimodal/",
    "ultron/backend/tests/",
)
FORBIDDEN_NAMES = {
    "__init__.py", "security.py", "auth.py", "executor.py", "runtime.py",
    "codegen.py", "github_pr_publisher.py", "risk.py", "approval.py",
}
CREDENTIALS = re.compile(
    r"(?:-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"
    r"|sk-(?:proj-)?[A-Za-z0-9_-]{16,}"
    r"|github_pat_[A-Za-z0-9_]{15,}"
    r"|gh[pousr]_[A-Za-z0-9_]{20,}"
    r"|AIza[A-Za-z0-9_-]{24,})", re.I,
)


class ProposalError(ValueError):
    pass


def load_goals(path: Path = GOALS) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or data.get("base_branch") != BASE_BRANCH:
        raise ProposalError("invalid_goal_registry")
    goals = data.get("goals")
    if not isinstance(goals, list) or not goals:
        raise ProposalError("empty_goals")
    seen = set()
    for goal in goals:
        if not isinstance(goal, dict) or not re.fullmatch(r"[a-z0-9-]{5,64}", str(goal.get("id", ""))):
            raise ProposalError("invalid_goal_id")
        if goal["id"] in seen:
            raise ProposalError("duplicate_goal_id")
        seen.add(goal["id"])
        if not isinstance(goal.get("goal"), str) or not 30 <= len(goal["goal"]) <= 1300:
            raise ProposalError("invalid_goal_description")
        paths = goal.get("paths")
        if not isinstance(paths, list) or not 2 <= len(paths) <= MAX_FILES:
            raise ProposalError("invalid_goal_paths")
        if len(set(paths)) != len(paths):
            raise ProposalError("duplicate_goal_path")
        if goal.get("test_path") not in paths or not goal["test_path"].startswith("ultron/backend/tests/"):
            raise ProposalError("test_path_required")
        for path in paths:
            validate_path(path, root=ROOT)
    return goals


def validate_path(path: str, *, root: Path = ROOT) -> Path:
    if not isinstance(path, str) or not path or len(path) > 180 or "\\" in path:
        raise ProposalError("invalid_path")
    if path.startswith(("/", ".")) or "//" in path:
        raise ProposalError("invalid_path")
    parts = path.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ProposalError("path_traversal")
    if not path.endswith(".py") or not any(path.startswith(prefix) for prefix in ALLOWED_ROOTS):
        raise ProposalError("path_not_allowlisted")
    if parts[-1].lower() in FORBIDDEN_NAMES or "security" in parts or "auth" in parts:
        raise ProposalError("protected_source")
    repo_root = root.resolve()
    destination = root.joinpath(*parts)
    if destination.is_symlink() or not destination.resolve().is_relative_to(repo_root):
        raise ProposalError("symlink_or_outside_repository")
    return destination


def select_goal(goals: list[dict], open_prs: list[dict]) -> dict | None:
    """One proposed change at a time. Never spawn on top of pending PRs."""
    if not isinstance(open_prs, list):
        raise ProposalError("invalid_pr_list")
    if any("GOLGE-AUTODEV:" in str(row.get("body") or "") for row in open_prs if isinstance(row, dict)):
        return None
    return goals[0] if goals else None


def validate_proposal(proposal: dict, goal: dict, *, root: Path = ROOT) -> list[tuple[str, str]]:
    if not isinstance(proposal, dict) or proposal.get("goal_id") != goal["id"]:
        raise ProposalError("wrong_goal")
    if not isinstance(proposal.get("summary"), str) or len(proposal["summary"]) > 400:
        raise ProposalError("invalid_summary")
    files = proposal.get("files")
    if not isinstance(files, list) or not (2 <= len(files) <= MAX_FILES):
        raise ProposalError("invalid_file_count")
    allowed = set(goal["paths"])
    seen = set()
    total = 0
    changed = []
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"path", "content"}:
            raise ProposalError("invalid_file_entry")
        path, content = entry.get("path"), entry.get("content")
        if path not in allowed or path in seen or not isinstance(content, str):
            raise ProposalError("not_allowed_or_duplicate")
        validate_path(path, root=root)
        encoded = content.encode("utf-8")
        if not encoded or len(encoded) > MAX_SINGLE_BYTES or "\x00" in content:
            raise ProposalError("oversized_or_binary_patch")
        if CREDENTIALS.search(content):
            raise ProposalError("credential_like_content")
        total += len(encoded)
        if total > MAX_TOTAL_BYTES:
            raise ProposalError("total_patch_limit")
        seen.add(path)
        changed.append((path, content))
    if goal["test_path"] not in seen:
        raise ProposalError("missing_regression_test")
    if "def test_" not in dict(changed)[goal["test_path"]]:
        raise ProposalError("test_function_required")
    if not (seen - {goal["test_path"]}):
        raise ProposalError("missing_implementation")
    if not isinstance(proposal.get("base_sha"), str) or not re.fullmatch(r"[0-9a-f]{40}", proposal["base_sha"]):
        raise ProposalError("invalid_base_sha")
    return changed


def plan_goal(base_sha: str, open_prs: list[dict]) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", base_sha):
        raise ProposalError("invalid_base_sha")
    goal = select_goal(load_goals(), open_prs)
    if not goal:
        return {"status": "already_pending", "base_sha": base_sha}
    return {"status": "ready", "base_sha": base_sha, "goal": goal}


def _json_request(url: str, body: dict, headers: dict) -> dict:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url, data=payload,
        headers={**headers, "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            if response.status != 200:
                raise ProposalError("model_http_error")
            raw = response.read(MAX_MODEL_CHARS + 1)
            if len(raw) > MAX_MODEL_CHARS:
                raise ProposalError("model_response_too_large")
            return json.loads(raw)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        # Never log URLs/headers/response bodies which may include credentials.
        raise ProposalError("model_unavailable:" + type(exc).__name__) from None


def infer(prompt: str, provider: str) -> str:
    if provider == "gemini":
        key = os.getenv("GOLGE_AUTODEV_GEMINI_API_KEY", "")
        model = os.getenv("GOLGE_AUTODEV_MODEL", "gemini-2.5-flash")
        if not key:
            raise ProposalError("gemini_key_not_configured")
        if not re.fullmatch(r"[A-Za-z0-9._-]{3,80}", model):
            raise ProposalError("invalid_model")
        result = _json_request(
            "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent",
            {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
             "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}},
            {"x-goog-api-key": key},
        )
        parts = ((result.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        return "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    if provider == "ollama":
        # Local Qwen only. Never accept model-supplied network endpoints.
        model = os.getenv("GOLGE_AUTODEV_OLLAMA_MODEL", "qwen2.5-coder:7b")
        if not re.fullmatch(r"[\w.:/-]{2,80}", model):
            raise ProposalError("invalid_local_model")
        result = _json_request(
            "http://127.0.0.1:11434/api/generate",
            {"model": model, "prompt": prompt, "stream": False, "format": "json",
             "options": {"temperature": 0.1, "num_predict": 6000}},
            {},
        )
        return str(result.get("response") or "")
    raise ProposalError("unsupported_provider")


def generate(plan: dict, provider: str, *, root: Path = ROOT) -> dict:
    if plan.get("status") != "ready":
        raise ProposalError("no_goal_available")
    goal = plan["goal"]
    inputs = []
    for path in goal["paths"]:
        source = validate_path(path, root=root)
        text = source.read_text(encoding="utf-8") if source.exists() else ""
        if len(text) > MAX_CONTEXT_CHARS:
            raise ProposalError("source_too_large_for_safe_context")
        inputs.append({"path": path, "content": text})
    instruction = {
        "task": "Propose a minimal, real, test-backed change to an existing Python project.",
        "goal_id": goal["id"],
        "goal": goal["goal"],
        "source_files": inputs,
        "contract": {
            "only_paths": goal["paths"],
            "full_file_replacements": True,
            "test_file_required": goal["test_path"],
            "format": {"goal_id": goal["id"], "base_sha": plan["base_sha"],
                       "summary": "short summary", "files": [
                           {"path": "exact allowed path", "content": "full file text"}]},
            "never": ["change permissions", "modify security/auth", "merge or deploy",
                      "claim real device/provider testing", "install packages",
                      "execute code", "delete tests", "weaken approval gate"],
        },
    }
    result = infer(json.dumps(instruction, ensure_ascii=False), provider)
    try:
        proposal = json.loads(result)
    except (TypeError, ValueError) as exc:
        raise ProposalError("model_non_json") from exc
    validate_proposal(proposal, goal, root=root)
    # Bind metadata to registry, not to the model's description.
    return proposal


def apply(proposal: dict, *, root: Path = ROOT) -> list[str]:
    goals = load_goals()
    goal = next((g for g in goals if g["id"] == proposal.get("goal_id")), None)
    if goal is None:
        raise ProposalError("unknown_goal")
    changed = validate_proposal(proposal, goal, root=root)
    # Check the checked-out commit matches the generated proposal.
    # Caller must pin checkout to base SHA; no rebase of unreviewed replacements.
    import subprocess
    current = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(root),
        capture_output=True, text=True, timeout=5, check=True,
    ).stdout.strip().lower()
    if current != proposal["base_sha"]:
        raise ProposalError("stale_base_sha")
    for path, content in changed:
        destination = validate_path(path, root=root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    return [path for path, _ in changed]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("plan", "generate", "validate", "apply"))
    parser.add_argument("--base-sha", default="")
    parser.add_argument("--open-prs", type=Path)
    parser.add_argument("--plan-file", type=Path, default=Path("golge-autodev-plan.json"))
    parser.add_argument("--proposal", type=Path, default=Path("golge-autodev-proposal.json"))
    parser.add_argument("--provider", choices=("gemini", "ollama"), default="gemini")
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            open_prs = json.loads(args.open_prs.read_text(encoding="utf-8")) if args.open_prs else []
            plan = plan_goal(args.base_sha, open_prs)
            args.plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
            print("AUTODEV:" + plan["status"])
        elif args.command == "generate":
            plan = json.loads(args.plan_file.read_text(encoding="utf-8"))
            if plan.get("status") != "ready":
                print("AUTODEV:already_pending")
                return 0
            proposal = generate(plan, args.provider)
            args.proposal.write_text(json.dumps(proposal, ensure_ascii=False), encoding="utf-8")
            print("AUTODEV:proposal_generated")
        else:
            proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
            if args.command == "validate":
                goal = next((g for g in load_goals() if g["id"] == proposal.get("goal_id")), None)
                if goal is None:
                    raise ProposalError("unknown_goal")
                paths = [p for p, _ in validate_proposal(proposal, goal)]
                print("AUTODEV:validated:" + ",".join(paths))
            else:
                paths = apply(proposal)
                print("AUTODEV:applied_in_isolated_checkout:" + ",".join(paths))
        return 0
    except (ProposalError, ValueError, OSError, KeyError) as exc:
        print("AUTODEV:FAILED:" + str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
