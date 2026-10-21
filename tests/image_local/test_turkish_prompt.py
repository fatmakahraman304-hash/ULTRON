import asyncio
import json
import threading
import unittest
from unittest.mock import patch

from aiohttp import web
from aiohttp.test_utils import TestServer

from integration import turkish_prompt


class LocalTurkishPrompt(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls = []
        self.content = json.dumps({
            "translation": "In a dim library, an open book and two green apples sit on a wooden table. "
            "The pages should have no readable text. No other books or people are in frame. "
            "Cold blue window light contrasts with warm yellow light from the table lamp."
        })

        async def chat(request):
            self.calls.append((request.path, await request.json()))
            return web.json_response({"message": {"content": self.content}})

        app = web.Application()
        app.router.add_post("/api/chat", chat)
        self.server = TestServer(app)
        await self.server.start_server()

    async def asyncTearDown(self):
        await self.server.close()

    async def test_uses_loopback_json_translation_without_tools(self):
        source = (
            "Loş bir kütüphanede ahşap masanın üzerinde açık bir kitap, yanında iki yeşil elma var. "
            "Kitabın sayfalarında okunabilir yazı olmasın. Kadrajda başka kitap veya kişi bulunmasın. "
            "Pencereden gelen soğuk mavi ışıkla masadaki sıcak sarı lamba ışığı belirgin biçimde ayrışsın."
        )
        with patch.object(turkish_prompt, "OLLAMA_URL", str(self.server.make_url("/")).rstrip("/")):
            translated = await turkish_prompt.translate_turkish_prompt(source)

        self.assertIn("two green apples", translated)
        self.assertIn("no readable text", translated)
        self.assertIn("Cold blue window light", translated)
        self.assertEqual(len(self.calls), 1)
        path, request = self.calls[0]
        self.assertEqual(path, "/api/chat")
        self.assertEqual(request["model"], turkish_prompt._configured_model())
        self.assertFalse(request["think"])
        self.assertFalse(request["stream"])
        self.assertNotIn("tools", request)
        self.assertEqual(
            request["options"],
            {"temperature": 0, "num_predict": 256, "num_gpu": 0},
        )
        self.assertEqual(request["messages"][1]["content"], source)
        self.assertEqual(request["format"]["required"], ["translation"])

    async def test_english_prompt_skips_model(self):
        translated = await turkish_prompt.translate_turkish_prompt("A red car beside a lake.")
        self.assertIsNone(translated)
        self.assertEqual(self.calls, [])

    async def test_cancelled_request_skips_model(self):
        cancelled = threading.Event()
        cancelled.set()
        translated = await turkish_prompt.translate_turkish_prompt(
            "Mersin sahilinde gün batımı.", cancelled=cancelled
        )
        self.assertIsNone(translated)
        self.assertEqual(self.calls, [])

    async def test_malformed_translation_falls_back(self):
        self.content = "not JSON"
        with patch.object(turkish_prompt, "OLLAMA_URL", str(self.server.make_url("/")).rstrip("/")):
            translated = await turkish_prompt.translate_turkish_prompt(
                "Mersin sahilinde gün batımı."
            )
        self.assertIsNone(translated)

    async def test_translation_missing_a_source_sentence_falls_back(self):
        self.content = json.dumps({
            "translation": "In a dim library, there is a book on a table. "
            "The pages should have no readable text. No other books or people are in frame."
        })
        source = (
            "Loş bir kütüphane. Kitabın sayfalarında okunabilir yazı olmasın. "
            "Kadrajda başka kitap veya kişi bulunmasın. Pencereden mavi ışık gelsin."
        )
        with patch.object(turkish_prompt, "OLLAMA_URL", str(self.server.make_url("/")).rstrip("/")):
            translated = await turkish_prompt.translate_turkish_prompt(source)
        self.assertIsNone(translated)


if __name__ == "__main__":
    unittest.main()
