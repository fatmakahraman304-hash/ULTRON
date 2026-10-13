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
    async def test_proposal_rejects_sibling_directory_with_project_name_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "ULTRON"
            root.mkdir()
            cg = CodeGen(root, SilentAudit(), lambda *args, **kwargs: None)

            async def outside_patch(*args, **kwargs):
                return {"files": [{"path": "../ULTRON-private/secret.py", "content": "SECRET = 1\n"}]}

            with patch("codegen._llm_patch", outside_patch):
                result = await cg.propose("Update the project code", brain=object())

        self.assertFalse(result["ok"])
        self.assertIn("Proje dışına yazım reddedildi", result["error"])


if __name__ == "__main__":
    unittest.main()
