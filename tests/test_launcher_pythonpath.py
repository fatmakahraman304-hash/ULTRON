"""Regression tests for GÖLGE Windows START.bat and local backend import paths."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from integration.launcher import Services, child_pythonpath
from integration.paths import BACKEND, ROOT


class LauncherPythonPathTests(unittest.TestCase):
    def test_required_roots_precede_preserved_pythonpath(self):
        inherited = os.pathsep.join(("external-one", "external-two"))
        self.assertEqual(
            child_pythonpath(inherited).split(os.pathsep),
            [str(BACKEND), str(ROOT), "external-one", "external-two"],
        )
        self.assertEqual(
            child_pythonpath("").split(os.pathsep), [str(BACKEND), str(ROOT)]
        )

    def test_services_start_exports_roots_to_backend_child(self):
        with patch.dict(os.environ, {"PYTHONPATH": "inherited-addon"}):
            with patch("integration.launcher.Bridge") as bridge:
                bridge.return_value.health.return_value = {
                    "ok": True, "service": "mark-ultron"
                }
                with patch.object(Services, "spawn") as spawn:
                    spawn.return_value.poll.return_value = None
                    service = Services()
                    service.start()
        spawn.assert_called_once()
        self.assertEqual(spawn.call_args.args[0][0], sys.executable)
        exported_paths = service.env["PYTHONPATH"].split(os.pathsep)
        self.assertEqual(exported_paths[:2], [str(BACKEND), str(ROOT)])
        self.assertEqual(exported_paths[-1], "inherited-addon")

    def test_subprocess_from_backend_directory_finds_cloud_package(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = child_pythonpath("")
        outcome = subprocess.run(
            [
                sys.executable, "-c",
                "import importlib.util; "
                "spec = importlib.util.find_spec('ultron.cloud_service.conversation_persona'); "
                "assert spec is not None and spec.origin.endswith('conversation_persona.py')"
            ],
            cwd=BACKEND,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        self.assertEqual(outcome.returncode, 0, outcome.stderr)

    def test_powershell_bootstrap_sets_both_import_paths(self):
        script = (ROOT / "scripts" / "bootstrap.ps1").read_text(encoding="utf-8")
        self.assertIn("$pythonPaths = @($backendPath, $projectRoot)", script)
        self.assertIn("if ($env:PYTHONPATH) { $pythonPaths += $env:PYTHONPATH }", script)
        self.assertIn(
            "$env:PYTHONPATH = $pythonPaths -join [IO.Path]::PathSeparator",
            script,
        )


if __name__ == "__main__":
    unittest.main()
