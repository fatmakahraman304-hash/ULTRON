from __future__ import annotations

import sys
import subprocess
from unittest.mock import patch
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sandbox
from sandbox import run_sandboxed


class GeneratedCodeSandboxContracts(unittest.TestCase):
    def test_workspace_is_read_only_and_host_secrets_are_not_in_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "should-not-be-created"
            result = run_sandboxed(
                [sys.executable, "-c", (
                    "import os,pathlib; "
                    "assert 'GOLGE_TEST_SECRET' not in os.environ; "
                    f"pathlib.Path({str(marker)!r}).write_text('bad')"
                )],
                cwd=root, env={"GOLGE_TEST_SECRET": "private-test-value"}, timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())

    def test_host_tmp_files_and_outbound_network_are_hidden(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as sibling:
            root = Path(tmp)
            private = Path(sibling) / "private.txt"
            private.write_text("private host content", encoding="utf-8")
            script = (
                "import pathlib,socket; "
                f"assert not pathlib.Path({str(private)!r}).exists(); "
                "s=socket.socket(); s.settimeout(1); "
                "\ntry: s.connect(('1.1.1.1',53))\n"
                "except OSError: print('network blocked')\n"
                "else: raise SystemExit('network unexpectedly available')"
            )
            result = run_sandboxed([sys.executable, "-c", script], cwd=root, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("network blocked", result.stdout)


    def test_venv_mounts_base_interpreter_read_only_without_host_home(self):
        # Mock Docker to test the invocation contract on machines without it.
        with tempfile.TemporaryDirectory() as root_tmp, \
             tempfile.TemporaryDirectory() as venv_tmp, \
             tempfile.TemporaryDirectory() as base_tmp:
            root, venv, base = map(Path, (root_tmp, venv_tmp, base_tmp))
            with patch.object(sandbox.sys, "platform", "linux"), \
                 patch.object(sandbox.sys, "prefix", str(venv)), \
                 patch.object(sandbox.sys, "base_prefix", str(base)), \
                 patch.object(sandbox.shutil, "which", return_value="/usr/bin/docker"), \
                 patch.object(sandbox, "_docker_ready", return_value=True), \
                 patch.object(sandbox.subprocess, "run", return_value=subprocess.CompletedProcess(
                     [], 0, "ok", "")) as docker_run:
                result = sandbox.run_sandboxed([str(venv / "bin/python"), "-V"],
                                               cwd=root, timeout=5)
            self.assertEqual(result.returncode, 0)
            args = docker_run.call_args.args[0]
            self.assertIn(f"{venv}:{venv}:ro", args)
            self.assertIn(f"{base}:{base}:ro", args)
            self.assertIn("--network=none", args)
            self.assertIn("--read-only", args)
            self.assertIn("--cap-drop=ALL", args)
            self.assertIn(str(venv / "bin/python"), args)

    def test_docker_runtime_init_failure_is_infrastructure_not_model_failure(self):
        with tempfile.TemporaryDirectory() as root_tmp:
            failing = subprocess.CompletedProcess(
                [], 127, "", "docker: Error response from daemon: "
                "OCI runtime create failed: runc create failed: missing interpreter")
            with patch.object(sandbox.sys, "platform", "linux"), \
                 patch.object(sandbox.shutil, "which", return_value="/usr/bin/docker"), \
                 patch.object(sandbox, "_docker_ready", return_value=True), \
                 patch.object(sandbox.subprocess, "run", return_value=failing):
                with self.assertRaisesRegex(sandbox.SandboxUnavailable, "sandbox_container_start_failed"):
                    sandbox.run_sandboxed([sys.executable, "-V"], cwd=Path(root_tmp))




if __name__ == "__main__":
    unittest.main()
