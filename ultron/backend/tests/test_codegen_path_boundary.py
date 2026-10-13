"""Code generation must not mistake a sibling path prefix for project scope."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from codegen import CodeGen


class SilentAudit:
    def write(self, *args):
        pass


class CodegenPathBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def _propose(self, root, files):
        cg = CodeGen(root, SilentAudit(), lambda *args, **kwargs: None)

        async def generated_patch(*args, **kwargs):
            return {"files": files}

        with patch("codegen._llm_patch", generated_patch):
            return await cg.propose("Improve this project", brain=object())

    async def test_proposal_rejects_sibling_directory_with_project_name_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "ULTRON"
            root.mkdir()
            result = await self._propose(root, [
                {"path": "../ULTRON-private/secret.py", "content": "SECRET = 1\n"},
            ])

        self.assertFalse(result["ok"])
        self.assertIn("Proje dışına yazım reddedildi", result["error"])

    async def test_proposal_rejects_security_core_before_owner_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            result = await self._propose(Path(temp) / "ULTRON", [
                {"path": "backend/app/security/vault.py", "content": "SECRET = 1\n"},
            ])
        self.assertFalse(result["ok"])
        self.assertIn("güvenlik çekirdeğine ait", result["error"])

    async def test_proposal_rejects_duplicate_normalized_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            result = await self._propose(Path(temp) / "ULTRON", [
                {"path": "backend/app/tools/task.py", "content": "VALUE = 1\n"},
                {"path": "backend/app/tools/../tools/task.py", "content": "VALUE = 2\n"},
            ])
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "Patch contains duplicate file paths.")

    async def test_proposal_rejects_excessive_file_count_and_payload_size(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "ULTRON"
            too_many = await self._propose(root, [
                {"path": f"generated/file_{index}.py", "content": "VALUE = 1\n"}
                for index in range(13)
            ])
            too_large = await self._propose(root, [
                {"path": "generated/large.py", "content": "x" * (128 * 1024 + 1)}
            ])
            too_much_total = await self._propose(root, [
                {"path": f"generated/part_{index}.py", "content": "x" * (110 * 1024)}
                for index in range(5)
            ])
        self.assertFalse(too_many["ok"])
        self.assertEqual(too_many["error"], "Patch exceeds the 12-file review limit.")
        self.assertFalse(too_large["ok"])
        self.assertEqual(too_large["error"], "A generated file exceeds the 128 KiB review limit.")
        self.assertFalse(too_much_total["ok"])
        self.assertEqual(too_much_total["error"], "Patch exceeds the 512 KiB total review limit.")


if __name__ == "__main__":
    unittest.main()
