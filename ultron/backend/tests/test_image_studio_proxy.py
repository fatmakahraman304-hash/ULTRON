"""Desktop Cloud transport uses existing credentials, fixed routes, no redirects."""

import asyncio
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import merged_api
from cloud_client import CloudClient


class ImageProxyTests(unittest.IsolatedAsyncioTestCase):
    async def test_auth_origin_fixed_path_and_binary_response(self):
        proxy = SimpleNamespace(
            image_request=AsyncMock(
                return_value=(200, b"controlled image", "image/png")
            )
        )
        with patch.dict(
            os.environ, {"MARK_ULTRON_TOKEN": "fixture-desktop"}
        ), patch.object(merged_api, "CloudClient", return_value=proxy):
            app = web.Application()
            merged_api.install(app, SimpleNamespace())
            client = TestClient(TestServer(app))
            await client.start_server()
        try:
            path = "/api/merged/image-studio/generated/42"
            self.assertEqual((await client.get(path)).status, 401)
            headers = {"X-MARK-Token": "fixture-desktop"}
            res = await client.get(path, headers=headers)
            self.assertEqual(res.status, 200)
            self.assertEqual(await res.read(), b"controlled image")
            self.assertIn("no-store", res.headers["Cache-Control"])
            proxy.image_request.assert_awaited_once_with(
                "GET", "/api/image/generated/42", None
            )
            cookie = {
                "Cookie": "mark_session=fixture-desktop",
                "Origin": "https://foreign.invalid",
            }
            self.assertEqual(
                (
                    await client.post(
                        "/api/merged/image-studio/generate", json={}, headers=cookie
                    )
                ).status,
                401,
            )
            self.assertEqual(
                (
                    await client.get(
                        "/api/merged/image-studio/https://foreign.invalid",
                        headers=headers,
                    )
                ).status,
                404,
            )
        finally:
            await client.close()

    async def test_cloud_disabled_and_arbitrary_paths_rejected(self):
        with patch.dict(
            os.environ, {"ULTRON_CLOUD_URL": "", "ULTRON_DEVICE_TOKEN": ""}
        ):
            client = CloudClient()
        try:
            self.assertEqual(
                (await client.image_request("GET", "/api/image/status"))[0], 503
            )
            with self.assertRaises(ValueError):
                await client.image_request("GET", "https://attacker.invalid")
        finally:
            client._executor.shutdown()
            client._local_executor.shutdown()

    async def test_redirect_handler_will_not_forward_authentication(self):
        with patch.dict(
            os.environ,
            {
                "ULTRON_CLOUD_URL": "https://cloud.example",
                "ULTRON_DEVICE_TOKEN": "fixture",
            },
        ):
            client = CloudClient()

        class Response:
            status = 200
            headers = SimpleNamespace(get_content_type=lambda: "application/json")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self, n):
                return b'{"available":false}'

        captured = []

        def opener(handler):
            captured.append(handler)
            return SimpleNamespace(open=lambda req, timeout: Response())

        try:
            with patch("urllib.request.build_opener", side_effect=opener):
                self.assertEqual(
                    (await client.image_request("GET", "/api/image/status"))[0], 200
                )
            self.assertIsNone(
                captured[0].redirect_request(
                    None, None, 302, "", {}, "https://foreign.invalid"
                )
            )
        finally:
            client._executor.shutdown()
            client._local_executor.shutdown()
