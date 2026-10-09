"""Guard the owner-controlled ULTRON -> ChatGPT -> GitHub -> Render proof path.

No Google/Gemini/Postgres credentials are loaded. Test the PURE status logic
and assert request endpoints cannot accept client-provided 'completed' state.
"""
from __future__ import annotations
import ast
import re
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = (ROOT / "development_updates.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SCHEMA = (ROOT / "schema.sql").read_text(encoding="utf-8")


def helpers():
    parsed = ast.parse(SRC)
    functions = [
        node for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name in
        ("dev_intent", "handoff_text", "release_state")
    ]
    module = ast.Module(body=[
        ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
        *functions,
    ], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"re": re, "REPOSITORY": "fatmakahraman304-hash/ULTRON",
                 "BRANCH": "feat/ultron-cloud-shared-memory"}
    exec(compile(module, "<development_updates>", "exec"), namespace)
    return types.SimpleNamespace(**namespace)


class DevelopmentWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dev = helpers()

    def test_recognizes_explicit_self_development_but_not_weather(self):
        for sample in (
            "ULTRON, kendini güncelle ve yeni özellik ekle",
            "ULTRON arayüzünü geliştir",
            "Ultron'daki eksik kodu düzelt",
            "Kendini geliştir",
        ):
            self.assertTrue(self.dev.dev_intent(sample), sample)
        for ordinary in ("Hava durumunu güncelle", "Dünyayı aç",
                         "ULTRON, bilgisayarı aç", "Bana haberleri söyle"):
            self.assertFalse(self.dev.dev_intent(ordinary), ordinary)

    def test_github_handoff_uses_unique_unforgeable_marker(self):
        job = {"id": "123e4567-e89b-12d3-a456-426614174000",
               "prompt": "ULTRON, telefona yeni özelliği ekle", "target": "phone"}
        text = self.dev.handoff_text(job)
        self.assertIn("ULTRON-DEV-123e4567-e89b-12d3-a456-426614174000", text)
        self.assertIn("feat/ultron-cloud-shared-memory", text)
        self.assertIn(job["prompt"], text)
        self.assertIn("test", text.lower())
        self.assertNotIn("OPENAI_API_KEY", text)
        self.assertNotIn("ULTRON_DEVICE_TOKEN", text)

    def test_release_requires_real_code_ci_deploy_and_desktop(self):
        release = self.dev.release_state
        self.assertEqual(release(target="both",tests_ok=False,tests_failed=False,
                                 deployed_ok=False,desktop_ok=False), "tests_pending")
        self.assertEqual(release(target="phone",tests_ok=True,tests_failed=True,
                                 deployed_ok=True,desktop_ok=False), "tests_failed")
        self.assertEqual(release(target="phone",tests_ok=True,tests_failed=False,
                                 deployed_ok=False,desktop_ok=False), "release_pending")
        self.assertEqual(release(target="desktop",tests_ok=True,tests_failed=False,
                                 deployed_ok=True,desktop_ok=False), "desktop_pending")
        self.assertEqual(release(target="both",tests_ok=True,tests_failed=False,
                                 deployed_ok=True,desktop_ok=False), "desktop_pending")
        self.assertEqual(release(target="phone",tests_ok=True,tests_failed=False,
                                 deployed_ok=True,desktop_ok=False), "completed")
        self.assertEqual(release(target="both",tests_ok=True,tests_failed=False,
                                 deployed_ok=True,desktop_ok=True), "completed")

    def test_auth_required_and_persistence_without_client_success_field(self):
        self.assertIn("register_development_routes(app)", APP)
        self.assertIn("CREATE TABLE IF NOT EXISTS dev_requests", SCHEMA)
        self.assertIn("CREATE INDEX IF NOT EXISTS idx_dev_requests_owner_time", SCHEMA)
        self.assertIn("WHERE id=$1 AND user_id=$2", SRC)
        self.assertIn("request[\"auth_kind\"]", SRC) if False else None
        self.assertIn('request.get("auth_kind") != "device"', SRC)
        self.assertIn("desktop_token_required", SRC)
        self.assertIn("uuid.uuid4()", SRC)
        self.assertIn("rate_limit_12_per_hour", SRC)
        self.assertNotIn("body.get('status')", SRC)
        self.assertNotIn('body.get("status")', SRC)
        self.assertNotIn("UPDATE dev_requests SET status='completed'", SRC)

    def test_git_commit_markers_ci_and_render_must_all_be_proved(self):
        self.assertIn('"/commits?sha="', SRC)
        self.assertIn("marker in str(", SRC)
        self.assertIn('"/actions/runs?head_sha="', SRC)
        self.assertIn("r.get(\"head_sha\") == sha", SRC)
        self.assertIn("needed.issubset(green)", SRC)
        self.assertIn('os.getenv("RENDER_GIT_COMMIT"', SRC)
        self.assertIn('_is_ancestor(sha, deployed)', SRC)
        self.assertIn('_is_ancestor(sha, local_sha)', SRC)
        self.assertIn('"completed"', SRC)
        self.assertNotIn('app.router.add_post("/api/dev-requests/{id}/complete"', SRC)

    def test_no_automatic_code_execution_or_hidden_chatgpt_messages(self):
        self.assertNotIn("subprocess.", SRC)
        self.assertNotIn("exec(", SRC)
        self.assertNotIn("eval(", SRC)
        self.assertNotIn("api.openai.com", SRC)
        self.assertNotIn("POST https://chatgpt.com", SRC)
        self.assertIn("ChatGPT chat has no background inbox", SRC)


if __name__ == "__main__":
    unittest.main()
