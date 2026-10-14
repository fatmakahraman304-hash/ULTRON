"""Required, independently reported gates for isolated generated patches."""
from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REQUIRED_GATES = (
    "syntax", "type_check", "unit_test", "integration_test", "secret_scan",
    "dependency_integrity", "security_boundary", "api_compatibility",
    "performance_regression", "rollback_readiness",
)
APPROVED_STATUSES = {"PASS", "NOT_APPLICABLE"}


def gates_approved(gates: dict) -> bool:
    """Fail closed for missing, pending, skipped, or unreported required gates."""
    return isinstance(gates, dict) and all(
        isinstance(gates.get(name), dict) and gates[name].get("status") in APPROVED_STATUSES
        for name in REQUIRED_GATES
    )


def _api_symbols(source: str) -> dict[str, str]:
    tree = ast.parse(source or "")
    output: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            output[node.name] = ast.dump(node.args, include_attributes=False) + "->" + ast.dump(node.returns, include_attributes=False) if node.returns else ast.dump(node.args, include_attributes=False)
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            output[node.name] = "class"
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and not child.name.startswith("_"):
                    key = node.name + "." + child.name
                    output[key] = ast.dump(child.args, include_attributes=False) + "->" + ast.dump(child.returns, include_attributes=False) if child.returns else ast.dump(child.args, include_attributes=False)
    return output


def compare_public_api(before: str, after: str) -> list[str]:
    """Return removed or signature-changed public Python callables/classes."""
    old = _api_symbols(before)
    new = _api_symbols(after)
    return sorted(key for key, signature in old.items() if key not in new or new[key] != signature)


def preflight(proposal: dict, goal: dict, *, root: Path, engine_module) -> dict:
    gates: dict[str, dict[str, object]] = {
        name: {"status": "NOT_RUN", "reason": "gate_not_started"} for name in REQUIRED_GATES}
    changed = engine_module.validate_proposal(proposal, goal, root=root)
    for path, content in changed:
        if engine_module.CREDENTIALS.search(content):
            raise engine_module.ProposalError("secret_scan_failed")
        if path.endswith(".py"):
            ast.parse(content, filename=path)
            compile(content, path, "exec")
    gates["syntax"] = {"status": "PASS", "files": len(changed)}
    gates["secret_scan"] = {"status": "PASS", "scanner": "bounded repository credential-pattern scan"}
    # The active proposal allowlist excludes dependency manifests and lockfiles.
    gates["dependency_integrity"] = {
        "status": "PASS", "reason": "dependency files are outside the generated-patch allowlist"}
    gates["security_boundary"] = {"status": "PENDING"}
    gates["unit_test"] = {"status": "PENDING"}
    gates["integration_test"] = {"status": "PENDING"}
    gates["type_check"] = {"status": "PENDING"}
    gates["api_compatibility"] = {"status": "PENDING"}
    gates["performance_regression"] = {"status": "NOT_APPLICABLE",
                                        "reason": "registered task has no production performance baseline"}
    gates["rollback_readiness"] = {"status": "PENDING"}
    return gates


def _safe_test_env(root: Path) -> dict[str, str]:
    env = {key: os.environ[key] for key in
           ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL")
           if key in os.environ}
    backend = str((root / "ultron/backend").resolve())
    env.update({"PYTHONPATH": backend, "PYTHONDONTWRITEBYTECODE": "1",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"})
    return env


def _run(command: list[str], *, cwd: Path, timeout: int = 240) -> tuple[str, str]:
    try:
        from sandbox import SandboxUnavailable, run_sandboxed
        result = run_sandboxed(command, cwd=cwd, env=_safe_test_env(cwd), timeout=timeout)
    except subprocess.TimeoutExpired:
        return "FAIL", "quality_gate_timeout"
    except SandboxUnavailable:
        return "NOT_RUN", "pinned_docker_sandbox_unavailable"
    if result.returncode == 0:
        return "PASS", ""
    diagnostics = ((result.stdout or "") + "\n" + (result.stderr or ""))[-4000:]
    try:
        import engine
        diagnostics = engine.sanitize_diagnostics(diagnostics)
    except ImportError:
        diagnostics = diagnostics[-4000:]
    return "FAIL", diagnostics


def complete_verification(proposal: dict, goal: dict, *, root: Path,
                          engine_module, changed_paths: list[str],
                          original_sources: dict[str, str], unit_status: str) -> dict:
    """Run the mandatory local gate set after a proposal was applied to a disposable checkout."""
    from quality_gates import preflight  # supports direct script and package import

    gates = preflight(proposal, goal, root=root, engine_module=engine_module)
    gates["unit_test"] = {"status": unit_status}

    try:
        has_mypy = importlib.util.find_spec("mypy") is not None
    except (ImportError, ValueError):
        has_mypy = False
    python_files = [path for path in changed_paths if path.endswith(".py")]
    if not has_mypy:
        gates["type_check"] = {"status": "NOT_RUN", "reason": "mypy is not installed in the isolated verifier"}
    elif not python_files:
        gates["type_check"] = {"status": "NOT_APPLICABLE", "reason": "no Python files changed"}
    else:
        command = [sys.executable, "-m", "mypy", "--follow-imports=skip",
                   "--ignore-missing-imports", "--no-error-summary", "--no-incremental", *python_files]
        status, reason = _run(command, cwd=root)
        gates["type_check"] = {"status": status, **({"reason": reason} if reason else {})}

    integration_paths = goal.get("integration_tests", [])
    if not integration_paths:
        gates["integration_test"] = {"status": "NOT_RUN", "reason": "registered integration tests are missing"}
    elif any(not isinstance(path, str) or not path.startswith("ultron/backend/tests/test_")
             or ".." in Path(path).parts or not (root / path).is_file() for path in integration_paths):
        gates["integration_test"] = {"status": "FAIL", "reason": "registered integration test path missing or unsafe"}
    else:
        status, reason = _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               *integration_paths], cwd=root)
        gates["integration_test"] = {"status": status,
                                     "tests": [Path(path).name for path in integration_paths],
                                     **({"reason": reason} if reason else {})}

    # Existing path-boundary and approval/publisher tests run in a clean tools
    # checkout with no provider credentials or GitHub write token.
    tools_root = Path(engine_module.__file__).resolve().parents[2]
    boundary_paths = [tools_root / "ultron/backend/tests/test_codegen_path_boundary.py",
                      tools_root / "ultron/backend/tests/test_github_pr_publisher.py"]
    boundary_paths = [path for path in boundary_paths if path.is_file()]
    if not boundary_paths:
        gates["security_boundary"] = {"status": "NOT_RUN", "reason": "security regression suite unavailable"}
    else:
        command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                   *map(str, boundary_paths)]
        status, reason = _run(command, cwd=tools_root)
        gates["security_boundary"] = {"status": status, "tests": [p.name for p in boundary_paths],
                                      **({"reason": reason} if reason else {})}

    compatibility: list[str] = []
    for path, previous in original_sources.items():
        if "/tests/" in path or not path.endswith(".py"):
            continue
        current = (root / path).read_text(encoding="utf-8") if (root / path).exists() else ""
        compatibility.extend(f"{path}:{symbol}" for symbol in compare_public_api(previous, current))
    gates["api_compatibility"] = ({"status": "FAIL", "reason": "public_signature_changed",
                                   "symbols": compatibility[:30]} if compatibility else {"status": "PASS"})

    # A performance change is acceptable only when its registered task declares
    # a baseline and supplies an independent benchmark test. Otherwise it is
    # explicitly not applicable; it is never reported as a measured pass.
    performance_test = goal.get("performance_test")
    if goal.get("performance_sensitive") is True:
        if not isinstance(performance_test, str) or not performance_test.startswith("ultron/backend/tests/test_"):
            gates["performance_regression"] = {"status": "NOT_RUN", "reason": "performance baseline/test not registered"}
        elif not (root / performance_test).is_file():
            gates["performance_regression"] = {"status": "FAIL", "reason": "registered performance test missing"}
        else:
            status, reason = _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                   performance_test], cwd=root)
            gates["performance_regression"] = {"status": status, "test": Path(performance_test).name,
                                                "measurement": "registered threshold test",
                                                **({"reason": reason} if reason else {})}

    changed_set = set(changed_paths)
    try:
        diff = subprocess.run(["git", "diff", "--check"], cwd=root, env=_safe_test_env(root),
                              capture_output=True, text=True, timeout=10, check=False)
        git_status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                                    cwd=root, env=_safe_test_env(root), capture_output=True, text=True,
                                    timeout=10, check=False)
        actual = set()
        for line in git_status.stdout.splitlines():
            raw = line[3:].strip().split(" -> ")[-1]
            if raw:
                actual.add(raw.replace("\\", "/"))
        allowed = {path.replace("\\", "/") for path in changed_set}
        clean = diff.returncode == 0 and git_status.returncode == 0 and actual <= allowed
    except (OSError, subprocess.TimeoutExpired):
        clean = False
    gates["rollback_readiness"] = ({"status": "PASS", "reason": "SHA-pinned disposable checkout; only allowlisted proposal files changed"}
                                   if clean else {"status": "FAIL", "reason": "rollback_or_scope_check_failed"})
    return gates
