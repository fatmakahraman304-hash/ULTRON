"""Smoke/regression tests for the safe Codex continuation report."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "ultron_dev_resume.py"
spec = importlib.util.spec_from_file_location("ultron_dev_resume", MODULE)
resume = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resume)


class ResumeTests(unittest.TestCase):
    def test_extracts_only_actionable_section(self):
        text = """# ULTRON

## Başka bir bölüm
- Do not execute this

## Hemen yapılacak
1. Fix camera persistence.
2. Run deterministic tests.
- Update CI.

## Sonra
1. Not a current task.
"""
        self.assertEqual(
            resume.extract_next_tasks(text),
            ["Fix camera persistence.", "Run deterministic tests.", "Update CI."],
        )

    def test_non_git_folder_is_reported_without_crashing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "ULTRON_NEXT_TASKS.md").write_text(
                "## Hemen yapılacak\n1. Continue tests.\n", encoding="utf-8"
            )
            report = resume.build_report(root)
            self.assertEqual(report["documents"]["ULTRON_ROADMAP.md"], "missing")
            self.assertEqual(report["documents"]["ULTRON_NEXT_TASKS.md"], "present")
            self.assertEqual(report["next_tasks"], ["Continue tests."])
            self.assertIsNone(report["branch"])
            self.assertEqual(report["working_tree"], "unknown")
            self.assertIn("no test or deployment", report["notice"].lower())

    def test_markdown_text_not_treated_as_executable_command(self):
        text = "## Hemen yapılacak\n1. $(rm -rf /) SHOULD BE TEXT ONLY\n"
        self.assertEqual(
            resume.extract_next_tasks(text), ["$(rm -rf /) SHOULD BE TEXT ONLY"]
        )


if __name__ == "__main__":
    unittest.main()
