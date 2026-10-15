from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from artifact_locator import assert_no_existing_memory_artifact, select_latest, validate_run_details


class ArtifactLocatorContracts(unittest.TestCase):
    def setUp(self):
        self.now = "2026-10-14T12:00:00+00:00"
        self.artifact = {
            "id": 501, "name": "golge-autodev-engineering-memory", "expired": False,
            "created_at": "2026-10-13T12:00:00+00:00", "expires_at": "2027-01-11T12:00:00+00:00",
            "workflow_run": {"id": 401, "repository_id": 12, "workflow_id": 34,
                             "head_branch": "main", "head_sha": "a" * 40},
        }

    def test_selects_only_latest_same_repo_workflow_and_allowed_run_branch(self):
        older = dict(self.artifact, id=500, created_at="2026-10-12T12:00:00+00:00")
        selected = select_latest({"artifacts": [older, self.artifact]}, repository_id="12",
                                 workflow_id="34", source_branch="feat/ultron-cloud-shared-memory",
                                 current_run_id="402", now=self.now)
        self.assertEqual(selected["artifact_id"], "501")
        self.assertEqual(selected["run_id"], "401")

    def test_expired_old_foreign_workflow_foreign_repo_and_current_run_are_rejected(self):
        rows = []
        for change in (
            {"expired": True},
            {"created_at": "2026-07-01T12:00:00+00:00"},
            {"workflow_run": {**self.artifact["workflow_run"], "workflow_id": 99}},
            {"workflow_run": {**self.artifact["workflow_run"], "repository_id": 99}},
            {"workflow_run": {**self.artifact["workflow_run"], "id": 402}},
            {"workflow_run": {**self.artifact["workflow_run"], "head_branch": "feature/untrusted"}},
        ):
            row = dict(self.artifact)
            row.update(change)
            rows.append(row)
        self.assertIsNone(select_latest(rows, repository_id="12", workflow_id="34",
                                        source_branch="feat/ultron-cloud-shared-memory",
                                        current_run_id="402", now=self.now))

    def test_authoritative_run_metadata_must_match_workflow_repository_and_path(self):
        selected = select_latest({"artifacts": [self.artifact]}, repository_id="12", workflow_id="34",
                                 source_branch="feat/ultron-cloud-shared-memory",
                                 current_run_id="402", now=self.now)
        details = {"id": 401, "workflow_id": 34, "repository": {"id": 12},
                   "head_branch": "main", "head_sha": "a" * 40,
                   "path": ".github/workflows/golge-autodev.yml",
                   "event": "schedule"}
        self.assertTrue(validate_run_details(selected, details, repository_id="12", workflow_id="34",
                                             source_branch="feat/ultron-cloud-shared-memory",
                                             current_run_id="402"))
        for key, value in (("workflow_id", 99), ("path", ".github/workflows/other.yml"),
                           ("event", "pull_request"), ("id", 402)):
            bad = dict(details, **{key: value})
            with self.subTest(key=key):
                self.assertFalse(validate_run_details(selected, bad, repository_id="12", workflow_id="34",
                                                      source_branch="feat/ultron-cloud-shared-memory",
                                                      current_run_id="402"))

    def test_authoritative_run_sha_must_match_selected_artifact_receipt(self):
        selected = select_latest({"artifacts": [self.artifact]}, repository_id="12", workflow_id="34",
                                 source_branch="feat/ultron-cloud-shared-memory",
                                 current_run_id="402", now=self.now)
        details = {"id": 401, "workflow_id": 34, "repository": {"id": 12},
                   "head_branch": "main", "head_sha": "a" * 40,
                   "path": ".github/workflows/golge-autodev.yml", "event": "schedule"}
        self.assertTrue(validate_run_details(selected, details, repository_id="12", workflow_id="34",
                                             source_branch="feat/ultron-cloud-shared-memory",
                                             current_run_id="402"))
        details["head_sha"] = "b" * 40
        self.assertFalse(validate_run_details(selected, details, repository_id="12", workflow_id="34",
                                              source_branch="feat/ultron-cloud-shared-memory",
                                              current_run_id="402"))

    def test_empty_memory_can_only_be_initialized_when_listing_is_complete_and_empty(self):
        self.assertTrue(assert_no_existing_memory_artifact({"total_count": 0, "artifacts": []}))
        self.assertTrue(assert_no_existing_memory_artifact({"total_count": 1, "artifacts": [
            {"name": "golge-autodev-discovery"},
        ]}))
        with self.assertRaisesRegex(ValueError, "memory_bootstrap_refused_existing_artifact"):
            assert_no_existing_memory_artifact({"total_count": 1, "artifacts": [{
                "name": "golge-autodev-engineering-memory", "expired": True,
            }]})

    def test_memory_bootstrap_rejects_incomplete_or_malformed_artifact_listing(self):
        with self.assertRaisesRegex(ValueError, "artifact_listing_incomplete"):
            assert_no_existing_memory_artifact({"total_count": 2, "artifacts": [
                {"name": "golge-autodev-discovery"},
            ]})
        with self.assertRaisesRegex(ValueError, "artifact_listing_invalid"):
            assert_no_existing_memory_artifact({"total_count": 0, "artifacts": [None]})

    def test_restore_rejects_a_truncated_first_page_instead_of_guessing(self):
        with self.assertRaisesRegex(ValueError, "artifact_listing_incomplete"):
            select_latest({"total_count": 101, "artifacts": [self.artifact]},
                          repository_id="12", workflow_id="34",
                          source_branch="feat/ultron-cloud-shared-memory",
                          current_run_id="402", now=self.now)


if __name__ == "__main__":
    unittest.main()
