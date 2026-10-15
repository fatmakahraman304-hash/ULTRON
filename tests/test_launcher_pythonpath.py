"""Regression tests for GÖLGE Windows START.bat and local backend import paths."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from integration.launcher import Services, child_pythonpath, desktop_pythonpath
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
        self.assertEqual(
            desktop_pythonpath(service.env["PYTHONPATH"]).split(os.pathsep)[:2],
            [str(ROOT), str(BACKEND)],
        )

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

    def test_desktop_roots_reverse_backend_priority(self):
        inherited = os.pathsep.join(
            [str(BACKEND), str(ROOT), "legacy-addon", str(BACKEND)]
        )
        paths = desktop_pythonpath(inherited).split(os.pathsep)
        self.assertEqual(paths, [str(ROOT), str(BACKEND), "legacy-addon"])

    def test_backend_and_desktop_memory_modules_are_distinct(self):
        for label, cwd, pythonpath, snippet in (
            (
                "backend", BACKEND, child_pythonpath(""),
                "from memory import MemorySystem; "
                "import memory; assert memory.__file__.endswith('memory.py')"
            ),
            (
                "desktop", ROOT, desktop_pythonpath(
                    os.pathsep.join([str(BACKEND), str(ROOT)])
                ),
                "import memory; from memory.memory_manager import load_memory; "
                "assert memory.__file__.endswith('__init__.py')"
            ),
        ):
            with self.subTest(role=label):
                env = os.environ.copy()
                env["PYTHONPATH"] = pythonpath
                result = subprocess.run(
                    [sys.executable, "-c", snippet], cwd=cwd, env=env,
                    capture_output=True, text=True, check=False, timeout=20,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_desktop_imports_own_memory_before_ui(self):
        script = (ROOT / "mark_app.py").read_text(encoding="utf-8")
        self.assertLess(
            script.index("from memory.memory_manager import ("),
            script.index("from ui import UltronUI"),
        )

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
