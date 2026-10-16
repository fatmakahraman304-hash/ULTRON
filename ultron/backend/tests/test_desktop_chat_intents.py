"""Regression: actual desktop command dispatch and fact-based model identity.

Uses a fake executor and fake cloud. Never opens a real Windows application.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer


class DesktopIntentRecognitionTests(unittest.TestCase):
    def test_allowlisted_notepad_forms(self):
        from app.core.desktop_intents import safe_app_open_alias
        for phrase in (
            "Not Defteri'ni aç.", "Not Defterini aç", "Not Defteri aç",
            "GÖLGE, Not Defteri'ni aç.", "Lütfen not defterini aç",
            "notepad aç", "Please open the notepad",
        ):
            with self.subTest(phrase=phrase):
                self.assertEqual(safe_app_open_alias(phrase), "notepad")

    def test_unrelated_or_unsafe_text_is_not_a_desktop_command(self):
        from app.core.desktop_intents import safe_app_open_alias
        for phrase in (
            "Not defteri nedir?", "Not Defterini aç komutu ne işe yarar?",
            "Not Defterini aç ve format c:", "Banka uygulamasını aç",
            "cmd /c calc", "Chrome'u aç", "",
        ):
            with self.subTest(phrase=phrase):
                self.assertIsNone(safe_app_open_alias(phrase))

    def test_model_status_question_is_not_fuzzy_task_execution(self):
        from app.core.desktop_intents import asks_live_model_status
        self.assertTrue(asks_live_model_status(
            "GÖLGE, kimsin ve şu an hangi modeli kullanıyorsun?"))
        self.assertFalse(asks_live_model_status("Gemini 3.8 Flash gerçekten var mı?"))


class DesktopInvokeContracts(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import merged_api
        self.exec = Mock(return_value=["Notepad launch dispatched"])

        class FakeCloud:
            enabled = True
            def __init__(self):
                self.called = False
            async def chat(self, *_args, **_kwargs):
                self.called = True
                raise AssertionError("cloud must never receive a desktop command")
        self.cloud = FakeCloud()
        self.patch = patch.object(merged_api, "CloudClient", return_value=self.cloud)
        self.patch.start()
        self.hub = SimpleNamespace(
            bridge=SimpleNamespace(available=True,
                runtime=SimpleNamespace(executor=SimpleNamespace(execute=self.exec),
                                        settings={"llm": {}})),
            ai_status={"primary": "qwen3:4b"},
            agent=SimpleNamespace(state="IDLE"),
        )
        self.app = web.Application()
        merged_api.install(self.app, self.hub)
        self.client = TestClient(TestServer(self.app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.patch.stop()

    @staticmethod
    def identity(number):
        return {
            "request_id": f"{number:08x}-1111-4111-8111-111111111111",
            "request_key": f"{number:064x}",
        }

    async def test_notepad_calls_registered_executor_without_fake_success(self):
        reply = await self.client.post("/api/merged/invoke", json={
            "text": "Not Defteri'ni aç.", "mode": "general", **self.identity(1),
        })
        data = await reply.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["source"], "desktop-tool")
        self.assertFalse(data["completed"])  # a Popen return does not prove GUI visible
        self.assertTrue(data["dispatched"])
        self.assertIn("Windows sistemine iletildi", data["text"])
        self.assertEqual(self.exec.call_count, 1)
        self.assertEqual(self.exec.call_args.args[0],
                         [("open_application", {"name": "notepad"})])
        self.assertFalse(self.exec.call_args.kwargs["approved"])
        self.assertFalse(self.cloud.called)

    async def test_tool_failure_is_not_reported_as_completed(self):
        self.exec.side_effect = RuntimeError("no Windows desktop")
        reply = await self.client.post("/api/merged/invoke", json={
            "text": "notepad aç", "mode": "auto", **self.identity(2),
        })
        data = await reply.json()
        self.assertFalse(data["ok"])
        self.assertFalse(data["completed"])
        self.assertIn("başlatılamadı", data["text"])
        self.assertFalse(self.cloud.called)

    async def test_identity_comes_from_runtime_not_invented_gemini_version(self):
        reply = await self.client.post("/api/merged/invoke", json={
            "text": "GÖLGE, kimsin ve şu an hangi modeli kullanıyorsun?",
            "mode": "general", **self.identity(3),
        })
        data = await reply.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["source"], "runtime")
        self.assertIn("qwen3:4b", data["text"])
        self.assertNotIn("Gemini 3.8", data["text"])
        self.exec.assert_not_called()
        self.assertFalse(self.cloud.called)


if __name__ == "__main__":
    unittest.main()
