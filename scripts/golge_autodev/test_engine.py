"""Zero-provider tests for the GÖLGE autonomous draft patch boundary."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine

SHA = "a" * 40


class AutonomousPatchContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "ultron/backend/app/cognitive").mkdir(parents=True)
        (self.root / "ultron/backend/tests").mkdir(parents=True)
        self.code_path = "ultron/backend/app/cognitive/communication.py"
        self.test_path = "ultron/backend/tests/test_autodev_communication.py"
        self.goal = {
            "id": "dialogue-continuity-contract",
            "goal": "Improve interruption handling while preserving all existing owner and device security boundaries",
            "paths": [self.code_path, self.test_path],
            "test_path": self.test_path,
        }
        self.proposal = {
            "goal_id": self.goal["id"], "base_sha": SHA,
            "summary": "Add bounded interruption regression coverage",
            "attempt": 1,
            "files": [
                {"path": self.code_path, "content": "def safe():\n    return True\n"},
                {"path": self.test_path, "content": "from app.cognitive.communication import safe\n\ndef test_safe():\n    assert safe() is True\n"},
            ],
        }

    def test_goal_registry_is_valid(self):
        goals = engine.load_goals()
        self.assertGreaterEqual(len(goals), 2)
        self.assertEqual(goals[0]["id"], "voice-interrupt-contract")

    def test_stop_when_a_prior_autodev_pr_is_open(self):
        self.assertIsNone(engine.select_goal([self.goal], [
            {"body": "GOLGE-AUTODEV:voice-interrupt-contract"}
        ]))
        self.assertEqual(engine.select_goal([self.goal], [])[ "id"], self.goal["id"])

    def test_priority_selection_skips_paths_owned_by_another_open_pr(self):
        goals = engine.load_goals()
        selected = engine.select_goal(goals, [{
            "title": "True interruption V1",
            "files": [{"path": "ultron/backend/app/multimodal/voice_runtime.py"}],
        }])
        self.assertEqual(selected["id"], "dialogue-continuity-contract")

    def test_plan_records_evidence_risk_scope_and_success_criteria(self):
        result = engine.plan_goal(SHA, [])
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["task"]["risk_level"], "medium")
        self.assertTrue(result["task"]["problem_evidence"])
        self.assertTrue(result["task"]["affected_files"])
        self.assertTrue(result["task"]["test_scope"])
        self.assertTrue(result["task"]["success_criteria"])

    def test_completed_goal_is_skipped_for_next_queued_goal(self):
        goals = engine.load_goals()
        completed = [{"title": "GÖLGE autonomous: voice-interrupt-contract", "body": ""}]
        goal = engine.select_goal(goals, [], completed)
        self.assertIsNotNone(goal)
        self.assertEqual(goal["id"], "dialogue-continuity-contract")
        self.assertIsNone(engine.select_goal(goals, [], [
            {"body": "GOLGE-AUTODEV:voice-interrupt-contract"},
            {"body": "GOLGE-AUTODEV:dialogue-continuity-contract"},
        ]))

    def test_generate_uses_a_fake_model_then_proves_bounded_patch(self):
        source = self.root / self.code_path
        source.write_text("def safe():\n    return False\n", encoding="utf-8")
        plan = {"status": "ready", "base_sha": SHA, "goal": self.goal}
        model_patch = {
            "summary": self.proposal["summary"],
            "files": [
                {"path": "app/cognitive/communication.py", "content": self.proposal["files"][0]["content"]},
                {"path": "tests/test_autodev_communication.py", "content": self.proposal["files"][1]["content"]},
            ],
        }
        with patch.object(engine, "infer", return_value=json.dumps(model_patch)) as fake:
            result = engine.generate(plan, "ollama", root=self.root)
        self.assertEqual(result["goal_id"], self.goal["id"])
        self.assertTrue(fake.called)
        self.assertEqual(source.read_text(encoding="utf-8"), "def safe():\n    return False\n")
        self.assertEqual(result["attempt"], 1)
        prompt = json.loads(fake.call_args.args[0])
        self.assertIn("app/cognitive/communication.py", prompt["user"])
        self.assertNotIn("server.py", prompt["user"])

    def test_valid_patch_can_apply_only_on_pinned_commit(self):
        with patch("subprocess.run") as run:
            run.return_value.stdout = SHA + "\n"
            paths = engine.apply(self.proposal, root=self.root)
        self.assertEqual(set(paths), set(self.goal["paths"]))
        self.assertIn("def safe():", (self.root / self.code_path).read_text(encoding="utf-8"))

    def test_valid_patch_and_explicit_test_requirement(self):
        paths = engine.validate_proposal(self.proposal, self.goal, root=self.root)
        self.assertEqual(len(paths), 2)
        self.proposal["files"].pop()
        with self.assertRaisesRegex(engine.ProposalError, "invalid_file_count"):
            engine.validate_proposal(self.proposal, self.goal, root=self.root)

    def test_block_unlisted_paths_and_protected_core(self):
        for bad in (
            "../../secrets.py", "/etc/shadow", "ultron/backend/app/security/vault.py",
            ".github/workflows/bypass.yml", "ultron/backend/app/cognitive/../security/risk.py",
            "ultron/backend/codegen.py", "ultron/backend/app/cognitive/__init__.py",
        ):
            with self.subTest(bad=bad), self.assertRaises(engine.ProposalError):
                engine.validate_path(bad, root=self.root)

    def test_reject_duplicate_paths_and_wrong_goal(self):
        self.proposal["files"][1]["path"] = self.code_path
        with self.assertRaises(engine.ProposalError):
            engine.validate_proposal(self.proposal, self.goal, root=self.root)
        self.proposal["goal_id"] = "fake-goal"
        with self.assertRaises(engine.ProposalError):
            engine.validate_proposal(self.proposal, self.goal, root=self.root)

    def test_secret_like_and_oversized_replacements_are_rejected(self):
        self.proposal["files"][0]["content"] = "token='ghp_abcdefghijklmnopqrstuvwxyz1234567'"
        with self.assertRaisesRegex(engine.ProposalError, "credential_like"):
            engine.validate_proposal(self.proposal, self.goal, root=self.root)
        self.proposal["files"][0]["content"] = "x" * (engine.MAX_SINGLE_BYTES + 1)
        with self.assertRaisesRegex(engine.ProposalError, "oversized"):
            engine.validate_proposal(self.proposal, self.goal, root=self.root)

    def test_symlink_escape_is_rejected(self):
        dest = self.root / self.code_path
        dest.symlink_to(Path(self.tmp.name).parent / "outside.py")
        with self.assertRaises(engine.ProposalError):
            engine.validate_path(self.code_path, root=self.root)

    def test_stale_commit_rejected_before_any_write(self):
        existing = self.root / self.code_path
        existing.write_text("original\n", encoding="utf-8")
        with patch("subprocess.run") as run:
            run.return_value.stdout = "b" * 40
            with self.assertRaisesRegex(engine.ProposalError, "stale_base_sha"):
                engine.apply(self.proposal, root=self.root)
        self.assertEqual(existing.read_text(encoding="utf-8"), "original\n")

    def test_model_endpoint_restricted_to_known_provider(self):
        with self.assertRaisesRegex(engine.ProposalError, "unsupported_provider"):
            engine.infer("Test", "unknown")

    def test_planner_never_claims_autonomous_release(self):
        result = engine.plan_goal(SHA, [])
        self.assertEqual(result["status"], "ready")
        self.assertNotIn("deployed", result)
        self.assertNotIn("approved", result)

    def test_existing_regression_test_must_be_preserved_verbatim(self):
        test_file = self.root / self.test_path
        original = "def test_existing_behavior():\n    assert 2 + 2 == 4\n"
        test_file.write_text(original, encoding="utf-8")
        self.proposal["files"][1]["content"] = "def test_existing_behavior():\n    assert True\n"
        with self.assertRaisesRegex(engine.ProposalError, "existing_tests_must_be_preserved"):
            engine.validate_proposal(self.proposal, self.goal, root=self.root)

    def test_trivial_new_test_is_rejected(self):
        self.proposal["files"][1]["content"] = "def test_safe():\n    assert True\n"
        with self.assertRaisesRegex(engine.ProposalError, "trivial_test_rejected"):
            engine.validate_proposal(self.proposal, self.goal, root=self.root)

    def test_repair_is_one_bounded_model_attempt_with_redacted_feedback(self):
        source = self.root / self.code_path
        source.write_text("def safe():\n    return False\n", encoding="utf-8")
        plan = {"status": "ready", "base_sha": SHA, "goal": self.goal}
        model_patch = {
            "summary": "Repair the observed regression",
            "files": [
                {"path": "app/cognitive/communication.py", "content": "def safe():\n    return True\n"},
                {"path": "tests/test_autodev_communication.py", "content": "def test_safe():\n    assert safe() is True\n"},
            ],
        }
        previous = dict(self.proposal)
        previous["files"] = [dict(item) for item in self.proposal["files"]]
        with patch.object(engine, "infer", return_value=json.dumps(model_patch)) as fake:
            result = engine.generate(
                plan, "gemini", root=self.root,
                failure_summary="bad test; key=AIza0123456789abcdefghijklmnop",
                previous_proposal=previous,
            )
        self.assertEqual(result["attempt"], 2)
        prompt = fake.call_args.args[0]
        self.assertIn("UNTRUSTED TEST DIAGNOSTICS", prompt)
        self.assertIn("[REDACTED_CREDENTIAL]", prompt)
        self.assertNotIn("AIza0123456789abcdefghijklmnop", prompt)

    def test_repair_rejects_third_call_and_no_change(self):
        plan = {"status": "ready", "base_sha": SHA, "goal": self.goal}
        with patch.object(engine, "infer", return_value="{}"):
            with self.assertRaisesRegex(engine.ProposalError, "model_call_budget_exceeded"):
                engine.generate(plan, "ollama", root=self.root, failure_summary="x", previous_proposal={
                    "attempt": 2,
                })

    def test_sanitize_diagnostics_redacts_tokens_and_bounds_output(self):
        raw = "\x1b[31mAIza0123456789abcdefghijklmnop\x1b[0m\n" + "x" * 9000
        cleaned = engine.sanitize_diagnostics(raw)
        self.assertNotIn("AIza0123456789abcdefghijklmnop", cleaned)
        self.assertLessEqual(len(cleaned), engine.MAX_FAILURE_CONTEXT_CHARS)

    def test_transient_provider_or_environment_failures_are_not_retried(self):
        self.assertFalse(engine.failure_is_repairable("Provider temporarily unavailable; 429 quota exceeded"))
        self.assertFalse(engine.failure_is_repairable("ModuleNotFoundError: No module named 'pytest'"))
        self.assertTrue(engine.failure_is_repairable("AssertionError: expected owner scoped result"))

    def test_verify_runs_real_generated_regression_and_sanitizes_failure(self):
        self.proposal["files"][0]["content"] = "def safe():\n    return False\n"
        self.proposal["files"][1]["content"] = (
            "from app.cognitive.communication import safe\n\n"
            "def test_safe():\n    assert safe(), 'AIza0123456789abcdefghijklmnop'\n"
        )
        def materialize(_proposal, *, root):
            for entry in self.proposal["files"]:
                target = root / entry["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(entry["content"], encoding="utf-8")
            return [entry["path"] for entry in self.proposal["files"]]
        with patch.object(engine, "load_goals", return_value=[self.goal]), \
             patch.object(engine, "apply", side_effect=materialize):
            result = engine.verify_proposal(self.proposal, root=self.root)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_class"], "preflight")
        self.assertFalse(result["repairable"])
        self.assertNotIn("AIza0123456789abcdefghijklmnop", result["diagnostics"])
        self.assertIn("credential_like_content", result["diagnostics"])

    def test_verify_accepts_a_passing_generated_regression(self):
        self.proposal["files"][1]["content"] = (
            "from app.cognitive.communication import safe\n\n"
            "def test_safe():\n    assert safe() is True\n"
        )
        def materialize(_proposal, *, root):
            for entry in self.proposal["files"]:
                target = root / entry["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(entry["content"], encoding="utf-8")
            return [entry["path"] for entry in self.proposal["files"]]
        with patch.object(engine, "load_goals", return_value=[self.goal]), \
             patch.object(engine, "apply", side_effect=materialize):
            result = engine.verify_proposal(self.proposal, root=self.root)
        self.assertEqual(result["status"], "passed", result["diagnostics"])
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["quality_gates"]["syntax"]["status"], "PASS")
        self.assertEqual(result["quality_gates"]["unit_test"]["status"], "PASS")
        self.assertEqual(result["quality_gates"]["type_check"]["status"], "PENDING")
        self.assertEqual(result["quality_gates"]["performance_regression"]["status"], "NOT_APPLICABLE")
        self.assertIsNone(result["failure_class"])

    def test_fake_model_to_failing_test_to_repair_and_retest(self):
        backend = self.root / "ultron/backend"
        source = backend / "app/cognitive/communication.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("def safe():\n    return False\n", encoding="utf-8")
        subprocess.run(["git", "init", "-b", "test-base"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Autodev Test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "autodev-test@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "ultron/backend/app/cognitive/communication.py"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "fixture base"], cwd=self.root, check=True, capture_output=True)
        base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, check=True,
                                  capture_output=True, text=True).stdout.strip()
        plan = {"status": "ready", "base_sha": base_sha, "goal": self.goal}
        test_content = (
            "from app.cognitive.communication import safe\n\n"
            "def test_safe():\n    assert safe() is True\n"
        )
        initial = {"summary": "Regression candidate", "files": [
            {"path": "app/cognitive/communication.py", "content": "def safe():\n    return False\n"},
            {"path": "tests/test_autodev_communication.py", "content": test_content},
        ]}
        repaired = {"summary": "Repair candidate after observed failure", "files": [
            {"path": "app/cognitive/communication.py", "content": "def safe():\n    return True\n"},
            {"path": "tests/test_autodev_communication.py", "content": test_content},
        ]}
        with patch.object(engine, "load_goals", return_value=[self.goal]), \
             patch.object(engine, "infer", side_effect=[json.dumps(initial), json.dumps(repaired)]) as fake:
            first = engine.generate(plan, "ollama", root=self.root)
            failed = engine.verify_proposal(first, root=self.root)
            self.assertEqual(failed["status"], "failed")
            self.assertEqual(failed["failure_class"], "code")
            self.assertGreater(len(failed["diagnostics"]), 0)
            subprocess.run(["git", "reset", "--hard", base_sha], cwd=self.root, check=True, capture_output=True)
            subprocess.run(["git", "clean", "-fd"], cwd=self.root, check=True, capture_output=True)
            second = engine.generate(
                plan, "ollama", root=self.root,
                failure_summary=failed["diagnostics"], previous_proposal=first,
            )
            passed = engine.verify_proposal(second, root=self.root)
        self.assertEqual(fake.call_count, 2)
        self.assertEqual(first["attempt"], 1)
        self.assertEqual(second["attempt"], 2)
        self.assertEqual(passed["status"], "passed", passed["diagnostics"])


if __name__ == "__main__":
    unittest.main()
