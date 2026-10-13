"""Provider failures must not echo raw request or credential details."""
import ast
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

from aiohttp import FormData, web
from aiohttp.test_utils import TestClient, TestServer

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import app as cloud


class ProviderErrorPrivacyTests(unittest.IsolatedAsyncioTestCase):
    def test_safe_error_classification_never_echoes_provider_exception(self):
        secret = "AIzaSyD-PRIVATE-REQUEST-CONTENT"
        cases = (
            (RuntimeError(f"API key {secret}; user prompt private"),
             "provider_request_failed"),
            (RuntimeError(f"429 RESOURCE_EXHAUSTED: {secret}"),
             "provider_temporarily_unavailable"),
        )
        for exc, expected in cases:
            with self.subTest(expected=expected):
                label = cloud._safe_provider_error(exc)
                self.assertEqual(label, expected)
                self.assertNotIn(secret, label)
                self.assertNotIn("private", label)

    async def test_vision_failure_does_not_store_or_return_raw_provider_error(self):
        class FakeDB:
            def __init__(self):
                self.events = []

            async def execute(self, sql, *args):
                self.events.append((sql, args))

        secret = "AIzaSyD-PRIVATE-REQUEST-CONTENT"
        db = FakeDB()
        app = web.Application(middlewares=[cloud.auth_middleware])
        app["db"] = db
        app.router.add_post("/api/vision", cloud.vision)
        client = TestClient(TestServer(app))
        await client.start_server()
        form = FormData()
        form.add_field("image", b"photo", filename="photo.png",
                       content_type="image/png")
        form.add_field("question", "What is in this private photo?")
        try:
            with patch.dict(os.environ, {"ULTRON_DEVICE_TOKEN": "error-test-token"}), \
                 patch.object(cloud, "_memory_context", new=AsyncMock(return_value="")), \
                 patch.object(cloud, "_recent_context", new=AsyncMock(return_value="")), \
                 patch.object(cloud, "_gemini_image_reply",
                              side_effect=RuntimeError(f"API key {secret}; private prompt")):
                response = await client.post(
                    "/api/vision", data=form,
                    headers={"Authorization": "Bearer error-test-token"},
                )
            body = await response.text()
        finally:
            await client.close()
        self.assertEqual(response.status, 502)
        self.assertNotIn(secret, body)
        self.assertNotIn("private prompt", body)
        self.assertEqual(len(db.events), 1)
        detail = db.events[0][1][1]
        self.assertEqual(detail, "provider_request_failed")
        self.assertNotIn(secret, detail)

    def test_provider_failure_sinks_use_safe_labels(self):
        source = (HERE / "app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        endpoints = {node.name: node for node in tree.body
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for name in ("vision", "document", "camera_frame", "chat"):
            with self.subTest(endpoint=name):
                text = ast.get_source_segment(source, endpoints[name])
                self.assertIn("_safe_provider_error(exc)", text)
                self.assertNotIn("str(exc)", text)

        live = endpoints["live_voice"]
        live_error_handlers = [handler for handler in ast.walk(live)
                               if isinstance(handler, ast.ExceptHandler)
                               and "gemini_live_error" in ast.dump(handler)]
        self.assertEqual(len(live_error_handlers), 1)
        live_handler = ast.get_source_segment(source, live_error_handlers[0])
        self.assertIn("_safe_provider_error(exc)", live_handler)
        self.assertNotIn("str(exc)", live_handler)

        watcher = next(node for node in ast.walk(live)
                       if isinstance(node, ast.AsyncFunctionDef)
                       and node.name == "watch_desktop_task_result")
        watcher_text = ast.get_source_segment(source, watcher)
        self.assertNotIn("str(exc)", watcher_text)


if __name__ == "__main__":
    unittest.main()
