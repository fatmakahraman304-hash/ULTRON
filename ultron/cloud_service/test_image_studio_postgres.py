"""Real PostgreSQL + HTTP with controlled provider. No real AI generation."""

import asyncio
import os
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
import asyncpg
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import app as cloud
import image_studio as studio
from test_image_studio import result, png

DB = os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL", "")


@unittest.skipUnless(DB, "disposable PostgreSQL required")
class StudioPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.owner = "ci-image-" + uuid.uuid4().hex
        self.other = self.owner + "-b"
        self.env = patch.dict(
            os.environ,
            {
                "GOLGE_IMAGE_PROVIDER":"gemini",
                "ULTRON_DEVICE_TOKEN": "fixture-image",
                "ULTRON_USER_ID": self.owner,
                "GOLGE_IMAGE_ENABLED": "true",
                "GOLGE_IMAGE_BUDGET_APPROVED": "true",
                "GOLGE_IMAGE_DAILY_LIMIT": "20",
                "GOLGE_IMAGE_DAILY_BUDGET_USD": "10",
                "GEMINI_API_KEY": "fixture",
            },
        )
        self.env.start()
        self.userpatch = patch.object(cloud, "DEFAULT_USER_ID", self.owner)
        self.userpatch.start()
        self.pool = await asyncpg.create_pool(DB, min_size=1, max_size=5)
        await self.pool.execute(
            Path(studio.__file__).with_name("schema.sql").read_text()
        )
        await self.pool.execute(
            "DELETE FROM image_requests WHERE user_id LIKE $1", "ci-image-%"
        )
        self.client = await self.make_client()
        self.headers = {"Authorization": "Bearer fixture-image"}
        self.body = dict(
            prompt="Bir Ferrari fotoğrafı oluştur",
            request_id=str(uuid.uuid4()),
            conversation_id=str(uuid.uuid4()),
            cost_approved=True,
            aspect_ratio="9:16",
            style="photo",
        )

    async def make_client(self):
        app = web.Application(middlewares=[cloud.auth_middleware])
        app["db"] = self.pool
        app.router.add_post("/api/image/generate", cloud.generate_image)
        app.router.add_post("/api/image/cancel", studio.cancel)
        app.router.add_get("/api/image/generated/{id}", cloud.get_generated_image)
        app.router.add_get("/api/messages", cloud.list_messages)
        client = TestClient(TestServer(app))
        await client.start_server()
        return client

    async def asyncTearDown(self):
        await self.client.close()
        await self.pool.execute(
            "DELETE FROM conversations WHERE user_id=ANY($1)", [self.owner, self.other]
        )
        await self.pool.execute(
            "DELETE FROM image_requests WHERE user_id=ANY($1)", [self.owner, self.other]
        )
        await self.pool.close()
        self.env.stop()
        self.userpatch.stop()

    async def send(self, **extra):
        return await self.client.post(
            "/api/image/generate", json=self.body | extra, headers=self.headers
        )

    async def test_success_reload_owner_and_restart_idempotency(self):
        with patch.object(
            cloud, "_gemini_generate_image", return_value=result()
        ) as provider:
            first = await self.send()
            self.assertEqual(first.status, 200, await first.text())
            data = await first.json()
            image = await self.client.get(data["image_url"], headers=self.headers)
            self.assertEqual(await image.read(), png())
            history = await self.client.get(
                "/api/messages?conversation_id=" + self.body["conversation_id"],
                headers=self.headers,
            )
            rows = (await history.json())["messages"]
            self.assertTrue(rows[-1]["has_generated_image"])
            await self.client.close()
            self.client = await self.make_client()
            retry = await self.send()
            self.assertEqual(await retry.json(), data)
            provider.assert_called_once()
            with patch.object(cloud, "DEFAULT_USER_ID", self.other):
                denied = await self.client.get(data["image_url"], headers=self.headers)
                self.assertEqual(denied.status, 404)
                denied = await self.send(request_id=str(uuid.uuid4()))
                self.assertEqual(denied.status, 404)
            conflict = await self.send(prompt="changed")
            self.assertEqual(conflict.status, 409)

    async def test_concurrent_duplicate_and_cancellation_discards_late_result(self):
        entered, release = threading.Event(), threading.Event()

        def provider(*a, **k):
            entered.set()
            release.wait(5)
            return result()

        with patch.object(cloud, "_gemini_generate_image", side_effect=provider) as p:
            task = asyncio.create_task(self.send())
            await asyncio.to_thread(entered.wait, 3)
            try:
                duplicate = await self.send()
                self.assertEqual(duplicate.status, 409)
                c = await self.client.post(
                    "/api/image/cancel",
                    json={"request_id": self.body["request_id"]},
                    headers=self.headers,
                )
                self.assertFalse((await c.json())["provider_stopped"])
            finally:
                release.set()
            late = await task
            self.assertEqual(late.status, 409)
            p.assert_called_once()
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT count(*) FROM messages WHERE user_id=$1", self.owner
            ),
            0,
        )

    async def test_early_cancel_other_owner_and_new_turn(self):
        rid = self.body["request_id"]
        with patch.object(cloud, "DEFAULT_USER_ID", self.other):
            await self.client.post(
                "/api/image/cancel", json={"request_id": rid}, headers=self.headers
            )
        with patch.object(cloud, "_gemini_generate_image", return_value=result()) as p:
            self.assertEqual((await self.send()).status, 200)
            new = str(uuid.uuid4())
            await self.client.post(
                "/api/image/cancel", json={"request_id": new}, headers=self.headers
            )
            self.assertEqual((await self.send(request_id=new)).status, 409)
            self.assertEqual(
                (await self.send(request_id=str(uuid.uuid4()))).status, 200
            )
            self.assertEqual(p.call_count, 2)

    async def test_policy_quota_csrf_and_invalid_output(self):
        with patch.object(cloud, "_gemini_generate_image", return_value=result()) as p:
            self.assertEqual((await self.send(cost_approved=False)).status, 403)
            with patch.dict(os.environ, {"GOLGE_IMAGE_ENABLED": "false"}):
                self.assertEqual((await self.send()).status, 503)
            denied = await self.client.post("/api/image/generate", json=self.body)
            self.assertEqual(denied.status, 401)
            p.assert_not_called()
            with patch.dict(os.environ, {"GOLGE_IMAGE_DAILY_LIMIT": "1"}):
                self.assertEqual((await self.send()).status, 200)
                self.assertEqual(
                    (await self.send(request_id=str(uuid.uuid4()))).status, 429
                )
        with patch.object(
            cloud,
            "_gemini_generate_image",
            return_value={"mime_type": "image/png", "image_b64": "eA=="},
        ) as p:
            rid = str(uuid.uuid4())
            self.assertEqual((await self.send(request_id=rid)).status, 502)
            self.assertEqual((await self.send(request_id=rid)).status, 409)
            p.assert_called_once()

    async def test_crashed_worker_never_redispatches(self):
        rid = uuid.UUID(self.body["request_id"])
        await self.pool.execute(
            "INSERT INTO image_requests(user_id,request_id,status,reserved) VALUES($1,$2,'running',true)",
            self.owner,
            rid,
        )
        with patch.object(cloud, "_gemini_generate_image") as p:
            self.assertEqual((await self.send()).status, 409)
            p.assert_not_called()

    async def test_failed_provider_does_not_write_success_and_no_retry(self):
        class Quota(Exception):
            code = 429

        with patch.object(
            cloud, "_gemini_generate_image", side_effect=Quota("secret must not leak")
        ) as p:
            res = await self.send()
            self.assertEqual(res.status, 429)
            self.assertNotIn("secret", await res.text())
            self.assertEqual((await self.send()).status, 409)
            p.assert_called_once()
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT count(*) FROM messages WHERE user_id=$1", self.owner
            ),
            0,
        )

    async def test_browser_origin_required_even_with_valid_cookie(self):
        with patch.dict(
            os.environ, {"ULTRON_SESSION_SECRET": "fixture-session-secret"}
        ):
            cookie = cloud.create_session_cookie(self.owner)
            headers = {
                "Cookie": cloud.COOKIE_NAME + "=" + cookie,
                "Origin": "https://attacker.invalid",
            }
            with patch.object(cloud, "_gemini_generate_image") as p:
                for path in ["/api/image/generate", "/api/image/cancel"]:
                    res = await self.client.post(path, json=self.body, headers=headers)
                    self.assertEqual(res.status, 403)
                headers.pop("Origin")
                res = await self.client.post(
                    "/api/image/generate", json=self.body, headers=headers
                )
                self.assertEqual(res.status, 403)
                p.assert_not_called()
            headers["Origin"] = str(self.client.make_url("/")).rstrip("/")
            with patch.object(cloud, "_gemini_generate_image", return_value=result()):
                res = await self.client.post(
                    "/api/image/generate", json=self.body, headers=headers
                )
                self.assertEqual(res.status, 200)

    async def test_global_concurrent_quota_and_completed_cancel(self):
        entered, release = threading.Event(), threading.Event()

        def provider(*a, **k):
            entered.set()
            release.wait(5)
            return result()

        with patch.dict(os.environ, {"GOLGE_IMAGE_DAILY_LIMIT": "1"}), patch.object(
            cloud, "_gemini_generate_image", side_effect=provider
        ):
            task = asyncio.create_task(self.send())
            await asyncio.to_thread(entered.wait, 3)
            try:
                self.assertEqual(
                    (await self.send(request_id=str(uuid.uuid4()))).status, 429
                )
            finally:
                release.set()
            self.assertEqual((await task).status, 200)
        res = await self.client.post(
            "/api/image/cancel",
            json={"request_id": self.body["request_id"]},
            headers=self.headers,
        )
        self.assertEqual((await res.json())["status"], "already_completed")

    async def test_expired_replay_is_not_reported_as_available(self):
        with patch.object(cloud, "_gemini_generate_image", return_value=result()) as p:
            self.assertEqual((await self.send()).status, 200)
            await self.pool.execute(
                "UPDATE generated_images SET created_at=NOW()-INTERVAL '31 days' WHERE user_id=$1",
                self.owner,
            )
            res = await self.send()
            self.assertEqual(res.status, 410)
            p.assert_called_once()

    async def test_plain_chat_cannot_bypass_image_cost_consent(self):
        app = web.Application(middlewares=[cloud.auth_middleware])
        app["db"] = self.pool
        app.router.add_post("/api/chat", cloud.chat)
        other = TestClient(TestServer(app))
        await other.start_server()
        try:
            with patch.object(cloud, "_gemini_reply") as p:
                res = await other.post(
                    "/api/chat",
                    json={"message": "Ferrari fotoğrafı oluştur"},
                    headers=self.headers,
                )
                self.assertEqual(res.status, 409)
                p.assert_not_called()
        finally:
            await other.close()
