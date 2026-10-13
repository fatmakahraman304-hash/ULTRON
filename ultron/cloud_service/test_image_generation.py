"""Image generation API contract and provider payload handling."""
import base64
import os
import unittest
import uuid
from unittest.mock import patch

from aiohttp import web
from aiohttp import FormData
from aiohttp.test_utils import TestClient, TestServer
import app as cloud


class FakeDB:
    def __init__(self):
        self.messages = []
        self.next_id = 0

    async def fetchval(self, sql, *args):
        if "RETURNING id" in sql and "INSERT INTO messages" in sql:
            self.next_id += 1
            self.messages.append(args)
            return self.next_id
        return args[0]

    async def execute(self, sql, *args):
        self.messages.append(args)


class ImageGenerationApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict(os.environ, {"ULTRON_DEVICE_TOKEN": "image_test_only"})
        self.env.start()
        self.db = FakeDB()
        app = web.Application(middlewares=[cloud.auth_middleware])
        app["db"] = self.db
        app.router.add_post("/api/image/generate", cloud.generate_image)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.env.stop()

    async def test_requires_auth_and_prompt_before_provider(self):
        with patch.object(cloud, "_gemini_generate_image") as generate:
            response = await self.client.post("/api/image/generate", data={"prompt": "a blue circle"})
            self.assertEqual(response.status, 401)
            response = await self.client.post("/api/image/generate", json={"prompt": " "},
                headers={"Authorization": "Bearer image_test_only"})
            self.assertEqual(response.status, 400)
            generate.assert_not_called()

    async def test_returns_real_image_payload_and_threads_request(self):
        headers = {"Authorization": "Bearer image_test_only"}
        form = FormData({"prompt": "draw a blue circle"})
        form._is_multipart = True
        expected = {"mime_type": "image/png", "image_b64": base64.b64encode(b"png bytes").decode(), "model": "test"}
        with patch.object(cloud, "_gemini_generate_image", return_value=expected) as generate:
            response = await self.client.post("/api/image/generate", data=form, headers=headers)
        self.assertEqual(response.status, 200)
        data = await response.json()
        self.assertEqual(data["image_b64"], expected["image_b64"])
        self.assertTrue(data["conversation_id"])
        self.assertEqual(generate.call_args.args, ("draw a blue circle", None, None))
        self.assertEqual(len(self.db.messages), 2)

    async def test_edit_sends_uploaded_image_bytes_to_provider(self):
        headers = {"Authorization": "Bearer image_test_only"}
        form = FormData()
        form.add_field("prompt", "improve this image")
        form.add_field("image", b"original image bytes", filename="original.png", content_type="image/png")
        with patch.object(cloud, "_gemini_generate_image", return_value={"mime_type": "image/png", "image_b64": "eA=="}) as generate:
            response = await self.client.post("/api/image/generate", data=form, headers=headers)
        self.assertEqual(response.status, 200)
        self.assertEqual(generate.call_args.args, ("improve this image", b"original image bytes", "image/png"))

    async def test_uploaded_image_and_followup_stay_in_the_same_thread(self):
        from aiohttp import FormData
        thread = str(uuid.uuid4())
        app = web.Application(middlewares=[cloud.auth_middleware])
        app["db"] = self.db
        app.router.add_post("/api/vision", cloud.vision)
        client = TestClient(TestServer(app))
        await client.start_server()
        form = FormData()
        form.add_field("image", b"photo", filename="photo.png", content_type="image/png")
        form.add_field("question", "Fotoğrafta ne var?")
        headers = {"Authorization": "Bearer image_test_only"}
        try:
            with patch.object(cloud, "_memory_context", return_value=""), \
                 patch.object(cloud, "_recent_context", return_value="Önceki konuşma" ) as recent, \
                 patch.object(cloud, "_gemini_image_reply", return_value="Bir kedi görünüyor."):
                response = await client.post("/api/vision?conversation_id=" + thread, data=form, headers=headers)
            self.assertEqual(response.status, 200)
            payload = await response.json()
            self.assertEqual(payload["conversation_id"], thread)
            self.assertEqual(payload["reply"], "Bir kedi görünüyor.")
            self.assertEqual(recent.call_args.kwargs["conversation_id"], uuid.UUID(thread))
            self.assertEqual(payload["user_message_id"], 1)
            self.assertEqual(payload["assistant_message_id"], 2)
        finally:
            await client.close()


if __name__ == "__main__":
    unittest.main()
