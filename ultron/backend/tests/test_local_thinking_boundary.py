"""No Qwen reasoning text may escape the local chat/agent/UI boundary."""
import asyncio
import json
import unittest
from unittest.mock import Mock

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer


def make_brain():
    from app.core.brain import Brain
    return Brain({"llm": {"provider": "ollama", "model": "qwen3:4b",
                          "base_url": "http://127.0.0.1:11434",
                          "fast_brain": {"enabled": True}}})


class SynchronousReasoningTests(unittest.TestCase):
    def test_direct_ask_discards_thinking_without_publishing_it(self):
        brain = make_brain()
        brain._post = Mock(return_value={"model": "qwen3:4b", "message": {
            "content": "<think>\nOkay, the user asks who I am.\n</think>\n"
                       "Ben GÖLGE, kişisel asistanınım."
        }})
        answer = brain.ask("Sen kimsin?")
        self.assertEqual(answer, "Ben GÖLGE, kişisel asistanınım.")
        self.assertNotIn("Okay", answer)

    def test_model_only_thinking_does_not_succeed(self):
        brain = make_brain()
        brain._post = Mock(return_value={"message": {"content":
            "<think>\nI must think first"}})
        with self.assertRaisesRegex(RuntimeError, "no publishable"):
            brain.ask("hello")

    def test_agent_chat_strips_thinking_but_preserves_tool_call(self):
        brain = make_brain()
        tool_call = {"function": {"name": "calculate",
                                  "arguments": {"text": "2+3"}}}
        brain._post = Mock(return_value={"message": {
            "content": "<think>\nInternal notes\n</think>\n",
            "tool_calls": [tool_call]}})
        response = brain.chat([{"role": "user", "content": "2+3"}], tools=[{
            "type": "function", "function": {"name": "calculate"}}])
        self.assertEqual(response["message"]["content"], "")
        self.assertEqual(response["message"]["tool_calls"], [tool_call])

    def test_agent_chat_without_visible_answer_is_not_success(self):
        brain = make_brain()
        brain._post = Mock(return_value={"message": {
            "content": "<think>\nUnfinished thinking"}})
        with self.assertRaisesRegex(RuntimeError, "no publishable"):
            brain.chat([{"role": "user", "content": "Hi"}])

    def test_literal_fenced_think_tags_are_preserved(self):
        brain = make_brain()
        literal = "Example:\n```xml\n<think>\nhello\n</think>\n```"
        brain._post = Mock(return_value={"message": {"content": literal}})
        self.assertEqual(brain.ask("Show me literal XML tags"), literal)


class StreamingReasoningTests(unittest.IsolatedAsyncioTestCase):
    async def test_streamed_think_channel_is_never_exposed(self):
        from app.core.brain import Brain
        async def fake_ollama(_request):
            response = web.StreamResponse(headers={
                "Content-Type": "application/x-ndjson"})
            await response.prepare(_request)
            fragments = ["<think>\nOkay, the user asks", " who I am.\n</think>\n",
                         "Ben GÖLGE'yim."]
            for fragment in fragments:
                await response.write((json.dumps({"message": {
                    "content": fragment}}) + "\n").encode())
            await response.write((json.dumps({"done": True,
                "model": "qwen3:4b"}) + "\n").encode())
            await response.write_eof()
            return response
        app = web.Application()
        app.router.add_post("/api/chat", fake_ollama)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            brain = Brain({"llm": {"base_url":
                str(client.make_url("/")).rstrip("/"),
                "model": "qwen3:4b", "fast_brain": {"enabled": True}}})
            answer = await brain.ask_cancellable(
                "Sen kimsin?", cancel_event=asyncio.Event())
            self.assertEqual(answer, "Ben GÖLGE'yim.")
        finally:
            await client.close()

    async def test_stream_with_only_thinking_text_fails_closed(self):
        from app.core.brain import Brain
        async def fake_ollama(request):
            return web.Response(text=(json.dumps({
                "message": {"content": "<think>\nPrivate draft"},
                "done": True, "model": "qwen3:4b"}) + "\n"),
                content_type="application/x-ndjson")
        app = web.Application()
        app.router.add_post("/api/chat", fake_ollama)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            brain = Brain({"llm": {"base_url":
                str(client.make_url("/")).rstrip("/"),
                "model": "qwen3:4b", "fast_brain": {"enabled": True}}})
            with self.assertRaisesRegex(RuntimeError, "empty streamed reply"):
                await brain.ask_cancellable(
                    "Who are you?", cancel_event=asyncio.Event())
        finally:
            await client.close()


if __name__ == "__main__":
    unittest.main()
