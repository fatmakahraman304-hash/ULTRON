from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]


class BootstrapFrontendDependencySyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = (ROOT / "scripts" / "bootstrap.ps1").read_text(encoding="utf-8")

    def test_lockfile_hash_participates_in_startup_build_decision(self):
        self.assertIn(".ultron-package-lock.sha256", self.script)
        self.assertIn("Get-FileHash -LiteralPath $frontendLock -Algorithm SHA256", self.script)
        self.assertRegex(
            self.script,
            r"\$needsFrontendDependencies\s*=[\s\S]*?\$installedLockHash\s*-ne\s*\$expectedLockHash",
        )
        self.assertRegex(
            self.script,
            r"\$needsFrontendBuild\s*=[\s\S]*?\$needsFrontendDependencies",
        )

    def test_dependencies_are_reinstalled_from_lock_before_rebuild(self):
        self.assertRegex(
            self.script,
            r"if\s*\(\$needsFrontendDependencies\)\s*\{\s*Write-Host[^\n]*\n\s*& \$npm\.Source ci --no-audit --no-fund",
        )
        self.assertLess(self.script.index("& $npm.Source ci --no-audit --no-fund"),
                        self.script.index("& $npm.Source run build"))
        self.assertIn("WriteAllText($dependencyMarker, $expectedLockHash", self.script)


if __name__ == "__main__":
    unittest.main()
