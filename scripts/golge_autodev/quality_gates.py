"""Honest, bounded quality gate report for isolated generated patches."""
from __future__ import annotations

import ast
from pathlib import Path


def preflight(proposal: dict, goal: dict, *, root: Path, engine_module) -> dict:
    gates = {
        "syntax": {"status": "NOT_RUN"},
        "type_check": {"status": "NOT_RUN", "reason": "no type checker configured in isolated runner"},
        "unit_test": {"status": "PENDING"},
        "integration_test": {"status": "NOT_RUN", "reason": "generated regression only"},
        "dependency_integrity": {"status": "NOT_RUN"},
        "secret_scan": {"status": "NOT_RUN"},
        "security_boundary": {"status": "NOT_RUN"},
        "performance_regression": {"status": "NOT_RUN", "reason": "no benchmark baseline"},
        "api_compatibility": {"status": "NOT_RUN", "reason": "no API contract diff runner"},
        "rollback_readiness": {"status": "NOT_RUN"},
    }
    changed = engine_module.validate_proposal(proposal, goal, root=root)
    for path, content in changed:
        if engine_module.CREDENTIALS.search(content):
            raise engine_module.ProposalError("secret_scan_failed")
        if path.endswith(".py"):
            ast.parse(content, filename=path)
    gates["syntax"] = {"status": "PASS"}
    # Model scope can only contain allowlisted Python application/test files,
    # never package manifests or lockfiles.
    gates["dependency_integrity"] = {"status": "PASS", "reason": "dependency files are outside patch allowlist"}
    gates["secret_scan"] = {"status": "PASS"}
    gates["security_boundary"] = {"status": "PASS"}
    gates["rollback_readiness"] = {"status": "PASS", "reason": "apply is SHA-pinned and runner checkout is disposable"}
    return gates
