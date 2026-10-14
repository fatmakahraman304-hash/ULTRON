from __future__ import annotations

import sys
import unittest
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


if __name__ == "__main__":
    unittest.main()
