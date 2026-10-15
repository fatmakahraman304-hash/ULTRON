"""Repeatable coding tasks with independent, withheld acceptance oracles.

The default mode never calls a provider and reports NOT_RUN. A live model is
only called when explicitly selected; Gemini additionally requires both the
repository budget approval and a configured positive cost ceiling. Results
from injected/fake providers are intended for harness tests and are labelled
as simulated.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from sandbox import SandboxUnavailable, run_sandboxed

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAX_TASKS = 8
MAX_ATTEMPTS = 2
MAX_PROVIDER_CALLS = MAX_TASKS * MAX_ATTEMPTS
MAX_OUTPUT_TOKENS = 1_400
MAX_PROMPT_CHARS = 20_000
MAX_PATCH_BYTES = 84_000
MAX_FILE_BYTES = 48_000
MAX_TEST_SECONDS = 30
SECRET = re.compile(r"(?:AIza[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{15,}|sk-(?:proj-)?[A-Za-z0-9_-]{16,})", re.I)

CATEGORIES = {
    "python_bugfix", "react_typescript", "multi_file_debugging", "behavior_preserving_refactor",
    "api_integration", "feature_development", "secure_code_change", "performance_improvement",
}

# A provider-side format hint, not a substitute for validate_patch:
# path allowlisting, duplicate detection, secret filtering, and byte limits
# remain mandatory after JSON is returned. This schema is task-independent
# and contains no hidden acceptance tests, source paths, or expected values.
LOCAL_PATCH_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["files"],
    "additionalProperties": False,
}

TASKS = (
    {
        "id": "py-normalize-key", "category": "python_bugfix", "language": "python",
        "prompt": "Fix normalize_key so it trims outer whitespace and performs Unicode-aware case-insensitive normalization. Preserve its name and argument contract.",
        "starter_files": {"solution.py": "def normalize_key(value: str) -> str:\n    return value.strip()\n"},
        "oracle_file": "test_oracle.py",
        "oracle_script": "from solution import normalize_key\n\ndef test_normalization():\n    assert normalize_key('  Straße  ') == 'strasse'\n    assert normalize_key(' İ ') == 'i̇'\n    assert normalize_key('ABC') == 'abc'\n",
    },
    {
        "id": "ts-compact-count", "category": "react_typescript", "language": "typescript",
        "prompt": "Implement formatCompactCount for a React/TypeScript UI. Return the original integer below 1,000; use one decimal and K/M suffixes above that. Preserve sign and reject non-finite numbers with an empty string.",
        "starter_files": {"formatCompactCount.ts": "export function formatCompactCount(value: number): string {\n  return String(value);\n}\n"},
        "oracle_file": "oracle.cjs",
        "oracle_script": "const path = require('path');\nconst mod = require(path.join(process.argv[2], 'formatCompactCount.js'));\nconst f = mod.formatCompactCount;\nconst cases = [[0,'0'],[999,'999'],[1000,'1.0K'],[1250,'1.3K'],[1500000,'1.5M'],[-1250,'-1.3K'],[Infinity,'']];\nfor (const [n, want] of cases) { if (f(n) !== want) throw new Error('oracle mismatch'); }\n",
    },
    {
        "id": "multi-cart-tax", "category": "multi_file_debugging", "language": "python",
        "prompt": "Debug the two-file total calculation. Each line total is unit price multiplied by quantity before tax is applied once. Keep total_for_cart(cart, tax_rate) and make no unrelated changes.",
        "starter_files": {
            "cart.py": "from pricing import taxed\n\ndef total_for_cart(cart, tax_rate):\n    return sum(taxed(item['price'], tax_rate) for item in cart)\n",
            "pricing.py": "def taxed(amount, rate):\n    return amount * (1 + rate)\n",
        },
        "oracle_file": "test_oracle.py",
        "oracle_script": "from cart import total_for_cart\n\ndef test_quantity_is_included_before_tax():\n    assert total_for_cart([{'price': 10, 'quantity': 2}, {'price': 20, 'quantity': 3}], 0.1) == 88\n    assert total_for_cart([], 0.25) == 0\n",
    },
    {
        "id": "refactor-first-delimiter", "category": "behavior_preserving_refactor", "language": "python",
        "prompt": "Refactor parse_pair without changing its public signature. Split on the first colon only, trim both sides, and reject missing/empty sides with ValueError.",
        "starter_files": {"solution.py": "def parse_pair(value: str) -> tuple[str, str]:\n    left, right = value.split(':')\n    return left, right\n"},
        "oracle_file": "test_oracle.py",
        "oracle_script": "import pytest\nfrom solution import parse_pair\n\ndef test_compatibility_matrix():\n    assert parse_pair(' alpha : beta ') == ('alpha', 'beta')\n    assert parse_pair('url:https://host/path') == ('url', 'https://host/path')\n    for bad in ('', ':x', 'x:', 'x'):\n        with pytest.raises(ValueError): parse_pair(bad)\n",
    },
    {
        "id": "api-profile-client", "category": "api_integration", "language": "python",
        "prompt": "Implement load_profile(client, user_id) using the supplied HTTP-like client. URL-encode user_id as one path segment, GET /profiles/{id}, raise HTTP errors, and return response.json()['profile']; do not make real network calls.",
        "starter_files": {"solution.py": "def load_profile(client, user_id):\n    return None\n"},
        "oracle_file": "test_oracle.py",
        "oracle_script": "from urllib.parse import quote\nfrom solution import load_profile\n\nclass Response:\n    def __init__(self, data): self.data=data; self.raised=False\n    def raise_for_status(self): self.raised=True\n    def json(self): return self.data\nclass Client:\n    def __init__(self): self.calls=[]; self.response=Response({'profile': {'id':'a/b'}})\n    def get(self, path): self.calls.append(path); return self.response\n\ndef test_client_contract():\n    client=Client(); result=load_profile(client,'a/b')\n    assert result == {'id':'a/b'}\n    assert client.calls == ['/profiles/' + quote('a/b', safe='')]\n    assert client.response.raised\n",
    },
    {
        "id": "cursor-pagination", "category": "feature_development", "language": "python",
        "prompt": "Implement page_items(items, offset, limit) returning a dict with items, next_offset and has_more. Reject negative offset and non-positive limit. Do not mutate the input.",
        "starter_files": {"solution.py": "def page_items(items, offset, limit):\n    return {'items': [], 'next_offset': None, 'has_more': False}\n"},
        "oracle_file": "test_oracle.py",
        "oracle_script": "import pytest\nfrom solution import page_items\n\ndef test_pages_and_validation():\n    data=[0,1,2,3,4]\n    assert page_items(data, 1, 2) == {'items':[1,2], 'next_offset':3, 'has_more':True}\n    assert page_items(data, 4, 2) == {'items':[4], 'next_offset':None, 'has_more':False}\n    assert page_items(data, 5, 2) == {'items':[], 'next_offset':None, 'has_more':False}\n    assert data == [0,1,2,3,4]\n    for args in ((data,-1,2),(data,0,0)):\n        with pytest.raises(ValueError): page_items(*args)\n",
    },
    {
        "id": "safe-asset-path", "category": "secure_code_change", "language": "python",
        "prompt": "Implement resolve_asset(root, name) to return a resolved path inside root. Reject absolute paths, traversal, and symlinks that escape root. This helper must not read or write files.",
        "starter_files": {"solution.py": "from pathlib import Path\n\ndef resolve_asset(root, name):\n    return Path(root) / name\n"},
        "oracle_file": "test_oracle.py",
        "oracle_script": "from pathlib import Path\nimport pytest\nfrom solution import resolve_asset\n\ndef test_confines_paths(tmp_path):\n    root=tmp_path/'assets'; root.mkdir()\n    assert resolve_asset(root,'icons/a.svg') == root/'icons/a.svg'\n    for name in ('../secret', str(tmp_path/'outside')):\n        with pytest.raises((ValueError, PermissionError)): resolve_asset(root,name)\n    outside=tmp_path/'outside'; outside.mkdir(); (outside/'secret').write_text('x')\n    (root/'escape').symlink_to(outside, target_is_directory=True)\n    with pytest.raises((ValueError, PermissionError)): resolve_asset(root,'escape/secret')\n",
    },
    {
        "id": "linear-stable-unique", "category": "performance_improvement", "language": "python",
        "prompt": "Implement unique_allowed(values, allowed) in O(n+m), preserving input order and returning each allowed identifier once. Do not mutate either iterable.",
        "starter_files": {"solution.py": "def unique_allowed(values, allowed):\n    return [value for value in values if value in allowed]\n"},
        "oracle_file": "test_oracle.py",
        "oracle_script": "from solution import unique_allowed\n\nclass Counted(list):\n    def __init__(self, values): super().__init__(values); self.comparisons=0\n    def __contains__(self, value):\n        for candidate in self:\n            self.comparisons += 1\n            if candidate == value: return True\n        return False\n\ndef test_order_uniqueness_and_linear_membership():\n    values=[x % 2000 for x in range(8000)]\n    allowed=Counted(list(range(1000,2000)))\n    result=unique_allowed(values,allowed)\n    assert result == list(range(1000,2000))\n    assert allowed.comparisons <= 2 * len(values)\n",
    },
)


class BenchmarkError(ValueError):
    pass


def _public_candidate_delta(task: dict, current_files: dict[str, str]) -> str:
    """Bounded starter-to-candidate diff; never inspect acceptance-oracle fields."""
    original_files = task["starter_files"]
    sections: list[str] = []
    remaining = 2_800
    for path, candidate in sorted(current_files.items()):
        original = original_files.get(path)
        if original is None or original == candidate:
            continue
        delta = difflib.unified_diff(
            original.splitlines(), candidate.splitlines(),
            fromfile=f"starter/{path}", tofile=f"candidate/{path}", lineterm=""
        )
        for line in delta:
            if remaining <= 0:
                break
            sections.append(line[:remaining])
            remaining -= len(line) + 1
        if remaining <= 0:
            break
    if not sections:
        return "Candidate has no source changes relative to the original starter."
    return "\n".join(sections)[:2_800]


def build_prompt(task: dict, *, current_files: dict[str, str] | None = None,
                 diagnostics: str = "", repair_mode: bool = False) -> str:
    """Render only task statement and working files, never the oracle fields."""
    files = current_files or task["starter_files"]
    payload = {"task": task["prompt"],
               "working_files": [{"path": path, "content": content}
                                 for path, content in sorted(files.items())],
               "output_contract": {"summary": "short explanation",
                                   "files": [{"path": "exact allowed path", "content": "complete file"}]}}
    payload["coding_rules"] = [
        "Return one complete valid JSON object, with no Markdown or extra text.",
        "Include the complete updated source for every working_files path, using exact paths.",
        "Preserve public APIs and check empty, invalid, boundary, and numeric edge cases.",
        "When validating paths or identifiers, distinguish raw inputs from derived values.",
        "Keep security boundaries and unrelated behavior intact; avoid speculative changes.",
    ]
    if diagnostics:
        safe = _sanitize(diagnostics)
        payload["public_repair_feedback"] = safe
    if repair_mode:
        # This context uses only the published starter and previous generated
        # source. No private test assertion, expected value, or stdout is read.
        payload["public_candidate_vs_starter_diff"] = _public_candidate_delta(task, files)
        payload["repair_rules"] = [
            "The previous candidate failed behavioral verification. Re-examine "
            "each requirement in task against the current working_files.",
            "Find a plausible semantic gap using only task and working_files; "
            "do not assume private test inputs or expected outputs.",
            "Produce a genuine behavior-changing correction, not identical "
            "code, formatting, or comments. Preserve the required public API.",
            "Return complete source for all paths as the specified JSON object.",
        ]
    prompt = json.dumps(payload, ensure_ascii=False)
    if len(prompt) > MAX_PROMPT_CHARS:
        raise BenchmarkError("prompt_too_large")
    return prompt


def validate_patch(task: dict, patch: dict) -> list[tuple[str, str]]:
    if not isinstance(patch, dict) or not isinstance(patch.get("files"), list):
        raise BenchmarkError("model_response_invalid")
    allowed = set(task["starter_files"])
    changed = []
    seen = set()
    total = 0
    for item in patch["files"]:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise BenchmarkError("model_file_invalid")
        path = item["path"]
        parts = Path(path).parts
        if path not in allowed or Path(path).is_absolute() or any(part in {".", ".."} for part in parts) or "\\" in path:
            raise BenchmarkError("model_path_outside_task")
        if path in seen:
            raise BenchmarkError("model_duplicate_path")
        content = item.get("content")
        if not isinstance(content, str) or SECRET.search(content):
            raise BenchmarkError("model_content_rejected")
        size = len(content.encode("utf-8"))
        if size > MAX_FILE_BYTES:
            raise BenchmarkError("model_file_too_large")
        total += size
        if total > MAX_PATCH_BYTES:
            raise BenchmarkError("model_patch_too_large")
        seen.add(path)
        changed.append((path, content))
    if seen != allowed:
        raise BenchmarkError("model_patch_incomplete")
    return changed


def _sanitize(value: str) -> str:
    value = SECRET.sub("[REDACTED]", str(value or ""))
    value = re.sub(r"(?i)(authorization\s*[:=]\s*bearer\s+)\S+", r"\1[REDACTED]", value)
    return value[-4_000:]


def _public_signatures(source: str) -> dict[str, str]:
    """Public callable contracts extracted solely from the supplied source."""
    tree = ast.parse(source)
    return {
        node.name: ast.dump(node.args, include_attributes=False)
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_")
    }


def _public_repair_feedback(task: dict, current_files: dict[str, str]) -> str:
    """Give source-grounded hints, never raw withheld acceptance output."""
    messages = [
        "The candidate failed independent behavioral verification; exact private assertions are withheld.",
        "Recheck each requirement in the public task against your implementation, including",
        "data representation, boundary inputs, error paths, and return contracts.",
    ]
    for path, content in sorted(current_files.items()):
        if not path.endswith(".py"):
            continue
        try:
            ast.parse(content, filename=path)
        except SyntaxError as exc:
            messages.append(
                f"Candidate syntax error in {path}, line {exc.lineno}, column {exc.offset or 0}."
            )
            continue
        baseline = task["starter_files"].get(path, "")
        try:
            old = _public_signatures(baseline)
            new = _public_signatures(content)
        except SyntaxError:
            continue
        for name, signature in sorted(old.items()):
            if new.get(name) != signature:
                messages.append(f"Candidate changes the original public signature: {path}:{name}.")
    return _sanitize("\n".join(messages))[:4000]


def _same_python_structure(current_files: dict[str, str],
                           changed: list[tuple[str, str]]) -> bool:
    """Skip an oracle rerun after edits that change only Python trivia."""
    if not changed or any(not path.endswith(".py") for path, _ in changed):
        return False
    try:
        return all(
            ast.dump(ast.parse(current_files[path]), include_attributes=False)
            == ast.dump(ast.parse(content), include_attributes=False)
            for path, content in changed
        )
    except (KeyError, SyntaxError, ValueError):
        return False


def _decode_patch(response: str) -> dict:
    text = str(response or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BenchmarkError("model_json_invalid") from exc
    if not isinstance(result, dict):
        raise BenchmarkError("model_response_invalid")
    return result


def _test_environment(workspace: Path) -> dict[str, str]:
    # Generated code receives no API keys, Actions token, or user environment.
    keep = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL") if key in os.environ}
    keep.update({"PYTHONPATH": str(workspace), "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"})
    return keep


def _run_oracle(task: dict, workspace: Path, oracle_dir: Path,
                *, typescript_bin: Path | None, node_bin: str) -> tuple[bool, str, int]:
    oracle = oracle_dir / task["oracle_file"]
    oracle.parent.mkdir(parents=True, exist_ok=True)
    oracle.write_text(task["oracle_script"], encoding="utf-8")
    started = time.perf_counter()
    env = _test_environment(workspace)
    if task["language"] == "python":
        cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(oracle)]
        try:
            result = run_sandboxed(cmd, cwd=workspace, env=env, timeout=MAX_TEST_SECONDS,
                                   readonly_paths=(oracle_dir,))
        except subprocess.TimeoutExpired:
            return False, "oracle_timeout", int((time.perf_counter() - started) * 1000)
        except SandboxUnavailable:
            return False, "sandbox_unavailable", int((time.perf_counter() - started) * 1000)
        return result.returncode == 0, _sanitize((result.stdout or "") + "\n" + (result.stderr or "")), int((time.perf_counter() - started) * 1000)
    if task["language"] == "typescript":
        node_executable = shutil.which(node_bin)
        if not typescript_bin or not typescript_bin.is_file() or not node_executable:
            return False, "typescript_toolchain_unavailable", int((time.perf_counter() - started) * 1000)
        source = workspace / next(iter(task["starter_files"]))
        output = workspace / ".bench-build"
        compile_cmd = [str(Path(node_executable).resolve()), str(typescript_bin.resolve()),
                       "--strict", "--target", "ES2022", "--module", "commonjs",
                       "--moduleResolution", "node", "--outDir", str(output), str(source)]
        node_path = Path(node_executable).resolve()
        readonly_paths = [oracle_dir, typescript_bin.parent.parent, node_path.parent]
        try:
            compiled = run_sandboxed(compile_cmd, cwd=workspace, env=env,
                                     timeout=MAX_TEST_SECONDS, writable_cwd=True,
                                     readonly_paths=tuple(readonly_paths))
            if compiled.returncode != 0:
                return False, _sanitize(compiled.stdout + "\n" + compiled.stderr), int((time.perf_counter() - started) * 1000)
            executed = run_sandboxed([str(node_path), str(oracle), str(output)], cwd=workspace, env=env,
                                     timeout=MAX_TEST_SECONDS, readonly_paths=tuple(readonly_paths))
        except subprocess.TimeoutExpired:
            return False, "oracle_timeout", int((time.perf_counter() - started) * 1000)
        except SandboxUnavailable:
            return False, "sandbox_unavailable", int((time.perf_counter() - started) * 1000)
        return executed.returncode == 0, _sanitize(executed.stdout + "\n" + executed.stderr), int((time.perf_counter() - started) * 1000)
    return False, "unsupported_task_language", int((time.perf_counter() - started) * 1000)


def _provider_guard(provider: str, *, cloud_budget_confirmed: bool) -> str | None:
    if provider == "gemini":
        if not cloud_budget_confirmed or os.getenv("GOLGE_AUTODEV_CLOUD_MODEL_BUDGET_APPROVED") != "true":
            return "cloud_budget_not_explicitly_approved"
        ceiling = os.getenv("GOLGE_AUTODEV_MAX_COST_USD", "")
        try:
            if not 0 < float(ceiling) <= 100:
                return "cloud_cost_ceiling_missing_or_invalid"
        except ValueError:
            return "cloud_cost_ceiling_missing_or_invalid"
        if not os.getenv("GOLGE_AUTODEV_GEMINI_API_KEY"):
            return "gemini_key_not_configured"
    if provider not in {"gemini", "ollama"}:
        return "unsupported_provider"
    return None


def _local_patch_format() -> str:
    """Conservative default; strict schema is an explicit comparison mode."""
    option = os.getenv("GOLGE_AUTODEV_OLLAMA_PATCH_FORMAT", "json").strip().lower()
    if option not in {"json", "schema"}:
        raise BenchmarkError("invalid_local_patch_format")
    return option


def infer_with_budget(prompt: str, provider: str) -> str:
    # Use exactly the same public coding prompt, oracle protection, limits,
    # and model for both modes. The provider-side JSON Schema is experimental:
    # a valid-shaped response is not evidence of correct program behavior.
    import engine
    if provider == "ollama" and _local_patch_format() == "schema":
        return engine.infer(prompt, provider, max_output_tokens=MAX_OUTPUT_TOKENS,
                            response_schema=LOCAL_PATCH_RESPONSE_SCHEMA)
    return engine.infer(prompt, provider, max_output_tokens=MAX_OUTPUT_TOKENS)


def run_task(task: dict, *, provider: str, infer_fn: Callable[[str, str], str] | None = None,
             max_attempts: int = MAX_ATTEMPTS, typescript_bin: Path | None = None,
             node_bin: str = "node") -> dict:
    infer_fn = infer_fn or infer_with_budget
    start = time.perf_counter()
    model_ms = 0
    test_ms = 0
    calls = 0
    with tempfile.TemporaryDirectory(prefix="golge-bench-task-") as task_tmp, \
         tempfile.TemporaryDirectory(prefix="golge-bench-oracle-") as oracle_tmp:
        workspace = Path(task_tmp)
        oracle_dir = Path(oracle_tmp)
        current = dict(task["starter_files"])
        for rel, content in current.items():
            target = workspace / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        baseline_ok, baseline_diag, baseline_ms = _run_oracle(
            task, workspace, oracle_dir, typescript_bin=typescript_bin, node_bin=node_bin)
        test_ms += baseline_ms
        if baseline_ok:
            return {"id": task["id"], "category": task["category"], "status": "INVALID_BASELINE",
                    "attempts": 0, "provider_calls": 0, "elapsed_ms": int((time.perf_counter()-start)*1000),
                    "model_ms": 0, "test_ms": test_ms, "reason": "oracle_did_not_reproduce_starter_defect"}
        if baseline_diag in {"typescript_toolchain_unavailable", "sandbox_unavailable"}:
            return {"id": task["id"], "category": task["category"], "status": "NOT_RUN",
                    "attempts": 0, "provider_calls": 0, "elapsed_ms": int((time.perf_counter()-start)*1000),
                    "model_ms": 0, "test_ms": test_ms, "reason": baseline_diag}
        last_diagnostics = ""
        previous_test_failed = False
        for attempt in range(1, max_attempts + 1):
            prompt = build_prompt(task, current_files=current, diagnostics=last_diagnostics,
                                  repair_mode=previous_test_failed)
            model_started = time.perf_counter()
            calls += 1
            try:
                raw = infer_fn(prompt, provider)
            except Exception as exc:
                reason = re.sub(r"[^A-Za-z0-9_:-]", "_", type(exc).__name__)[:80]
                return {"id": task["id"], "category": task["category"], "status": "NOT_RUN",
                        "attempts": attempt, "provider_calls": calls,
                        "elapsed_ms": int((time.perf_counter()-start)*1000),
                        "model_ms": int(model_ms + (time.perf_counter()-model_started)*1000),
                        "test_ms": test_ms, "reason": "provider_unavailable:" + reason}
            model_ms += int((time.perf_counter() - model_started) * 1000)
            try:
                patch = _decode_patch(raw)
                changed = validate_patch(task, patch)
                # A repeated failed patch cannot fix an observed test failure.
                # Stop rather than spending another sandbox run on identical code.
                unchanged_reason = None
                if previous_test_failed:
                    if all(current[path] == content for path, content in changed):
                        unchanged_reason = "unchanged_patch_after_repair"
                    elif _same_python_structure(current, changed):
                        unchanged_reason = "structurally_unchanged_patch_after_repair"
                if unchanged_reason:
                    return {"id": task["id"], "category": task["category"], "status": "FAIL",
                            "attempts": attempt, "provider_calls": calls,
                            "elapsed_ms": int((time.perf_counter()-start)*1000),
                            "model_ms": model_ms, "test_ms": test_ms,
                            "reason": unchanged_reason}
                current = dict(current)
                for path, content in changed:
                    current[path] = content
                    (workspace / path).write_text(content, encoding="utf-8")
            except BenchmarkError as exc:
                reason = str(exc)
                # Only shape/format mistakes may be retried. Unsafe paths,
                # secret-like content, oversized files, and duplicate paths
                # remain fail-closed without a second provider call.
                recoverable = {"model_json_invalid", "model_response_invalid",
                               "model_patch_incomplete"}
                if attempt < max_attempts and reason in recoverable:
                    last_diagnostics = (
                        "Previous response rejected: " + reason + ". "
                        "Return exactly one valid JSON object with a files array, "
                        "containing complete source for each original path; "
                        "no additional paths, no Markdown."
                    )
                    continue
                return {"id": task["id"], "category": task["category"], "status": "BLOCKED",
                        "attempts": attempt, "provider_calls": calls,
                        "elapsed_ms": int((time.perf_counter()-start)*1000), "model_ms": model_ms,
                        "test_ms": test_ms, "reason": reason}
            passed, diagnostics, elapsed = _run_oracle(
                task, workspace, oracle_dir, typescript_bin=typescript_bin, node_bin=node_bin)
            test_ms += elapsed
            if passed:
                return {"id": task["id"], "category": task["category"], "status": "PASS",
                        "attempts": attempt, "provider_calls": calls,
                        "elapsed_ms": int((time.perf_counter()-start)*1000),
                        "model_ms": model_ms, "test_ms": test_ms}
            # The withheld oracle's stdout/stderr can contain assertion source,
            # expected values and private fixtures. It must not reach a model
            # or the benchmark report, even after regex secret redaction.
            last_diagnostics = _public_repair_feedback(task, current)
            previous_test_failed = True
        return {"id": task["id"], "category": task["category"], "status": "FAIL",
                "attempts": max_attempts, "provider_calls": calls,
                "elapsed_ms": int((time.perf_counter()-start)*1000),
                "model_ms": model_ms, "test_ms": test_ms,
                "reason": "independent_oracle_failed_after_bounded_repair",
                "repair_feedback": _sanitize(last_diagnostics)}


def run_benchmark(*, provider: str | None, max_cases: int = MAX_TASKS,
                  max_calls: int = 0, cloud_budget_confirmed: bool = False,
                  infer_fn: Callable[[str, str], str] | None = None,
                  typescript_bin: Path | None = None, node_bin: str = "node") -> dict:
    if type(max_cases) is not int or not 1 <= max_cases <= MAX_TASKS:
        raise BenchmarkError("invalid_case_limit")
    selected = list(TASKS[:max_cases])
    guard = _provider_guard(provider, cloud_budget_confirmed=cloud_budget_confirmed) if provider else "provider_not_requested"
    local_patch_format = None
    if provider == "ollama":
        try:
            local_patch_format = _local_patch_format()
        except BenchmarkError:
            guard = "invalid_local_patch_format"
    if provider and (type(max_calls) is not int or not 1 <= max_calls <= min(MAX_PROVIDER_CALLS, max_cases * MAX_ATTEMPTS)):
        guard = "explicit_provider_call_limit_required"
    if guard:
        state = "BLOCKED" if provider else "NOT_RUN"
        tasks = [{"id": task["id"], "category": task["category"], "status": state,
                  "attempts": 0, "provider_calls": 0, "elapsed_ms": 0, "reason": guard}
                 for task in selected]
    else:
        tasks = []
        used_calls = 0
        for task in selected:
            if task["language"] == "typescript" and (not typescript_bin or not typescript_bin.is_file()):
                tasks.append({"id": task["id"], "category": task["category"], "status": "NOT_RUN",
                              "attempts": 0, "provider_calls": 0, "elapsed_ms": 0,
                              "reason": "typescript_toolchain_unavailable"})
                continue
            remaining = max_calls - used_calls
            if remaining <= 0:
                tasks.append({"id": task["id"], "category": task["category"], "status": "NOT_RUN",
                              "attempts": 0, "provider_calls": 0, "elapsed_ms": 0,
                              "reason": "provider_call_budget_exhausted"})
                continue
            result = run_task(task, provider=provider or "", infer_fn=infer_fn,
                              max_attempts=min(MAX_ATTEMPTS, remaining),
                              typescript_bin=typescript_bin, node_bin=node_bin)
            used_calls += result["provider_calls"]
            tasks.append(result)
            if result["status"] == "NOT_RUN" and str(result.get("reason", "")).startswith("provider_unavailable:"):
                for pending in selected[len(tasks):]:
                    tasks.append({"id": pending["id"], "category": pending["category"],
                                  "status": "NOT_RUN", "attempts": 0, "provider_calls": 0,
                                  "elapsed_ms": 0, "reason": "provider_unavailable_after_first_probe"})
                break
    counts = {state.lower(): sum(row["status"] == state for row in tasks)
              for state in ("PASS", "FAIL", "NOT_RUN", "BLOCKED", "INVALID_BASELINE")}
    scored = counts["pass"] + counts["fail"]
    provider_call_total = 0
    for row in tasks:
        value = row.get("provider_calls", 0)
        if isinstance(value, int):
            provider_call_total += value
    return {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
            "provider": provider or None,
            "model_status": ("NOT_RUN" if provider is None else
                             "BLOCKED" if guard or not provider_call_total else "ATTEMPTED"),
            "simulated": infer_fn is not None,
            "ollama_patch_format": local_patch_format,
            # Keep the historical pass/(PASS+FAIL) score for compatibility, but
            # report full-suite success separately so BLOCKED cases cannot
            # make an eight-task run appear better than six successes out of eight.
            "score": counts["pass"] / scored if scored else None,
            "score_denominator": scored,
            "suite_pass_rate": counts["pass"] / len(selected) if provider_call_total else None,
            "suite_denominator": len(selected),
            "summary": counts, "tasks": tasks,
            "limits": {"max_tasks": max_cases, "max_attempts_per_task": MAX_ATTEMPTS,
                       "max_provider_calls": max_calls, "max_output_tokens_per_call": MAX_OUTPUT_TOKENS}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("gemini", "ollama"), default=None)
    parser.add_argument("--max-cases", type=int, default=MAX_TASKS)
    parser.add_argument("--max-calls", type=int, default=0,
                        help="Required explicit total provider-call ceiling; repairs share this budget.")
    parser.add_argument("--confirm-cloud-budget", action="store_true")
    parser.add_argument("--typescript-bin", type=Path,
                        default=ROOT / "ultron/frontend/node_modules/.bin/tsc")
    parser.add_argument("--node-bin", default="node")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = run_benchmark(provider=args.provider, max_cases=args.max_cases, max_calls=args.max_calls,
                           cloud_budget_confirmed=args.confirm_cloud_budget,
                           typescript_bin=args.typescript_bin, node_bin=args.node_bin)
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        if args.output.is_symlink():
            raise SystemExit("output_symlink_rejected")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0 if report["model_status"] in {"NOT_RUN", "BLOCKED", "ATTEMPTED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
