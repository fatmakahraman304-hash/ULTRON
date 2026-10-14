from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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


if __name__ == "__main__":
    unittest.main()
