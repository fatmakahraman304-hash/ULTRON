"""Static contract for the double-click Windows launcher (cannot run wscript on Linux CI)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DesktopLauncherContract(unittest.TestCase):
    def read(self, name):
        raw = (ROOT / name).read_bytes()
        self.assertTrue(raw.isascii(), f"{name} must be ASCII (Turkish letters via ChrW) so wscript reads it on any code page")
        self.assertIn(b"\r\n", raw)
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
        return raw.decode("ascii")

    def test_launcher_starts_cockpit_hidden_and_reports_failures(self):
        text = self.read("GOLGE.vbs")
        for needle in ("scripts\\bootstrap.ps1", "-Mode start", "INSTALL.bat", ".venv\\Scripts\\python.exe", "logs\\golge-baslat.log"):
            self.assertIn(needle, text)
        self.assertRegex(text, r"sh\.Run\(cmd, 0, True\)")          # window style 0 = hidden
        self.assertIn("If rc <> 0", text)
        self.assertNotRegex(text, r"(?i)\b(del|rmdir|rd|format|reg add|setx)\b")

    def test_shortcut_installer_points_at_launcher_and_icon(self):
        text = self.read("GOLGE_KISAYOL_KUR.vbs")
        for needle in ("GOLGE.vbs", "config\\ultron.ico", 'SpecialFolders("Desktop")', 'SpecialFolders("Programs")', "wscript.exe"):
            self.assertIn(needle, text)
        self.assertIn("vbYesNo", text)                                  # autostart is opt-in
        self.assertRegex(text, r"If answer = vbYes Then\s+MakeShortcut sh\.SpecialFolders\(\"Startup\"\)")

    def test_referenced_files_exist(self):
        for name in ("scripts/bootstrap.ps1", "INSTALL.bat", "START.bat", "config/ultron.ico", "main.py"):
            self.assertTrue((ROOT / name).exists(), name)
        self.assertTrue(re.search(r"-Mode start", (ROOT / "START.bat").read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
