from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import connected_services as connector


def fake_render_service():
    return {
        "id": connector.RENDER_SERVICE_ID,
        "ownerId": connector.RENDER_WORKSPACE_ID,
        "repo": "https://github.com/" + connector.REPOSITORY,
        "branch": connector.RENDER_DEPLOY_BRANCH,
        "autoDeploy": "yes",
        "suspended": "not_suspended",
        "serviceDetails": {"url": "https://ultron-yubh.onrender.com"},
        "envVars": [{"key": "PRIVATE_DO_NOT_FORWARD", "value": "SECRET_VALUE_781"}],
    }


class ConnectedServicesV8Contracts(unittest.TestCase):
    def test_render_status_is_identity_scoped_and_filters_credentials(self):
        with patch.object(connector, "_render_get", return_value=fake_render_service()) as get:
            result = connector.render_service_status()
        get.assert_called_once_with(f"services/{connector.RENDER_SERVICE_ID}")
        self.assertTrue(result["read_only"])
        self.assertTrue(result["auto_deploy"])
        self.assertEqual(result["deploy_branch"], connector.RENDER_DEPLOY_BRANCH)
        self.assertNotIn("PRIVATE_DO_NOT_FORWARD", json.dumps(result))
        self.assertNotIn("SECRET_VALUE_781", json.dumps(result))
        for field, value in (
            ("ownerId", "tea-another-workspace"),
            ("id", "srv-another-service"),
            ("branch", "main"),
            ("repo", "https://github.com/attacker/repo"),
            ("repo", ["malformed"]),
        ):
            bad = dict(fake_render_service(), **{field: value})
            with self.subTest(field=field, value=value), patch.object(
                connector, "_render_get", return_value=bad
            ), self.assertRaisesRegex(connector.ConnectorUnavailable, "identity_mismatch"):
                connector.render_service_status()

    def test_render_http_is_get_only_fixed_scope_and_never_prints_key(self):
        observed = {}
        class FakeOpener:
            def open(self, request, *, timeout):
                observed["method"] = request.get_method()
                observed["url"] = request.full_url
                observed["auth"] = request.get_header("Authorization")
                observed["timeout"] = timeout
                return io.BytesIO(json.dumps(fake_render_service()).encode())

        token = "example-not-a-real-key-782"
        with patch.dict(os.environ, {"GOLGE_RENDER_API_KEY": token}), patch.object(
            connector.urllib.request, "build_opener", return_value=FakeOpener()
        ):
            result = connector.render_service_status()
        self.assertEqual(observed["method"], "GET")
        self.assertEqual(
            observed["url"], f"https://api.render.com/v1/services/{connector.RENDER_SERVICE_ID}"
        )
        self.assertEqual(observed["auth"], "Bearer " + token)
        self.assertEqual(observed["timeout"], connector.REQUEST_TIMEOUT_SECONDS)
        self.assertNotIn(token, json.dumps(result))
        with self.assertRaisesRegex(connector.ConnectorUnavailable, "action_not_allowed"):
            connector._render_get("services/srv-unknown")
        with self.assertRaisesRegex(connector.ConnectorUnavailable, "action_not_allowed"):
            connector._render_get(f"services/{connector.RENDER_SERVICE_ID}/deploys")

    def test_no_render_key_and_redirect_both_fail_closed(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(
            connector.ConnectorUnavailable, "local_key_not_configured"
        ):
            connector.render_service_status()
        with self.assertRaisesRegex(connector.ConnectorUnavailable, "redirect_rejected"):
            connector._RejectRedirect().redirect_request(
                None, None, 302, "redirect", {}, "https://untrusted.example/capture"
            )

    def test_render_events_return_only_allowlisted_metadata(self):
        events = [
            {"event": {
                "serviceId": connector.RENDER_SERVICE_ID,
                "type": "deploy_ended",
                "timestamp": "2026-10-14T11:32:20.619335Z",
                "details": {
                    "deployStatus": "succeeded", "env": "SECRET_VALUE_781",
                    "message": "PRIVATE_STACK_TRACE_1001",
                },
            }},
            {"event": {
                "serviceId": "srv-other", "type": "deploy_started",
                "timestamp": "2026-10-14T11:31:07Z",
            }},
        ]
        with patch.object(connector, "_render_get", return_value=events) as get:
            result = connector.render_recent_events()
        get.assert_called_once_with(f"services/{connector.RENDER_SERVICE_ID}/events?limit=10")
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["status"], "succeeded")
        self.assertNotIn("SECRET_VALUE_781", json.dumps(result))
        self.assertNotIn("PRIVATE_STACK_TRACE_1001", json.dumps(result))

    def test_github_pr_read_uses_fixed_repo_get_only_and_no_shell(self):
        payload = {
            "number": 46, "state": "open", "draft": True, "merged": False,
            "base": {"ref": "feat/golge-autonomous-engineer-v6-20261015"},
            "head": {"ref": "feat/golge-autonomous-engineer-v7-20261015"},
            "body": "SECRET_VALUE_781",
        }
        completed = subprocess.CompletedProcess([], 0, json.dumps(payload), "")
        with patch.object(connector.shutil, "which", return_value="/usr/bin/gh"), patch.object(
            connector.subprocess, "run", return_value=completed
        ) as run:
            status = connector.github_pr_status(46)
        self.assertEqual(run.call_args.args[0], [
            "gh", "api", "-X", "GET", f"repos/{connector.REPOSITORY}/pulls/46"
        ])
        self.assertFalse(run.call_args.kwargs.get("shell", False))
        self.assertTrue(status["draft"])
        self.assertTrue(status["read_only"])
        self.assertNotIn("SECRET_VALUE_781", json.dumps(status))

    def test_github_fail_closed_for_invalid_pr_and_missing_cli(self):
        for number in (-1, 0, True, 1_000_001):
            with self.subTest(number=number), self.assertRaisesRegex(
                connector.ConnectorUnavailable, "github_pr_number_invalid"
            ):
                connector.github_pr_status(number)
        with patch.object(connector.shutil, "which", return_value=None), self.assertRaisesRegex(
            connector.ConnectorUnavailable, "github_cli_missing"
        ):
            connector.github_pr_status(46)

    def test_render_api_failures_never_surface_raw_responses(self):
        token = "example-not-a-real-key-782"
        class FailingOpener:
            def open(self, request, *, timeout):
                raise OSError("SECRET_VALUE_781 upstream refused")
        with patch.dict(os.environ, {"GOLGE_RENDER_API_KEY": token}), patch.object(
            connector.urllib.request, "build_opener", return_value=FailingOpener()
        ):
            with self.assertRaises(connector.ConnectorUnavailable) as caught:
                connector.render_service_status()
        self.assertEqual(str(caught.exception), "render_read_failed")
        self.assertNotIn("SECRET_VALUE_781", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
