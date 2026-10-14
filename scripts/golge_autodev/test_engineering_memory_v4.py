from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ultron/backend"))
import discovery
import engine
from engineering_memory import EngineeringMemory
from remember_pipeline import record_pipeline
from triage import triage_candidates
from github_pr_publisher import GitHubPRPublisher, BASE_BRANCH

SHA = "a" * 40


class LocalDraftPublisher:
    """Exercise the shared publisher while stubbing GitHub network commands."""
    def __init__(self, root: Path, metadata: Path):
        self.root = root
        self.metadata = metadata

    def publish(self, proposal: dict, goal: dict) -> dict:
        paths = [path for path, _ in engine.validate_proposal(proposal, goal, root=self.root)]
        calls = []

        def no_network_run(args, **kwargs):
            calls.append(list(args))
            if args[:2] == ["git", "fetch"] or args[:2] == ["git", "push"]:
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
            if args[:3] == ["gh", "auth", "status"]:
                return subprocess.CompletedProcess(args, 0, stdout="authenticated fixture\n", stderr="")
            if args[:3] == ["gh", "pr", "create"]:
                return subprocess.CompletedProcess(
                    args, 0, stdout="https://github.com/fatmakahraman304-hash/ULTRON/pull/999\n", stderr="")
            return subprocess.run(args, **kwargs)

        proposal_id = hashlib.sha256(b"isolated-autodev-fixture").hexdigest()[:12]
        publisher = GitHubPRPublisher(self.root, run=no_network_run)
        prepared = publisher.prepare(proposal_id)
        if prepared["base"] != BASE_BRANCH:
            raise ValueError("fixture_publisher_base")
        applied = engine.apply(proposal, root=self.root)
        if applied != paths:
            raise ValueError("fixture_publisher_paths")
        relative = [path.removeprefix("ultron/") for path in paths]
        published = publisher.publish(
            proposal_id=proposal_id, branch=prepared["branch"], paths=relative,
            goal=proposal["summary"], autonomous_goal_id=goal["id"],
            autonomous_candidate_id=proposal.get("discovery_candidate_id"),
        )
        result = {**published, "draft": True, "paths": paths,
                  "network_calls": 0, "provider_calls": 0,
                  "github_write_commands": [row[:3] for row in calls if row[:2] in (["gh", "pr"], ["git", "push"]) ]}
        self.metadata.write_text(json.dumps(result), encoding="utf-8")
        return result


class EngineeringMemoryContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / "memory.sqlite"
        self.candidate = discovery.candidates_from_actions([{
            "databaseId": 987654, "conclusion": "failure",
            "headBranch": engine.BASE_BRANCH, "headSha": SHA,
            "jobs": [{"conclusion": "failure", "steps": [{
                "conclusion": "failure",
                "name": "pytest ultron/backend/tests/test_autodev_communication.py",
            }]}],
        }])[0]

    def test_memory_keeps_only_bounded_structured_evidence_and_round_trips(self):
        candidate = dict(self.candidate, status="eligible", verification_status="reproduced",
                         verified_test="ultron/backend/tests/test_autodev_communication.py",
                         evidence_commit_sha="b" * 40, verification_sha=SHA)
        candidate["evidence"] = "API_KEY=AIza0123456789abcdefghijklmnop raw exception details"
        memory = EngineeringMemory(self.db)
        memory.record_candidate(candidate, source_sha=SHA)
        memory.record_attempt(candidate["candidate_id"], attempt_no=1, stage="verify",
                              outcome="failed", source_sha=SHA,
                              tests=["ultron/backend/tests/test_autodev_communication.py"],
                              retry_after="2099-01-01T00:00:00+00:00")
        snapshot = memory.snapshot()
        packed = json.dumps(snapshot)
        self.assertNotIn("AIza0123456789abcdefghijklmnop", packed)
        self.assertNotIn("raw exception details", packed)
        self.assertEqual(snapshot["candidates"][0]["source_sha"], SHA)
        self.assertEqual(snapshot["candidates"][0]["evidence_sha"], "b" * 40)
        self.assertEqual(snapshot["candidates"][0]["verification_sha"], SHA)
        self.assertEqual(snapshot["attempts"][0].get("failure_class"), None)
        self.assertFalse(memory.retry_allowed(candidate["candidate_id"], now="2098-01-01T00:00:00+00:00"))
        self.assertTrue(memory.retry_allowed(candidate["candidate_id"], now="2099-01-02T00:00:00+00:00"))
        out = self.root / "memory.json"
        memory.export_json(out)
        memory.close()

        restored = EngineeringMemory(self.root / "restored.sqlite")
        restored.import_json(out)
        after = restored.snapshot()
        self.assertEqual(len(after["candidates"]), 1)
        self.assertEqual(len(after["attempts"]), 1)
        self.assertEqual(after["attempts"][0]["outcome"], "failed")
        restored.close()

    def test_model_text_unknown_paths_and_bad_provenance_cannot_enter_memory(self):
        memory = EngineeringMemory(self.db)
        candidate = dict(self.candidate)
        candidate["source_ref"] = "model says this is a bug"
        with self.assertRaisesRegex(ValueError, "untrusted_evidence_reference"):
            memory.record_candidate(candidate, source_sha=SHA)
        candidate = dict(self.candidate, affected_files=["../../secrets.py"])
        with self.assertRaisesRegex(ValueError, "path_outside_registered_scope"):
            memory.record_candidate(candidate, source_sha=SHA)
        memory.close()

    def test_draft_pr_is_not_claimed_as_resolved_and_requires_passing_receipts(self):
        memory = EngineeringMemory(self.db)
        candidate = dict(self.candidate, status="eligible", verification_status="reproduced",
                         verified_test="ultron/backend/tests/test_autodev_communication.py")
        memory.record_candidate(candidate, source_sha=SHA)
        cid = candidate["candidate_id"]
        with self.assertRaisesRegex(ValueError, "draft_pr_without_test_and_publish_receipts"):
            memory.record_draft_pr(cid, commit_sha=SHA,
                                     pr_url="https://github.com/fatmakahraman304-hash/ULTRON/pull/123",
                                     passing_tests=["ultron/backend/tests/test_autodev_communication.py"])
        memory.record_attempt(cid, attempt_no=1, stage="verify", outcome="passed", source_sha=SHA,
                              tests=["ultron/backend/tests/test_autodev_communication.py"])
        memory.record_attempt(cid, attempt_no=1, stage="publish", outcome="created", source_sha=SHA,
                              tests=["ultron/backend/tests/test_autodev_communication.py"],
                              commit_sha=SHA,
                              pr_url="https://github.com/fatmakahraman304-hash/ULTRON/pull/123")
        memory.record_draft_pr(cid, commit_sha=SHA,
                                 pr_url="https://github.com/fatmakahraman304-hash/ULTRON/pull/123",
                                 passing_tests=["ultron/backend/tests/test_autodev_communication.py"])
        self.assertEqual(memory.snapshot()["candidates"][0]["status"], "draft_pr_open")
        self.assertFalse(memory.retry_allowed(cid))
        self.assertFalse(memory.record_candidate(candidate, source_sha=SHA))
        memory.close()

    def test_confirmed_no_longer_reproduced_candidate_survives_worker_restart(self):
        candidate = dict(self.candidate, status="already_addressed", verification_status="passed",
                         verified_test="ultron/backend/tests/test_autodev_communication.py",
                         verification_sha=SHA)
        memory = EngineeringMemory(self.db)
        memory.record_candidate(candidate, source_sha=SHA)
        out = self.root / "confirmed.json"
        memory.export_json(out)
        memory.close()
        restored = EngineeringMemory(self.root / "confirmed-restored.sqlite")
        restored.import_json(out)
        self.assertEqual(restored.snapshot()["candidates"][0]["status"], "already_addressed")
        self.assertFalse(restored.record_candidate(candidate, source_sha=SHA))
        restored.close()

    def test_artifact_context_rejects_wrong_repo_workflow_branch_or_selected_run(self):
        memory = EngineeringMemory(self.db)
        context = {"repository": "fatmakahraman304-hash/ULTRON",
                   "workflow": "GOLGE Autonomous Development (Draft PR Only)",
                   "source_branch": engine.BASE_BRANCH, "producer_run_id": "101",
                   "exported_at": "2026-10-14T00:00:00+00:00"}
        artifact = self.root / "artifact.json"
        memory.export_json(artifact, artifact_context=context)
        memory.close()
        expected = {"repository": context["repository"], "workflow": context["workflow"],
                    "source_branch": context["source_branch"], "producer_run_id": "101"}
        restored = EngineeringMemory(self.root / "restored.sqlite")
        restored.import_json(artifact, expected_context=expected, current_run_id="102")
        restored.close()
        for key, wrong_value in (("repository", "somewhere/else"),
                                 ("workflow", "unrelated workflow"),
                                 ("source_branch", "main"),
                                 ("producer_run_id", "103")):
            wrong = dict(expected, **{key: wrong_value})
            target = EngineeringMemory(self.root / ("reject-" + key + ".sqlite"))
            with self.subTest(key=key), self.assertRaises(ValueError):
                target.import_json(artifact, expected_context=wrong, current_run_id="102")
            self.assertEqual(target.snapshot()["candidates"], [])
            target.close()
        # Same-run handoff between discovery and remember is valid only when
        # the run identity in the envelope matches the explicitly selected ID.
        target = EngineeringMemory(self.root / "same-run.sqlite")
        target.import_json(artifact, expected_context=expected, current_run_id="101")
        target.close()

    def test_artifact_older_than_ninety_days_is_rejected(self):
        memory = EngineeringMemory(self.db)
        context = {"repository": "fatmakahraman304-hash/ULTRON",
                   "workflow": "GOLGE Autonomous Development (Draft PR Only)",
                   "source_branch": engine.BASE_BRANCH, "producer_run_id": "101",
                   "exported_at": "2026-10-14T00:00:00+00:00"}
        artifact = self.root / "old.json"
        memory.export_json(artifact, artifact_context=context)
        memory.close()
        envelope = json.loads(artifact.read_text(encoding="utf-8"))
        envelope["artifact_context"]["exported_at"] = "2026-07-01T00:00:00+00:00"
        artifact.write_text(json.dumps(envelope), encoding="utf-8")
        target = EngineeringMemory(self.root / "target.sqlite")
        expected = {key: context[key] for key in ("repository", "workflow", "source_branch", "producer_run_id")}
        with self.assertRaisesRegex(ValueError, "memory_artifact_expired"):
            target.import_json(artifact, expected_context=expected, current_run_id="102",
                               now="2026-10-14T00:00:00+00:00")
        target.close()

    def test_v4_legacy_snapshot_requires_provenance_checked_artifact_receipt(self):
        memory = EngineeringMemory(self.db)
        candidate = dict(self.candidate, status="review_required", verification_status="not_run",
                         verified_test=None)
        memory.record_candidate(candidate, source_sha=SHA)
        artifact = self.root / "legacy-v4.json"
        artifact.write_text(json.dumps(memory.snapshot()), encoding="utf-8")  # V4's unwrapped snapshot shape.
        memory.close()
        expected = {"repository": "fatmakahraman304-hash/ULTRON",
                    "workflow": "GOLGE Autonomous Development (Draft PR Only)",
                    "source_branch": engine.BASE_BRANCH, "producer_run_id": "101"}
        rejected = EngineeringMemory(self.root / "legacy-rejected.sqlite")
        with self.assertRaisesRegex(ValueError, "memory_artifact_context_missing"):
            rejected.import_json(artifact, expected_context=expected, current_run_id="102")
        self.assertEqual(rejected.snapshot()["candidates"], [])
        rejected.close()
        restored = EngineeringMemory(self.root / "legacy-restored.sqlite")
        restored.import_json(artifact, expected_context=expected, current_run_id="102",
                             trusted_legacy_run_id="101",
                             trusted_legacy_created_at="2026-10-13T00:00:00+00:00",
                             now="2026-10-14T00:00:00+00:00")
        self.assertEqual(restored.snapshot()["candidates"][0]["candidate_id"], candidate["candidate_id"])
        restored.close()

    def test_invalid_later_candidate_cannot_partially_mutate_restored_database(self):
        memory = EngineeringMemory(self.db)
        candidate = dict(self.candidate, status="review_required", verification_status="not_run",
                         verified_test=None)
        memory.record_candidate(candidate, source_sha=SHA)
        artifact = self.root / "corrupt.json"
        artifact.write_text(json.dumps(memory.snapshot()), encoding="utf-8")
        memory.close()
        data = json.loads(artifact.read_text(encoding="utf-8"))
        data["candidates"].append({"candidate_id": "invalid"})
        artifact.write_text(json.dumps(data), encoding="utf-8")
        restored = EngineeringMemory(self.root / "restored-corrupt.sqlite")
        with self.assertRaises(ValueError):
            restored.import_json(artifact)
        self.assertEqual(restored.snapshot()["candidates"], [])
        restored.close()

    def test_open_draft_pr_remains_open_not_resolved_after_snapshot_restore(self):
        memory = EngineeringMemory(self.db)
        candidate = dict(self.candidate, status="eligible", verification_status="reproduced",
                         verified_test="ultron/backend/tests/test_autodev_communication.py")
        memory.record_candidate(candidate, source_sha=SHA)
        cid = candidate["candidate_id"]
        pr_url = "https://github.com/fatmakahraman304-hash/ULTRON/pull/123"
        memory.record_attempt(cid, attempt_no=1, stage="verify", outcome="passed", source_sha=SHA,
                              tests=[candidate["verified_test"]])
        memory.record_attempt(cid, attempt_no=1, stage="publish", outcome="created", source_sha=SHA,
                              tests=[candidate["verified_test"]], commit_sha=SHA, pr_url=pr_url)
        memory.record_draft_pr(cid, commit_sha=SHA, pr_url=pr_url,
                               passing_tests=[candidate["verified_test"]])
        artifact = self.root / "draft.json"
        memory.export_json(artifact)
        memory.close()
        restored = EngineeringMemory(self.root / "restored-draft.sqlite")
        restored.import_json(artifact)
        row = restored.snapshot()["candidates"][0]
        self.assertEqual(row["status"], "draft_pr_open")
        self.assertNotEqual(row["status"], "already_addressed")
        self.assertFalse(restored.retry_allowed(cid))
        restored.close()

    def test_provenance_bound_empty_bootstrap_survives_a_worker_restart(self):
        context = {"repository": "fatmakahraman304-hash/ULTRON",
                   "workflow": "GOLGE Autonomous Development (Draft PR Only)",
                   "source_branch": engine.BASE_BRANCH, "producer_run_id": "101",
                   "exported_at": "2026-10-14T12:00:00+00:00"}
        first_worker = EngineeringMemory(self.db)
        artifact = self.root / "initial-memory.json"
        first_worker.export_json(artifact, artifact_context=context)
        first_worker.close()

        restarted_worker = EngineeringMemory(self.root / "restarted.sqlite")
        restarted_worker.import_json(
            artifact,
            expected_context={key: value for key, value in context.items() if key != "exported_at"},
            current_run_id="102",
            now="2026-10-14T13:00:00+00:00",
        )
        restored = restarted_worker.snapshot()
        self.assertEqual(restored["candidates"], [])
        self.assertEqual(restored["attempts"], [])
        self.assertEqual(restored["scheduler"]["state"], "running")
        restarted_worker.close()

    def test_workflow_fails_closed_on_missing_memory_and_keeps_ninety_day_retention(self):
        workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/golge-autodev.yml").read_text(encoding="utf-8")
        self.assertIn("memory artifact missing or expired", workflow.lower())
        self.assertIn("retention-days: 90", workflow)
        self.assertIn("memory_available", workflow)
        self.assertIn("initialize_memory", workflow)
        self.assertIn("confirm_empty_memory_bootstrap", workflow)
        self.assertIn('"$GITHUB_REF" != "refs/heads/main"', workflow)
        self.assertIn("--assert-empty-memory", workflow)
        self.assertIn("main", workflow.split("  pull_request:", 1)[1].split("    paths:", 1)[0])
        self.assertIn("--network=none", Path(__file__).with_name("sandbox.py").read_text(encoding="utf-8"))
        self.assertIn("docker pull ubuntu:24.04@sha256:", workflow)
        for job in ("verify_initial", "verify_repair"):
            self.assertIn("docker pull ubuntu:24.04@sha256:", workflow.split(f"  {job}:", 1)[1])
        for tracking_file in ("ULTRON_ROADMAP.md", "ULTRON_PROGRESS.md",
                              "ULTRON_NEXT_TASKS.md", "ULTRON_TEST_RESULTS.md"):
            self.assertIn(f'"{tracking_file}"', workflow)

    def test_scheduler_is_single_flight_sha_pinned_and_pauseable(self):
        memory = EngineeringMemory(self.db)
        self.assertFalse(memory.acquire_write_slot(owner="stale", base_sha=SHA, current_sha="b" * 40))
        self.assertTrue(memory.acquire_write_slot(owner="run-1", base_sha=SHA, current_sha=SHA))
        self.assertFalse(memory.acquire_write_slot(owner="run-2", base_sha=SHA, current_sha=SHA))
        self.assertFalse(memory.release_write_slot("run-2"))
        self.assertTrue(memory.release_write_slot("run-1"))
        memory.set_paused(True, "test failure")
        self.assertFalse(memory.acquire_write_slot(owner="run-3", base_sha=SHA, current_sha=SHA))
        memory.set_paused(False)
        self.assertTrue(memory.acquire_write_slot(owner="run-3", base_sha=SHA, current_sha=SHA))
        memory.close()

    def test_scheduler_competing_workers_get_only_one_write_lease(self):
        initialized = EngineeringMemory(self.db)
        initialized.close()
        barrier = threading.Barrier(2)
        results = []

        def claim(name):
            store = EngineeringMemory(self.db)
            barrier.wait()
            results.append(store.acquire_write_slot(owner=name, base_sha=SHA, current_sha=SHA))
            store.close()

        threads = [threading.Thread(target=claim, args=("worker-a",)),
                   threading.Thread(target=claim, args=("worker-b",))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 1)

    def test_triage_requires_reproduced_registered_test_and_blocks_open_pr_conflicts(self):
        candidate = dict(self.candidate)
        test_path = "ultron/backend/tests/test_autodev_communication.py"
        failed = triage_candidates([candidate], base_sha=SHA,
                                   test_results={test_path: {"state": "failed_code", "returncode": 1}})[0]
        self.assertEqual(failed["status"], "eligible")
        passed = triage_candidates([candidate], base_sha=SHA,
                                   test_results={test_path: {"state": "passed", "returncode": 0}})[0]
        self.assertEqual(passed["status"], "already_addressed")
        blocked = triage_candidates([candidate], base_sha=SHA,
                                    open_prs=[{"paths": ["ultron/backend/app/cognitive/communication.py"]}],
                                    test_results={test_path: {"state": "failed_code", "returncode": 1}})[0]
        self.assertEqual(blocked["status"], "blocked")
        invalid = dict(candidate, evidence="model-invented failure")
        invalid["candidate_id"] = "f" * 20
        rejected = triage_candidates([invalid], base_sha=SHA,
                                     test_results={test_path: {"state": "failed_code", "returncode": 1}})[0]
        self.assertEqual(rejected["status"], "insufficient_evidence")


class FakeModelAutonomyIntegration(unittest.TestCase):
    """End-to-end fake model + real pytest + local-only draft publication.

    This intentionally does not make a Gemini/Qwen request or connect to GitHub.
    """
    def test_discover_code_fail_repair_pytest_publish_and_deduplicate(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        backend = root / "ultron/backend"
        code_rel = "ultron/backend/app/cognitive/communication.py"
        test_rel = "ultron/backend/tests/test_autodev_communication.py"
        integration_rel = "ultron/backend/tests/test_integration_smoke.py"
        (root / code_rel).parent.mkdir(parents=True)
        (root / test_rel).parent.mkdir(parents=True)
        (root / integration_rel).parent.mkdir(parents=True, exist_ok=True)
        (root / code_rel).write_text("def safe():\n    return False\n", encoding="utf-8")
        (root / integration_rel).write_text(
            "from app.cognitive.communication import safe\n\ndef test_integration_state():\n    assert safe() is True\n",
            encoding="utf-8")
        subprocess.run(["git", "init", "-b", BASE_BRANCH], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Autodev Fixture"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "add", code_rel, integration_rel], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "fixture base"], cwd=root, check=True, capture_output=True)
        base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                                  capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "remote", "add", "origin",
                        "https://github.com/fatmakahraman304-hash/ULTRON.git"], cwd=root,
                       check=True, capture_output=True)
        subprocess.run(["git", "update-ref", "refs/remotes/origin/" + BASE_BRANCH, base_sha],
                       cwd=root, check=True, capture_output=True)
        goal = next(item for item in engine.load_goals() if item["id"] == "dialogue-continuity-contract")
        goal = dict(goal, integration_tests=[integration_rel], quality_gate_policy="v5",
                    performance_sensitive=False)
        observed = discovery.candidates_from_actions([{
            "databaseId": 987655, "conclusion": "failure",
            "headBranch": engine.BASE_BRANCH, "headSha": base_sha,
            "jobs": [{"conclusion": "failure", "steps": [{
                "conclusion": "failure", "name": "pytest " + goal["test_path"],
            }]}],
        }])[0]
        triaged = triage_candidates([observed], base_sha=base_sha,
                                    test_results={goal["test_path"]: {"state": "failed_code", "returncode": 1}})
        self.assertEqual(triaged[0]["status"], "eligible")
        memory_path = root.with_name(root.name + "-memory.sqlite")
        for path in (memory_path, Path(str(memory_path) + "-wal"), Path(str(memory_path) + "-shm")):
            self.addCleanup(lambda path=path: path.unlink(missing_ok=True))
        memory = EngineeringMemory(memory_path)
        memory.record_candidate(triaged[0], source_sha=base_sha)
        self.assertTrue(memory.acquire_write_slot(owner="fixture-run", base_sha=base_sha,
                                                 current_sha=base_sha))
        plan = engine.plan_goal(base_sha, [], [], triaged, require_discovery=True,
                                memory_snapshot=memory.snapshot())
        self.assertEqual(plan["status"], "ready")
        self.assertEqual(plan["goal"]["id"], goal["id"])

        regression = "from app.cognitive.communication import safe\n\ndef test_safe():\n    assert safe() is True\n"
        first_model = {"summary": "Add a tested safe communication behavior", "files": [
            {"path": "app/cognitive/communication.py", "content": "def safe():\n    return False\n"},
            {"path": "tests/test_autodev_communication.py", "content": regression},
        ]}
        repair_model = {"summary": "Correct the reproduced communication regression", "files": [
            {"path": "app/cognitive/communication.py", "content": "def safe():\n    return True\n"},
            {"path": "tests/test_autodev_communication.py", "content": regression},
        ]}
        with patch.object(engine, "load_goals", return_value=[goal]), \
             patch.object(engine, "infer", side_effect=[json.dumps(first_model), json.dumps(repair_model)]) as fake:
            proposal1 = engine.generate(plan, "ollama", root=root)
            self.assertEqual(proposal1["discovery_candidate_id"], triaged[0]["candidate_id"])
            failed = engine.verify_proposal(proposal1, root=root)
            self.assertEqual(failed["status"], "failed", failed)
            self.assertEqual(failed["failure_class"], "code")
            self.assertTrue(failed["repairable"])
            subprocess.run(["git", "reset", "--hard", base_sha], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "clean", "-fd"], cwd=root, check=True, capture_output=True)
            proposal2 = engine.generate(plan, "ollama", root=root,
                                        failure_summary=failed["diagnostics"], previous_proposal=proposal1)
            self.assertEqual(proposal2["attempt"], 2)
            passed = engine.verify_proposal(proposal2, root=root)
        self.assertEqual(fake.call_count, 2)
        self.assertEqual(passed["status"], "passed", passed["diagnostics"])
        self.assertTrue(all(item["status"] in {"PASS", "NOT_APPLICABLE"}
                            for item in passed["quality_gates"].values()), passed["quality_gates"])

        # This narrow test publisher has no token/network. It creates only a
        # fixture-local commit through the real shared GitHubPRPublisher code.
        # Git fetch/push, gh auth and PR creation are stubbed; nothing is sent.
        publisher_metadata = root.with_name(root.name + "-fixture-pr.json")
        self.addCleanup(lambda: publisher_metadata.unlink(missing_ok=True))
        subprocess.run(["git", "reset", "--hard", base_sha], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "clean", "-fd"], cwd=root, check=True, capture_output=True)
        fake_publisher = LocalDraftPublisher(root, publisher_metadata)
        published = fake_publisher.publish(proposal2, goal)
        commit_sha = published["commit_sha"]
        self.assertRegex(commit_sha, r"^[0-9a-f]{40}$")
        self.assertTrue(published["draft"])
        self.assertEqual(published["network_calls"], 0)
        self.assertEqual(published["pull_request"], "https://github.com/fatmakahraman304-hash/ULTRON/pull/999")
        self.assertIn(["gh", "pr", "create"], published["github_write_commands"])
        ast_path = root / code_rel
        __import__("ast").parse(ast_path.read_text(encoding="utf-8"))
        outcome = record_pipeline(memory, candidate_id=triaged[0]["candidate_id"],
                                  source_sha=base_sha, plan_status="ready", proposed=True,
                                  propose_result="success", initial_result="failure",
                                  repair_result="success", verify_repair_result="success",
                                  initial_failure_class="code", repair_failure_class="none",
                                  initial_patch_sha="b" * 64, repair_patch_sha="c" * 64,
                                  draft_result="success",
                                  pr_url="https://github.com/fatmakahraman304-hash/ULTRON/pull/999",
                                  commit_sha=commit_sha)
        self.assertTrue(outcome["draft_pr_created"])
        self.assertFalse(outcome["problem_resolved"])
        self.assertTrue(memory.release_write_slot("fixture-run"))
        export_path = root.with_name(root.name + "-engineering-memory.json")
        memory.export_json(export_path)
        memory.close()
        restarted_path = root.with_name(root.name + "-restarted.sqlite")
        for path in (restarted_path, Path(str(restarted_path) + "-wal"), Path(str(restarted_path) + "-shm")):
            self.addCleanup(lambda path=path: path.unlink(missing_ok=True))
        restarted = EngineeringMemory(restarted_path)
        restarted.import_json(export_path)
        snapshot = restarted.snapshot()
        self.assertEqual(len(snapshot["attempts"]), 3)
        self.assertIn(commit_sha, [row["commit_sha"] for row in snapshot["attempts"]])
        verify_attempt = next(row for row in snapshot["attempts"] if row["stage"] == "verify")
        repair_attempt = next(row for row in snapshot["attempts"] if row["stage"] == "repair")
        self.assertEqual(verify_attempt["failure_class"], "code")
        self.assertEqual(verify_attempt["patch_sha"], "b" * 64)
        self.assertEqual(repair_attempt["patch_sha"], "c" * 64)
        self.assertEqual(snapshot["candidates"][0]["status"], "draft_pr_open")
        self.assertNotEqual(engine.plan_goal(base_sha, [], [], triaged,
                                             require_discovery=True,
                                             memory_snapshot=snapshot)["status"], "ready")
        restarted.close()


if __name__ == "__main__":
    unittest.main()
