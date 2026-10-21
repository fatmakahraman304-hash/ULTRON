import unittest
from integration.comfyui_image import build_workflow, local_config


class ComfyContracts(unittest.TestCase):
    def test_loopback_only_and_safetensors(self):
        for url in [
            "https://example.com",
            "http://localhost:8188",
            "http://127.0.0.1:8188/evil",
            "http://169.254.169.254",
        ]:
            with self.assertRaises(ValueError):
                local_config(
                    {
                        "GOLGE_COMFYUI_ENABLED": "true",
                        "GOLGE_COMFYUI_URL": url,
                        "GOLGE_SD15_CHECKPOINT": "sd15.safetensors",
                    }
                )

    def test_explicit_no_text_request_uses_negative_prompt(self):
        graph = build_workflow(
            "A book on a table. Its pages should have no readable text.",
            "1:1", "photo", "sd15.safetensors", 7,
        )
        self.assertEqual(
            graph["3"]["inputs"]["text"],
            "low quality, blurry, text, watermark",
        )

    def test_requested_visible_text_is_not_negated(self):
        graph = build_workflow(
            "A poster with visible text and a logo.",
            "1:1", "photo", "sd15.safetensors", 8,
        )
        self.assertEqual(graph["3"]["inputs"]["text"], "low quality, blurry")

    def test_fixed_low_vram_graph(self):
        graph = build_workflow("Ferrari", "9:16", "photo", "sd15.safetensors", 42)
        latent = graph["4"]["inputs"]
        self.assertEqual(
            (latent["width"], latent["height"], latent["batch_size"]), (384, 640, 1)
        )
        self.assertEqual(graph["5"]["inputs"]["steps"], 20)
        self.assertEqual(graph["6"]["class_type"], "VAEDecodeTiled")
        self.assertEqual(graph["6"]["inputs"]["tile_size"], 256)
        self.assertEqual(graph["6"]["inputs"]["temporal_size"], 64)
        self.assertEqual(graph["6"]["inputs"]["temporal_overlap"], 8)
        self.assertEqual(
            set(n["class_type"] for n in graph.values()),
            {
                "CheckpointLoaderSimple",
                "CLIPTextEncode",
                "EmptyLatentImage",
                "KSampler",
                "VAEDecodeTiled",
                "SaveImage",
            },
        )
        self.assertEqual(graph["2"]["inputs"]["text"], "Ferrari, photorealistic, natural lighting, highly detailed")


import asyncio
import io
import os
import threading
import uuid
from unittest.mock import AsyncMock, patch
from PIL import Image
from aiohttp import web
from aiohttp.test_utils import TestServer
from integration.comfyui_image import ComfyUI


class ComfyTransport(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls = []
        self.pid = str(uuid.uuid4())
        self.bad = False
        self.cancel = None
        f = io.BytesIO()
        Image.new("RGB", (512, 512), "cyan").save(f, format="PNG")
        self.png = f.getvalue()

        async def api(req):
            body = await req.json() if req.method == "POST" else None
            self.calls.append((req.method, req.path, body))
            if req.path == "/object_info/CheckpointLoaderSimple":
                return web.json_response(
                    {
                        "CheckpointLoaderSimple": {
                            "input": {"required": {"ckpt_name": [["sd15.safetensors"]]}}
                        }
                    }
                )
            if req.path == "/system_stats":
                return web.json_response(
                    {"devices": [{"type": "cuda", "vram_total": 4 * 1024**3}]}
                )
            if req.path == "/prompt":
                return web.json_response({"prompt_id": self.pid})
            if req.path.startswith("/history/"):
                if self.cancel:
                    self.cancel.set()
                return web.json_response(
                    {
                        self.pid: {
                            "status": {"completed": True},
                            "outputs": {
                                "7": {
                                    "images": [
                                        {
                                            "filename": (
                                                "../../secret.png"
                                                if self.bad
                                                else "golge-local_00001_.png"
                                            ),
                                            "type": "output",
                                            "subfolder": "",
                                        }
                                    ]
                                }
                            },
                        }
                    }
                )
            if req.path == "/view":
                return web.Response(body=self.png, content_type="image/png")
            return web.json_response({})

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", api)
        self.server = TestServer(app)
        await self.server.start_server()
        self.env = patch.dict(
            os.environ,
            {
                "GOLGE_COMFYUI_ENABLED": "true",
                "GOLGE_COMFYUI_URL": str(self.server.make_url("")).rstrip("/"),
                "GOLGE_SD15_CHECKPOINT": "sd15.safetensors",
            },
        )
        self.env.start()
        self.client = ComfyUI()
        self.payload = {
            "request_id": str(uuid.uuid4()),
            "text": "Ferrari",
            "aspect_ratio": "1:1",
            "style": "photo",
        }

    async def asyncTearDown(self):
        self.env.stop()
        await self.server.close()

    async def test_real_http_contract_and_scoped_cleanup(self):
        result = await self.client.generate(self.payload, threading.Event())
        self.assertEqual(result["provider"], "comfyui_local")
        self.assertTrue(result["image_b64"])
        post = next(c[2] for c in self.calls if c[1] == "/prompt")
        self.assertEqual(post["prompt"]["4"]["inputs"]["batch_size"], 1)
        self.assertIn(("POST", "/queue", {"delete": [self.pid]}), self.calls)
        self.assertNotIn("/interrupt", [c[1] for c in self.calls])

    @patch("integration.comfyui_image.translate_turkish_prompt", new_callable=AsyncMock)
    async def test_turkish_prompt_is_translated_before_comfy_dispatch(self, translate_prompt):
        source = "Loş bir kütüphanede iki yeşil elma var."
        translate_prompt.return_value = "Two green apples in a dim library."
        self.payload["text"] = source

        await self.client.generate(self.payload, threading.Event())

        translate_prompt.assert_awaited_once()
        graph = next(c[2]["prompt"] for c in self.calls if c[1] == "/prompt")
        self.assertEqual(
            graph["2"]["inputs"]["text"],
            "Two green apples in a dim library., photorealistic, natural lighting, highly detailed",
        )

    async def test_asset_path_rejected(self):
        self.bad = True
        with self.assertRaisesRegex(RuntimeError, "INVALID_ASSET"):
            await self.client.generate(self.payload, threading.Event())
        self.assertNotIn("/view", [c[1] for c in self.calls])

    async def test_late_cancel_never_returns_output(self):
        self.cancel = threading.Event()
        with self.assertRaisesRegex(RuntimeError, "SUPPRESSED"):
            await self.client.generate(self.payload, self.cancel)
        self.assertNotIn("/interrupt", [c[1] for c in self.calls])

    async def test_invalid_pixels_and_size_rejected(self):
        self.png = b"not png"
        with self.assertRaises(Exception):
            await self.client.generate(self.payload, threading.Event())

    async def test_cancel_before_dispatch(self):
        event = threading.Event()
        event.set()
        with self.assertRaisesRegex(RuntimeError, "CANCELLED"):
            await self.client.generate(self.payload, event)
        self.assertEqual(self.calls, [])


class LowVRAMLauncher(unittest.TestCase):
    def test_launcher_never_exposes_network_or_custom_nodes(self):
        from scripts.golge_comfyui_start import command, FLAGS

        self.assertEqual(FLAGS[FLAGS.index("--listen") + 1], "127.0.0.1")
        self.assertIn("--disable-all-custom-nodes", FLAGS)
        self.assertIn("--lowvram", FLAGS)
        self.assertIn("--cpu-vae", FLAGS)
        with self.assertRaises(ValueError):
            command({"GOLGE_COMFYUI_HOME": "/not-installed"})
