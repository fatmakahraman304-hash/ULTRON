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
            "files": [
                {"path": self.code_path, "content": "def safe():\n    return True\n"},
                {"path": self.test_path, "content": "def test_safe():\n    assert True\n"},
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
        with patch.object(engine, "infer", return_value=json.dumps(self.proposal)) as fake:
            result = engine.generate(plan, "ollama", root=self.root)
        self.assertEqual(result["goal_id"], self.goal["id"])
        self.assertTrue(fake.called)
        self.assertEqual(source.read_text(encoding="utf-8"), "def safe():\n    return False\n")

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


if __name__ == "__main__":
    unittest.main()
