from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from artifact_locator import select_latest, validate_run_details


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


if __name__ == "__main__":
    unittest.main()
