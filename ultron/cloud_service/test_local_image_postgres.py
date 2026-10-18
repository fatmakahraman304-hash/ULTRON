"""Real isolated Postgres + authenticated queue HTTP; synthetic GPU output only."""

import asyncio
import base64
import io
import json
import os
import uuid
import unittest
from pathlib import Path
from unittest.mock import patch
import asyncpg
from PIL import Image
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import app as cloud
import image_studio
import local_image

DB = os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL", "")


@unittest.skipUnless(DB, "disposable PostgreSQL required")
class LocalImageQueueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.owner = "ci-free-image-" + uuid.uuid4().hex
        self.env = patch.dict(
            os.environ,
            {
                "ULTRON_DEVICE_TOKEN": "fixture-device",
                "ULTRON_SESSION_SECRET": "fixture-cookie",
                "GOLGE_IMAGE_PROVIDER": "comfyui_local",
                "GOLGE_LOCAL_IMAGE_ENABLED": "true",
                "GOLGE_IMAGE_ENABLED": "true",
                "GOLGE_IMAGE_BUDGET_APPROVED": "true",
                "GEMINI_API_KEY": "fixture-never-call",
            },
        )
        self.env.start()
        self.owner_patch = patch.object(cloud, "DEFAULT_USER_ID", self.owner)
        self.owner_patch.start()
        self.paid = patch.object(
            cloud,
            "_gemini_generate_image",
            side_effect=AssertionError("Paid provider called"),
        )
        self.paid_mock = self.paid.start()
        self.pool = await asyncpg.create_pool(DB, min_size=1, max_size=5)
        await self.pool.execute(Path(__file__).with_name("schema.sql").read_text())
        await self.pool.execute(
            "INSERT INTO device_presence(user_id,device,state) VALUES($1,'desktop','{\"local_image_ready\":true}')",
            self.owner,
        )
        app = web.Application(
            middlewares=[cloud.auth_middleware], client_max_size=18 * 1024 * 1024
        )
        app["db"] = self.pool
        app.router.add_post("/api/image/generate", cloud.generate_image)
        app.router.add_get("/api/image/status", image_studio.status)
        app.router.add_get("/api/image/requests/{request_id}", local_image.get_request)
        app.router.add_post("/api/image/cancel", image_studio.cancel)
        app.router.add_get("/api/image/generated/{id}", cloud.get_generated_image)
        app.router.add_get("/api/messages", cloud.list_messages)
        app.router.add_post("/api/device-commands/claim", cloud.claim_device_commands)
        app.router.add_post(
            "/api/device-commands/{id}/complete", cloud.complete_device_command
        )
        self.client = TestClient(TestServer(app))
        await self.client.start_server()
        self.device = {"Authorization": "Bearer fixture-device"}
        self.phone = {
            "Cookie": cloud.COOKIE_NAME + "=" + cloud.create_session_cookie(self.owner),
            "Origin": str(self.client.make_url("")).rstrip("/"),
        }
        self.body = {
            "prompt": "Ferrari fotoğrafı oluştur",
            "request_id": str(uuid.uuid4()),
            "conversation_id": str(uuid.uuid4()),
            "style": "photo",
            "aspect_ratio": "1:1",
        }
        f = io.BytesIO()
        Image.new("RGB", (512, 512), "cyan").save(f, format="PNG")
        self.image = {
            "mime_type": "image/png",
            "image_b64": base64.b64encode(f.getvalue()).decode(),
        }

    async def asyncTearDown(self):
        self.paid_mock.assert_not_called()
        self.paid.stop()
        await self.client.close()
        for table in [
            "device_commands",
            "device_presence",
            "image_requests",
            "conversations",
        ]:
            await self.pool.execute(
                "DELETE FROM " + table + " WHERE user_id=$1", self.owner
            )
        await self.pool.close()
        self.owner_patch.stop()
        self.env.stop()

    async def send(self, **extra):
        return await self.client.post(
            "/api/image/generate", json=self.body | extra, headers=self.phone
        )

    async def claim(self):
        response = await self.client.post(
            "/api/device-commands/claim",
            json={"target": "desktop"},
            headers=self.device,
        )
        return (await response.json())["commands"]

    async def finish(self, job, **extra):
        return await self.client.post(
            "/api/device-commands/" + str(job["id"]) + "/complete",
            headers=self.device,
            json={
                "status": "completed",
                "delivery_attempt": job["delivery_attempt"],
                "result": {"image": self.image},
            }
            | extra,
        )

    async def poll(self, headers=None):
        return await self.client.get(
            "/api/image/requests/" + self.body["request_id"],
            headers=headers or self.phone,
        )

    async def test_phone_queue_laptop_result_history_replay(self):
        config = await (
            await self.client.get("/api/image/status", headers=self.phone)
        ).json()
        self.assertTrue(config["available"])
        self.assertFalse(config["requires_cost_approval"])
        self.assertEqual((await self.send()).status, 202)
        job = (await self.claim())[0]
        self.assertEqual(job["payload"]["mode"], "local_image")
        self.assertEqual(job["max_retries"], 0)
        ack = await self.finish(job)
        self.assertEqual(ack.status, 200, await ack.text())
        result = await (await self.poll()).json()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["model"], "stable-diffusion-1.5")
        image = await self.client.get(result["image_url"], headers=self.phone)
        self.assertEqual(image.status, 200)
        hist = await self.client.get(
            "/api/messages?conversation_id=" + self.body["conversation_id"],
            headers=self.phone,
        )
        self.assertTrue((await hist.json())["messages"][-1]["has_generated_image"])
        # A new module-facing HTTP request reads durable records; no regeneration.
        self.assertEqual(await (await self.send()).json(), result)
        self.assertTrue((await (await self.finish(job)).json())["replayed"])
        stored = await self.pool.fetchval(
            "SELECT result FROM device_commands WHERE id=$1", job["id"]
        )
        self.assertNotIn("image_b64", stored)
        other = {
            "Cookie": cloud.COOKIE_NAME
            + "="
            + cloud.create_session_cookie("unrelated-owner")
        }
        self.assertEqual((await self.poll(other)).status, 404)
        self.assertEqual(
            (await self.client.get(result["image_url"], headers=other)).status, 404
        )

    async def test_duplicate_race_and_conflicting_uuid(self):
        replies = await asyncio.gather(self.send(), self.send())
        self.assertEqual([r.status for r in replies], [202, 202])
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT count(*) FROM device_commands WHERE user_id=$1", self.owner
            ),
            1,
        )
        self.assertEqual((await self.send(prompt="changed")).status, 409)
        self.assertEqual((await self.send(request_id=str(uuid.uuid4()))).status, 429)

    async def test_offline_disabled_and_unknown_provider_never_fall_back(self):
        for state in ["offline", "disabled", "unknown"]:
            if state == "offline":
                await self.pool.execute(
                    "UPDATE device_presence SET last_seen=NOW()-INTERVAL '1 minute' WHERE user_id=$1",
                    self.owner,
                )
            else:
                await self.pool.execute(
                    "UPDATE device_presence SET last_seen=NOW() WHERE user_id=$1",
                    self.owner,
                )
            with patch.dict(
                os.environ,
                (
                    {"GOLGE_LOCAL_IMAGE_ENABLED": "false"}
                    if state == "disabled"
                    else (
                        {"GOLGE_IMAGE_PROVIDER": "unknown"}
                        if state == "unknown"
                        else {}
                    )
                ),
            ):
                self.assertEqual((await self.send()).status, 503)
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT count(*) FROM device_commands WHERE user_id=$1", self.owner
            ),
            0,
        )

    async def test_cancel_and_stale_generation_cannot_save(self):
        await self.send()
        job = (await self.claim())[0]
        c = await self.client.post(
            "/api/image/cancel",
            json={"request_id": self.body["request_id"]},
            headers=self.phone,
        )
        self.assertFalse((await c.json())["provider_stopped"])
        self.assertEqual((await self.finish(job)).status, 409)
        self.assertEqual((await self.poll()).status, 409)
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT count(*) FROM messages WHERE user_id=$1", self.owner
            ),
            0,
        )

    async def test_fence_invalid_png_and_phone_cannot_complete(self):
        await self.send()
        job = (await self.claim())[0]
        self.assertEqual(
            (
                await self.finish(job, delivery_attempt=job["delivery_attempt"] + 1)
            ).status,
            409,
        )
        image = self.image
        self.image = {"mime_type": "image/png", "image_b64": "aGVsbG8="}
        self.assertEqual((await self.finish(job)).status, 400)
        self.image = image
        response = await self.client.post(
            "/api/device-commands/" + str(job["id"]) + "/complete",
            headers=self.phone,
            json={
                "status": "completed",
                "delivery_attempt": job["delivery_attempt"],
                "result": {"image": self.image},
            },
        )
        self.assertEqual(response.status, 404)
        self.assertEqual((await self.finish(job)).status, 200)

    async def test_csrf_conversation_isolation_and_lease_failure(self):
        self.assertEqual(
            (
                await self.client.post(
                    "/api/image/generate",
                    json=self.body,
                    headers=self.phone | {"Origin": "https://attacker.invalid"},
                )
            ).status,
            403,
        )
        cid = uuid.uuid4()
        await self.pool.execute(
            "INSERT INTO conversations(id,user_id,title) VALUES($1,'other','private')",
            cid,
        )
        try:
            self.assertEqual((await self.send(conversation_id=str(cid))).status, 404)
        finally:
            await self.pool.execute("DELETE FROM conversations WHERE id=$1", cid)
        await self.send()
        job = (await self.claim())[0]
        await self.pool.execute(
            "UPDATE device_commands SET delivered_at=NOW()-INTERVAL '25 seconds' WHERE id=$1",
            job["id"],
        )
        self.assertEqual(await self.claim(), [])
        self.assertEqual((await self.poll()).status, 409)
        self.assertEqual((await self.finish(job)).status, 409)

    async def test_phone_to_comfy_transport_to_private_saved_image(self):
        # Real HTTP through all adapters, synthetic CUDA metadata and PNG; no GPU.
        import threading
        from integration.comfyui_image import ComfyUI

        pid = str(uuid.uuid4())
        calls = []

        async def comfy(req):
            calls.append(req.path)
            if req.path == "/object_info/CheckpointLoaderSimple":
                return web.json_response(
                    {
                        "CheckpointLoaderSimple": {
                            "input": {"required": {"ckpt_name": [["sd15.safetensors"]]}}
                        }
                    }
                )
            if req.path == "/system_stats":
                return web.json_response({"devices": [{"type": "cuda"}]})
            if req.path == "/prompt":
                graph = (await req.json())["prompt"]
                self.assertIn("Ferrari", graph["2"]["inputs"]["text"])
                return web.json_response({"prompt_id": pid})
            if req.path.startswith("/history/"):
                return web.json_response(
                    {
                        pid: {
                            "status": {"completed": True},
                            "outputs": {
                                "7": {
                                    "images": [
                                        {
                                            "filename": "golge-local_fixture.png",
                                            "subfolder": "",
                                            "type": "output",
                                        }
                                    ]
                                }
                            },
                        }
                    }
                )
            if req.path == "/view":
                # Deliberately split network chunks: read(n) is not a complete-body read.
                response = web.StreamResponse(headers={"Content-Type": "image/png"})
                await response.prepare(req)
                raw = base64.b64decode(self.image["image_b64"])
                await response.write(raw[:20])
                await asyncio.sleep(0.01)
                await response.write(raw[20:])
                await response.write_eof()
                return response
            return web.json_response({})

        app = web.Application()
        app.router.add_route("*", "/{path:.*}", comfy)
        server = TestServer(app)
        await server.start_server()
        try:
            self.assertEqual((await self.send()).status, 202)
            job = (await self.claim())[0]
            with patch.dict(
                os.environ,
                {
                    "GOLGE_COMFYUI_ENABLED": "true",
                    "GOLGE_SD15_CHECKPOINT": "sd15.safetensors",
                    "GOLGE_COMFYUI_URL": str(server.make_url("")).rstrip("/"),
                },
            ):
                output = await ComfyUI().generate(job["payload"], threading.Event())
            self.image = output
            self.assertEqual((await self.finish(job)).status, 200)
            saved = await (await self.poll()).json()
            self.assertEqual((saved["width"], saved["height"]), (512, 512))
            self.assertEqual(
                (await self.client.get(saved["image_url"], headers=self.phone)).status,
                200,
            )
            self.assertNotIn("/interrupt", calls)
            self.assertEqual(calls.count("/prompt"), 1)
        finally:
            await server.close()
