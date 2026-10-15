from __future__ import annotations

import sys
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quality_gates


class QualityGateV5Contracts(unittest.TestCase):
    def test_all_required_gates_must_pass_or_be_explicitly_not_applicable(self):
        report = {name: {"status": "PASS"} for name in quality_gates.REQUIRED_GATES}
        report["performance_regression"] = {"status": "NOT_APPLICABLE", "reason": "not performance-sensitive"}
        self.assertTrue(quality_gates.gates_approved(report))

    def test_any_failed_gate_blocks_draft_readiness(self):
        report = {name: {"status": "PASS"} for name in quality_gates.REQUIRED_GATES}
        report["secret_scan"] = {"status": "FAIL", "reason": "fixture"}
        self.assertFalse(quality_gates.gates_approved(report))

    def test_not_run_type_or_performance_gate_blocks_draft_readiness(self):
        report = {name: {"status": "PASS"} for name in quality_gates.REQUIRED_GATES}
        report["type_check"] = {"status": "NOT_RUN"}
        self.assertFalse(quality_gates.gates_approved(report))
        report["type_check"] = {"status": "PASS"}
        report["performance_regression"] = {"status": "NOT_RUN"}
        self.assertFalse(quality_gates.gates_approved(report))

    def test_public_api_signature_changes_are_detected(self):
        before = "def parse_value(value: str, strict: bool = False) -> int:\n    return 1\n"
        compatible = "def parse_value(value: str, strict: bool = False) -> int:\n    return 2\n"
        breaking = "def parse_value(value: str) -> int:\n    return 2\n"
        self.assertEqual(quality_gates.compare_public_api(before, compatible), [])
        self.assertTrue(quality_gates.compare_public_api(before, breaking))

    def test_missing_required_gate_is_not_silently_accepted(self):
        self.assertFalse(quality_gates.gates_approved({"syntax": {"status": "PASS"}}))


    def test_v7_type_check_uses_disposable_sandbox_cache(self):
        with patch.object(quality_gates.importlib.util, "find_spec", return_value=object()), \
             patch.object(quality_gates, "_run", return_value=("PASS", "")) as runner:
            gate = quality_gates._check_python_types(["ultron/backend/app/cognitive/communication.py"],
                                                    root=Path("/tmp/checked-source"))
        self.assertEqual(gate["status"], "PASS")
        command = runner.call_args.args[0]
        self.assertIn("--no-incremental", command)
        self.assertIn("--cache-dir=/tmp/mypy", command)
        self.assertIn("ultron/backend/app/cognitive/communication.py", command)
        self.assertEqual(runner.call_args.kwargs["cwd"], Path("/tmp/checked-source"))

    def test_v7_mypy_crash_and_absent_checker_never_approve(self):
        with patch.object(quality_gates.importlib.util, "find_spec", return_value=object()), \
             patch.object(quality_gates, "_run", return_value=("FAIL", "INTERNAL ERROR")):
            gate = quality_gates._check_python_types(["sample.py"], root=Path("/tmp"))
        self.assertEqual(gate, {"status": "FAIL", "reason": "INTERNAL ERROR"})
        gates = {name: {"status": "PASS"} for name in quality_gates.REQUIRED_GATES}
        gates["type_check"] = gate
        self.assertFalse(quality_gates.gates_approved(gates))
        with patch.object(quality_gates.importlib.util, "find_spec", return_value=None):
            missing = quality_gates._check_python_types(["sample.py"], root=Path("/tmp"))
        self.assertEqual(missing["status"], "NOT_RUN")
        gates["type_check"] = missing
        self.assertFalse(quality_gates.gates_approved(gates))
        self.assertEqual(
            quality_gates._check_python_types(["notes.txt"], root=Path("/tmp"))["status"],
            "NOT_APPLICABLE",
        )

if __name__ == "__main__":
    unittest.main()
