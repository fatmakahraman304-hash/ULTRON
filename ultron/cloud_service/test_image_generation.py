"""Image generation API contract and provider payload handling."""
import base64
from test_image_studio import png, result
import json
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
        self.requests = {}
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
        if "count(*) FROM image_requests" in sql:
            return sum(r.get('reserved',False) for r in self.requests.values())
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
        if "FROM image_requests" in sql:
            return self.requests.get((args[0],args[1]))
        if "FROM generated_images" in sql:
            return self.image_rows.get((args[0], args[1]))
        if "FROM uploaded_images" in sql:
            return self.uploaded_rows.get((args[0], args[1]))
        return None

    async def execute(self, sql, *args):
        if "INSERT INTO image_requests" in sql:
            self.requests[(args[0],args[1])]={'fingerprint':args[3],'status':'running','reserved':True}
        if "UPDATE image_requests" in sql:
            row=self.requests[(args[0],args[1])]
            if "status='completed'" in sql:row.update(status='completed',result=args[2])
            else:row['status']=args[2]
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
        self.env = patch.dict(os.environ, {"GOLGE_IMAGE_PROVIDER":"gemini", "ULTRON_DEVICE_TOKEN": "image_test_only", "GOLGE_IMAGE_ENABLED":"true", "GOLGE_IMAGE_BUDGET_APPROVED":"true", "GOLGE_IMAGE_DAILY_LIMIT":"20", "GOLGE_IMAGE_DAILY_BUDGET_USD":"10", "GEMINI_API_KEY":"fixture"})
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

    def payload(self, prompt="draw a blue circle", **extra):
        return dict(prompt=prompt,request_id=str(uuid.uuid4()),conversation_id=str(uuid.uuid4()),cost_approved=True,**extra)

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
        expected = result()
        with patch.object(cloud, "_gemini_generate_image", return_value=expected) as generate:
            response = await self.client.post("/api/image/generate", json=self.payload(), headers=headers)
        self.assertEqual(response.status, 200)
        data = await response.json()
        self.assertEqual(data["status"], "completed")
        self.assertTrue(data["conversation_id"])
        self.assertEqual(generate.call_args.args, ("draw a blue circle", None, None))
        self.assertEqual(len(self.db.messages), 2)
        self.assertEqual(len(self.db.image_rows), 1)
        self.assertEqual(data["image_url"], "/api/image/generated/2")
        asset = await self.client.get(
            data["image_url"], headers=headers,
        )
        self.assertEqual(asset.status, 200)
        self.assertEqual(await asset.read(), png())
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


    async def test_legacy_edit_is_blocked_without_paid_consent(self):
        headers = {"Authorization": "Bearer image_test_only"}
        form = FormData()
        form.add_field("prompt", "improve this image")
        form.add_field("image", b"original image bytes", filename="original.png", content_type="image/png")
        with patch.object(cloud, "_gemini_generate_image", return_value={"mime_type": "image/png", "image_b64": "eA=="}) as generate:
            response = await self.client.post("/api/image/generate", data=form, headers=headers)
        self.assertEqual(response.status, 400)
        generate.assert_not_called()

    async def test_invalid_image_response_does_not_claim_creation(self):
        headers = {"Authorization": "Bearer image_test_only"}
        for invalid in (
            {"mime_type": "image/png", "image_b64": "not base64"},
            {"mime_type": "image/svg+xml", "image_b64": base64.b64encode(b"svg").decode()},
            {"mime_type": "image/png", "image_b64": ""},
        ):
            with patch.object(cloud, "_gemini_generate_image", return_value=invalid):
                response = await self.client.post(
                    "/api/image/generate", json=self.payload("çiz"), headers=headers,
                )
            self.assertEqual(response.status, 502)
        self.assertEqual(self.db.messages, [])
        self.assertEqual(self.db.image_rows, {})

    async def test_provider_failure_does_not_create_a_conversation(self):
        headers = {"Authorization": "Bearer image_test_only"}
        with patch.object(cloud, "_gemini_generate_image", side_effect=RuntimeError("provider unavailable")):
            response = await self.client.post("/api/image/generate", json=self.payload(), headers=headers)
        self.assertEqual(response.status, 502)
        self.assertEqual(self.db.conversation_writes, [])
        self.assertEqual(self.db.messages, [])

    async def test_foreign_conversation_is_rejected_before_provider_call(self):
        headers = {"Authorization": "Bearer image_test_only"}
        thread = uuid.uuid4()
        self.db.conversations[thread] = 999
        payload=self.payload();payload['conversation_id']=str(thread)
        with patch.object(cloud, "_gemini_generate_image") as generate:
            response = await self.client.post("/api/image/generate", json=payload, headers=headers)
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


    def test_pdf_document_falls_back_without_changing_private_contents(self):
        class ModelUnavailable(Exception):
            code = 404
        records = []
        def generate_content(*, model, contents, config):
            records.append((model, contents, config))
            if len(records) == 1:
                raise ModelUnavailable("private API key and PDF text")
            return SimpleNamespace(text="Belge özeti tamamlandı.")
        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        with patch.object(cloud.genai, "Client", return_value=client), \
             patch.object(cloud, "required_env", return_value="fake"), \
             patch.dict(os.environ, {
                 "GEMINI_DOCUMENT_MODEL": "gemini-3.8-flash",
                 "GEMINI_DOCUMENT_FALLBACK_MODEL": "gemini-3.5-flash-lite",
             }):
            reply = cloud._gemini_pdf_reply(b"%PDF-1.7 fake bytes", "Özetle", "system")
        self.assertEqual(reply, "Belge özeti tamamlandı.")
        self.assertEqual([row[0] for row in records],
                         ["gemini-3.8-flash", "gemini-3.5-flash-lite"])
        self.assertIs(records[0][1], records[1][1])
        self.assertIs(records[0][2], records[1][2])
        self.assertEqual(records[0][1][1].inline_data.mime_type, "application/pdf")
        self.assertEqual(records[0][1][1].inline_data.data, b"%PDF-1.7 fake bytes")

    def test_document_unauthorized_or_invalid_input_is_never_retried(self):
        for code in (400, 401, 403, 415):
            with self.subTest(code=code):
                class AccessOrInputError(Exception):
                    pass
                calls=[]
                def generate_content(**kwargs):
                    calls.append(kwargs["model"])
                    error=AccessOrInputError("private document contents")
                    error.code=code
                    raise error
                client=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
                with patch.object(cloud.genai, "Client", return_value=client), \
                     patch.object(cloud, "required_env", return_value="fake"), \
                     patch.dict(os.environ, {
                         "GEMINI_DOCUMENT_MODEL": "gemini-3.8-flash",
                         "GEMINI_DOCUMENT_FALLBACK_MODEL": "gemini-3.5-flash-lite",
                     }):
                    with self.assertRaises(AccessOrInputError):
                        cloud._gemini_pdf_reply(b"%PDF-1.7 bytes", "Özetle", "system")
                self.assertEqual(calls, ["gemini-3.8-flash"])

    def test_document_fallback_is_bounded_and_safe_error_labels(self):
        class ModelOutage(Exception):
            code=503
        calls=[]
        def generate_content(**kwargs):
            calls.append(kwargs["model"])
            raise ModelOutage("private info")
        client=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        with patch.object(cloud.genai, "Client", return_value=client), \
             patch.object(cloud, "required_env", return_value="fake"), \
             patch.dict(os.environ, {
                 "GEMINI_DOCUMENT_MODEL": "gemini-3.8-flash",
                 "GEMINI_DOCUMENT_FALLBACK_MODEL": "gemini-3.5-flash-lite",
             }):
            with self.assertRaises(ModelOutage) as result:
                cloud._gemini_text_document_reply("Private student content", "Summarize", "system")
        self.assertEqual(calls, ["gemini-3.8-flash", "gemini-3.5-flash-lite"])
        self.assertEqual(cloud._safe_document_error_category(result.exception),
                         "document_provider_temporarily_unavailable")
        self.assertEqual(cloud._safe_document_error_category(
            RuntimeError("User name and API key 123")), "document_request_failed")

    async def test_pdf_document_endpoint_reports_success_and_safe_errors(self):
        from aiohttp import FormData
        app = web.Application(middlewares=[cloud.auth_middleware])
        app["db"] = self.db
        app.router.add_post("/api/document", cloud.document)
        client=TestClient(TestServer(app))
        await client.start_server()
        headers={"Authorization":"Bearer image_test_only"}
        def make_form(content=b"%PDF-1.7\nvalid",filename="test.pdf"):
            form=FormData()
            form.add_field("document",content,filename=filename,content_type="application/pdf")
            form.add_field("question","Bu PDF'yi özetle")
            return form
        try:
            with patch.object(cloud,"_memory_context",return_value=""), \
                 patch.object(cloud,"_recent_context",return_value=""), \
                 patch.object(cloud,"_gemini_pdf_reply",return_value="Başarıyla özetlendi.") as analyze:
                ok=await client.post("/api/document",data=make_form(),headers=headers)
            self.assertEqual(ok.status,200)
            self.assertEqual((await ok.json())["reply"],"Başarıyla özetlendi.")
            analyze.assert_called_once()
            malformed=await client.post("/api/document",data=make_form(b"NOT A PDF"),headers=headers)
            self.assertEqual(malformed.status,400)
            self.assertEqual((await malformed.json())["error"],"invalid_pdf_header")
            class ProviderIssue(Exception):
                code=429
            with patch.object(cloud,"_memory_context",return_value=""), \
                 patch.object(cloud,"_recent_context",return_value=""), \
                 patch.object(cloud,"_gemini_pdf_reply",
                              side_effect=ProviderIssue("PRIVATE FILE CONTENT API KEY")):
                fail=await client.post("/api/document",data=make_form(),headers=headers)
            self.assertEqual(fail.status,502)
            details=await fail.json()
            self.assertEqual(details["error_code"],"document_quota_or_rate_limit")
            self.assertNotIn("PRIVATE",str(details))
            self.assertNotIn("API KEY",str(details))
        finally:
            await client.close()

    def test_vision_recovers_with_alternate_model_for_transient_failure(self):
        """Retry an image once with an installed/configured multimodal model."""
        class ProviderOutage(Exception):
            code = 503
        observed = []
        client = SimpleNamespace(models=SimpleNamespace())
        def generate_content(*, model, contents, config):
            observed.append((model, contents, config))
            if len(observed) == 1:
                raise ProviderOutage("503 unavailable; PRIVATE-DATA-MUST-NOT-LOG")
            return SimpleNamespace(text="Görselde bir ağaç var.")
        client.models.generate_content = generate_content
        with patch.object(cloud.genai, "Client", return_value=client), \
             patch.object(cloud, "required_env", return_value="test-key"), \
             patch.dict(os.environ, {
                 "GEMINI_VISION_MODEL": "gemini-3.8-flash",
                 "GEMINI_VISION_FALLBACK_MODEL": "gemini-3.5-flash-lite",
             }):
            result = cloud._gemini_image_reply(
                b"photo bytes", "image/jpeg", "Fotoğrafta ne var?", "Trusted system")
        self.assertEqual(result, "Görselde bir ağaç var.")
        self.assertEqual([item[0] for item in observed],
                         ["gemini-3.8-flash", "gemini-3.5-flash-lite"])
        self.assertIs(observed[0][1], observed[1][1])
        self.assertIs(observed[0][2], observed[1][2])

    def test_vision_auth_and_bad_image_fail_closed_without_retry(self):
        for status in (400, 401, 403, 415):
            with self.subTest(status=status):
                class ProviderDenied(Exception):
                    code = status
                calls = []
                client = SimpleNamespace(models=SimpleNamespace())
                def generate_content(**kwargs):
                    calls.append(kwargs["model"])
                    raise ProviderDenied("private request details")
                client.models.generate_content = generate_content
                with patch.object(cloud.genai, "Client", return_value=client), \
                     patch.object(cloud, "required_env", return_value="test-key"), \
                     patch.dict(os.environ, {
                         "GEMINI_VISION_MODEL": "gemini-3.8-flash",
                         "GEMINI_VISION_FALLBACK_MODEL": "gemini-3.5-flash-lite",
                     }):
                    with self.assertRaises(ProviderDenied):
                        cloud._gemini_image_reply(b"x", "image/jpeg", "Bu nedir?", "System")
                self.assertEqual(calls, ["gemini-3.8-flash"])

    def test_vision_error_categories_are_bounded_and_never_echo_secrets(self):
        samples = (
            (401, "vision_permission_denied"),
            (403, "vision_permission_denied"),
            (404, "vision_model_unavailable"),
            (429, "vision_quota_or_rate_limit"),
            (503, "vision_provider_temporarily_unavailable"),
            (400, "vision_input_rejected"),
        )
        for status, expected in samples:
            with self.subTest(status=status):
                error = RuntimeError("Private photo request and API key")
                error.code = status
                result = cloud._safe_vision_failure_category(error)
                self.assertEqual(result, expected)
                self.assertNotIn("Private", result)
                self.assertNotIn("key", result)
        self.assertEqual(
            cloud._safe_vision_failure_category(
                RuntimeError("PRIVATE-REQUEST-VALUE")),
            "vision_request_failed",
        )

    def test_vision_fallback_is_bounded_and_same_model_is_not_retried(self):
        class ProviderOutage(Exception):
            code = 429
        calls = []
        client = SimpleNamespace(models=SimpleNamespace())
        def generate_content(**kwargs):
            calls.append(kwargs["model"])
            raise ProviderOutage("429 temporarily limited")
        client.models.generate_content = generate_content
        with patch.object(cloud.genai, "Client", return_value=client), \
             patch.object(cloud, "required_env", return_value="test-key"), \
             patch.dict(os.environ, {
                 "GEMINI_VISION_MODEL": "gemini-3.8-flash",
                 "GEMINI_VISION_FALLBACK_MODEL": "gemini-3.8-flash",
             }):
            with self.assertRaises(ProviderOutage):
                cloud._gemini_image_reply(b"x", "image/jpeg", "", "System")
        self.assertEqual(calls, ["gemini-3.8-flash"])

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
