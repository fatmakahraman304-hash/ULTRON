"""Image generation API contract and provider payload handling."""
import base64
import os
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from aiohttp import web
from aiohttp import FormData
from aiohttp.test_utils import TestClient, TestServer
import app as cloud


class FakeContext:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, *args):
        return False


class FakeDB:
    def __init__(self):
        self.messages = []
        self.image_rows = {}
        self.uploaded_rows = {}
        self.next_id = 0
        self.conversations = {}
        self.conversation_writes = []

    def acquire(self):
        return FakeContext(self)

    def transaction(self):
        return FakeContext(self)

    async def fetchval(self, sql, *args):
        if sql.startswith("SELECT user_id FROM conversations"):
            return self.conversations.get(args[0])
        if sql.startswith("INSERT INTO conversations"):
            self.conversation_writes.append(args)
            return args[0] if self.conversations.get(args[0], args[1]) == args[1] else None
        if "RETURNING id" in sql and "INSERT INTO messages" in sql:
            self.next_id += 1
            self.messages.append(args)
            return self.next_id
        return args[0]

    async def fetchrow(self, sql, *args):
        if "FROM generated_images" in sql:
            return self.image_rows.get((args[0], args[1]))
        if "FROM uploaded_images" in sql:
            return self.uploaded_rows.get((args[0], args[1]))
        return None

    async def execute(self, sql, *args):
        if "INSERT INTO generated_images" in sql:
            self.image_rows[(args[0], args[2])] = {
                "mime_type": args[3], "image_data": args[4],
            }
        if "INSERT INTO uploaded_images" in sql:
            self.uploaded_rows[(args[0], args[2])] = {
                "mime_type": args[3], "image_data": args[4],
                "conversation_id": args[1],
            }


class ImageGenerationApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict(os.environ, {"ULTRON_DEVICE_TOKEN": "image_test_only"})
        self.env.start()
        self.db = FakeDB()
        app = web.Application(middlewares=[cloud.auth_middleware])
        app["db"] = self.db
        app.router.add_post("/api/image/generate", cloud.generate_image)
        app.router.add_get("/api/image/generated/{id}", cloud.get_generated_image)
        app.router.add_get("/api/image/uploaded/{id}", cloud.get_uploaded_image)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.env.stop()

    def test_gemini_image_parts_are_extracted_and_limited_to_supported_mime(self):
        image = b"real generated PNG payload"
        part = SimpleNamespace(inline_data=SimpleNamespace(data=image, mime_type="image/png"))
        response = SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))])
        class FakeModels:
            def generate_content(self, **kwargs):
                self.kwargs = kwargs
                return response
        models = FakeModels()
        with patch.object(cloud.genai, "Client", return_value=SimpleNamespace(models=models)), \
             patch.object(cloud, "required_env", return_value="server-only-key"), \
             patch.dict(os.environ, {"GEMINI_IMAGE_MODEL": "test-image-model"}):
            result = cloud._gemini_generate_image("draw a blue circle", b"source", "image/jpeg")
        self.assertEqual(base64.b64decode(result["image_b64"]), image)
        self.assertEqual(result["mime_type"], "image/png")
        self.assertEqual(models.kwargs["config"].response_modalities, ["IMAGE", "TEXT"])
        self.assertEqual(models.kwargs["contents"][1].inline_data.data, b"source")

        bad_response = SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[
            SimpleNamespace(inline_data=SimpleNamespace(data=b"payload", mime_type="image/svg+xml"))]))])
        with patch.object(cloud.genai, "Client", return_value=SimpleNamespace(models=SimpleNamespace(
                 generate_content=lambda **_: bad_response))), \
             patch.object(cloud, "required_env", return_value="server-only-key"):
            with self.assertRaisesRegex(RuntimeError, "output limits"):
                cloud._gemini_generate_image("draw", None, None)

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
        self.assertEqual(len(self.db.image_rows), 1)
        self.assertEqual(data["image_url"], "/api/image/generated/2")
        asset = await self.client.get(
            data["image_url"], headers=headers,
        )
        self.assertEqual(asset.status, 200)
        self.assertEqual(await asset.read(), b"png bytes")
        self.assertEqual(asset.content_type, "image/png")
        self.assertIn("no-store", asset.headers["Cache-Control"])
        self.assertEqual(asset.headers["X-Content-Type-Options"], "nosniff")
        anonymous = await self.client.get(data["image_url"])
        self.assertEqual(anonymous.status, 401)
        unowned = await self.client.get("/api/image/generated/20000", headers=headers)
        self.assertEqual(unowned.status, 404)
        invalid = await self.client.get("/api/image/generated/nope", headers=headers)
        self.assertEqual(invalid.status, 404)
        self.db.image_rows[(900, "another-user")] = {
            "mime_type": "image/png", "image_data": b"other-user-secret",
        }
        cross_owner = await self.client.get("/api/image/generated/900", headers=headers)
        self.assertEqual(cross_owner.status, 404)


    async def test_edit_sends_uploaded_image_bytes_to_provider(self):
        headers = {"Authorization": "Bearer image_test_only"}
        form = FormData()
        form.add_field("prompt", "improve this image")
        form.add_field("image", b"original image bytes", filename="original.png", content_type="image/png")
        with patch.object(cloud, "_gemini_generate_image", return_value={"mime_type": "image/png", "image_b64": "eA=="}) as generate:
            response = await self.client.post("/api/image/generate", data=form, headers=headers)
        self.assertEqual(response.status, 200)
        self.assertEqual(generate.call_args.args, ("improve this image", b"original image bytes", "image/png"))

    async def test_invalid_image_response_does_not_claim_creation(self):
        headers = {"Authorization": "Bearer image_test_only"}
        for invalid in (
            {"mime_type": "image/png", "image_b64": "not base64"},
            {"mime_type": "image/svg+xml", "image_b64": base64.b64encode(b"svg").decode()},
            {"mime_type": "image/png", "image_b64": ""},
        ):
            with patch.object(cloud, "_gemini_generate_image", return_value=invalid):
                response = await self.client.post(
                    "/api/image/generate", json={"prompt": "çiz"}, headers=headers,
                )
            self.assertEqual(response.status, 502)
        self.assertEqual(self.db.messages, [])
        self.assertEqual(self.db.image_rows, {})

    async def test_provider_failure_does_not_create_a_conversation(self):
        headers = {"Authorization": "Bearer image_test_only"}
        form = FormData({"prompt": "draw a blue circle"})
        form._is_multipart = True
        with patch.object(cloud, "_gemini_generate_image", side_effect=RuntimeError("provider unavailable")):
            response = await self.client.post("/api/image/generate", data=form, headers=headers)
        self.assertEqual(response.status, 502)
        self.assertEqual(self.db.conversation_writes, [])
        self.assertEqual(self.db.messages, [])

    async def test_foreign_conversation_is_rejected_before_provider_call(self):
        headers = {"Authorization": "Bearer image_test_only"}
        thread = uuid.uuid4()
        self.db.conversations[thread] = 999
        form = FormData()
        form.add_field("prompt", "draw a blue circle")
        form.add_field("conversation_id", str(thread))
        form._is_multipart = True
        with patch.object(cloud, "_gemini_generate_image") as generate:
            response = await self.client.post("/api/image/generate", data=form, headers=headers)
        self.assertEqual(response.status, 404)
        generate.assert_not_called()
        self.assertEqual(self.db.conversation_writes, [])

    async def test_uploaded_image_and_followup_stay_in_the_same_thread(self):
        from aiohttp import FormData
        thread = str(uuid.uuid4())
        app = web.Application(middlewares=[cloud.auth_middleware])
        app["db"] = self.db
        app.router.add_post("/api/vision", cloud.vision)
        app.router.add_get("/api/image/uploaded/{id}", cloud.get_uploaded_image)
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
            self.assertEqual(payload["uploaded_image_url"], "/api/image/uploaded/1")
            stored = await client.get(payload["uploaded_image_url"], headers=headers)
            self.assertEqual(stored.status, 200)
            self.assertEqual(await stored.read(), b"photo")
            self.assertEqual(stored.headers["Cache-Control"], "private, no-store, max-age=0")
            self.assertEqual(stored.headers["X-Content-Type-Options"], "nosniff")
            anonymous = await client.get(payload["uploaded_image_url"])
            self.assertNotEqual(anonymous.status, 200)
            missing = await client.get("/api/image/uploaded/999999", headers=headers)
            self.assertEqual(missing.status, 404)
            invalid = await client.get("/api/image/uploaded/not-an-id", headers=headers)
            self.assertEqual(invalid.status, 404)
        finally:
            await client.close()


    async def test_vision_provider_failure_keeps_uploaded_photo(self):
        """A failing model must not cancel an otherwise valid photo upload."""
        headers = {"Authorization": "Bearer image_test_only"}
        app = web.Application(middlewares=[cloud.auth_middleware])
        app["db"] = self.db
        app.router.add_post("/api/vision", cloud.vision)
        app.router.add_get("/api/image/uploaded/{id}", cloud.get_uploaded_image)
        client = TestClient(TestServer(app))
        await client.start_server()
        form = FormData()
        form.add_field("image", b"photo data", filename="photo.jpg", content_type="image/jpeg")
        try:
            with patch.object(cloud, "_memory_context", return_value=""), \
                 patch.object(cloud, "_recent_context", return_value=""), \
                 patch.object(cloud, "_gemini_image_reply", side_effect=RuntimeError("offline")):
                response = await client.post("/api/vision", data=form, headers=headers)
            self.assertEqual(response.status, 200)
            data = await response.json()
            self.assertEqual(data["analysis_status"], "failed")
            self.assertIn("kaydedildi", data["reply"])
            self.assertEqual(len(self.db.uploaded_rows), 1)
            photo = await client.get(data["uploaded_image_url"], headers=headers)
            self.assertEqual(photo.status, 200)
            self.assertEqual(await photo.read(), b"photo data")
        finally:
            await client.close()

    async def test_image_followup_reuses_owner_stored_bytes_without_reupload(self):
        headers = {"Authorization": "Bearer image_test_only"}
        app = web.Application(middlewares=[cloud.auth_middleware])
        app["db"] = self.db
        app.router.add_post("/api/vision", cloud.vision)
        client = TestClient(TestServer(app))
        await client.start_server()
        photo = FormData()
        photo.add_field("image", b"stored photo", filename="photo.jpg", content_type="image/jpeg")
        question = FormData()
        question.add_field("image_id", "1")
        question.add_field("question", "Fotoğrafta ne var?")
        try:
            with patch.object(cloud, "_memory_context", return_value=""), \
                 patch.object(cloud, "_recent_context", return_value=""), \
                 patch.object(cloud, "_gemini_image_reply", return_value="Fotoğraf mevcut.") as analyze:
                first = await client.post("/api/vision", data=photo, headers=headers)
                self.assertEqual(first.status, 200)
                first_data = await first.json()
                second = await client.post(
                    "/api/vision?conversation_id=" + first_data["conversation_id"],
                    data=question, headers=headers,
                )
            self.assertEqual(second.status, 200)
            data = await second.json()
            self.assertEqual(data["analysis_status"], "completed")
            self.assertIsNone(data["uploaded_image_url"])
            self.assertEqual(data["conversation_id"], first_data["conversation_id"])
            self.assertEqual(analyze.call_count, 2)
            self.assertEqual(analyze.call_args.args[0], b"stored photo")
            self.assertEqual(len(self.db.uploaded_rows), 1)
        finally:
            await client.close()

    async def test_foreign_conversation_fails_before_upload_or_model_call(self):
        headers = {"Authorization": "Bearer image_test_only"}
        app = web.Application(middlewares=[cloud.auth_middleware])
        app["db"] = self.db
        app.router.add_post("/api/vision", cloud.vision)
        client = TestClient(TestServer(app))
        await client.start_server()
        foreign_id = uuid.uuid4()
        self.db.conversations[foreign_id] = "not-the-current-owner"
        form = FormData()
        form.add_field("image", b"photo", filename="photo.png", content_type="image/png")
        try:
            with patch.object(cloud, "_gemini_image_reply") as analyze:
                response = await client.post(
                    "/api/vision?conversation_id=" + str(foreign_id),
                    data=form, headers=headers,
                )
            self.assertEqual(response.status, 404)
            analyze.assert_not_called()
            self.assertEqual(self.db.uploaded_rows, {})
        finally:
            await client.close()


if __name__ == "__main__":
    unittest.main()
