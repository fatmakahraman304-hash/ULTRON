"""Bounded stock-node SD 1.5 client. No downloads, cloud APIs or global interrupt."""

from __future__ import annotations
import asyncio
import base64
import hashlib
import os
import re
import threading
import time
from urllib.parse import urlsplit
import aiohttp

from integration.turkish_prompt import translate_turkish_prompt

SIZES = {"1:1": (512, 512), "9:16": (384, 640), "16:9": (640, 384)}


def local_config(env=None):
    env = os.environ if env is None else env
    url = env.get("GOLGE_COMFYUI_URL", "http://127.0.0.1:8188")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.username
        or parsed.password
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or not parsed.port
    ):
        raise ValueError("ComfyUI must use an explicit numeric loopback HTTP port")
    checkpoint = env.get("GOLGE_SD15_CHECKPOINT", "")
    if not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,160}\.safetensors", checkpoint):
        raise ValueError(
            "Configure a local SD 1.5 safetensors filename, without a path"
        )
    if env.get("GOLGE_COMFYUI_ENABLED") != "true":
        raise ValueError("Local image generation disabled")
    return url.rstrip("/"), checkpoint


# Conservative, offline prompt preparation. Full-match templates deliberately
# avoid partial translation that might discard negation, subjects or quantities.
_STYLE_HINTS = {
    'natural': 'natural lighting, highly detailed',
    'photo': 'photorealistic, natural lighting, highly detailed',
    'cinematic': 'cinematic composition, cinematic lighting, highly detailed',
    'anime': 'anime illustration, detailed line art',
    '3d': '3D render, detailed materials',
    'digital-art': 'digital art, detailed illustration',
}
_COAST_SUNSET = re.compile(
    r'(?P<place>[\wÇĞİÖŞÜçğıöşü -]{1,80}) (?:sahilinde|kıyısında) '
    r'gün batımı(?:nın)?(?: (?P<photo>gerçekçi))?(?: bir)?'
    r'(?: fotoğraf(?:ını|ı)| görsel(?:ini|i)| resm(?:ini|i))?'
    r'(?: oluştur| çiz| yap)?[.!]?',
    re.IGNORECASE,
)
_TEXT_REQUEST = re.compile(
    r'\b(?:text|lettering|typography|caption|sign|logo|poster|watermark|'
    r'yazı\w*|metin\w*|harf\w*|tabela\w*|afiş\w*|filigran\w*)\b',
    re.IGNORECASE,
)
_NO_TEXT_REQUEST = re.compile(
    r'\b(?:no|without|exclude|avoid|free of|'
    r'(?:must|should|do|does)\s+not\s+(?:include|show|contain|have))\s+'
    r'(?:(?:any|visible|readable|extra|additional)\s+)*'
    r'(?:text|lettering|typography|caption|sign|logo|poster|watermark)\b|'
    r'\b(?:yazı|metin|harf|tabela|afiş|filigran)\w*'
    r'(?:\s+[^\s.!?]+){0,3}\s+olmasın\b',
    re.IGNORECASE,
)


def prepare_sd15_prompt(prompt, style):
    # Return positive/negative CLIP text without network or model calls.
    scene = prompt.strip()
    match = _COAST_SUNSET.fullmatch(scene)
    hints = _STYLE_HINTS[style]
    if match:
        scene = 'sunset on the coast of ' + match.group('place')
        if match.group('photo') and style == 'natural':
            hints = _STYLE_HINTS['photo']
    negative = 'low quality, blurry'
    if _NO_TEXT_REQUEST.search(prompt) or not _TEXT_REQUEST.search(prompt):
        negative += ', text, watermark'
    return scene + ', ' + hints, negative


def build_workflow(prompt, ratio, style, checkpoint, seed):
    if (
        not isinstance(prompt, str)
        or not 1 <= len(prompt.strip()) <= 4000
        or ratio not in SIZES
    ):
        raise ValueError("Invalid image request")
    if style not in ("natural", "photo", "cinematic", "anime", "3d", "digital-art"):
        raise ValueError("Invalid style")
    positive, negative = prepare_sd15_prompt(prompt, style)
    w, h = SIZES[ratio]
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive, "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": w, "height": h, "batch_size": 1},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 20,
                "cfg": 6.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            },
        },
        "6": {
            "class_type": "VAEDecodeTiled",
            "inputs": {
                "samples": ["5", 0],
                "vae": ["1", 2],
                "tile_size": 256,
                "overlap": 64,
                "temporal_size": 64,
                "temporal_overlap": 8,
            },
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "golge-local", "images": ["6", 0]},
        },
    }


async def read_limited(response, limit):
    chunks = []
    size = 0
    async for chunk in response.content.iter_chunked(65536):
        size += len(chunk)
        if size > limit:
            raise RuntimeError("COMFYUI_RESPONSE_TOO_LARGE")
        chunks.append(chunk)
    return b"".join(chunks)


class ComfyUI:
    def __init__(self):
        self.url, self.checkpoint = local_config()

    async def _json(self, session, method, path, body=None):
        async with session.request(
            method, self.url + path, json=body, allow_redirects=False
        ) as r:
            raw = await read_limited(r, 2 * 1024 * 1024)
            if r.status != 200 or len(raw) > 2 * 1024 * 1024:
                raise RuntimeError("COMFYUI_REQUEST_FAILED")
            import json

            return json.loads(raw)

    async def ready(self):
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=3), trust_env=False
            ) as s:
                info = await self._json(s, "GET", "/object_info/CheckpointLoaderSimple")
                choices = info["CheckpointLoaderSimple"]["input"]["required"][
                    "ckpt_name"
                ][0]
                stats = await self._json(s, "GET", "/system_stats")
                return self.checkpoint in choices and any(
                    d.get("type") == "cuda" for d in stats.get("devices", [])
                )
        except Exception:
            return False

    async def generate(self, payload, cancelled: threading.Event):
        # Task payload cannot supply a workflow, endpoint, checkpoint or executable node.
        import uuid

        rid = str(uuid.UUID(payload["request_id"]))
        source_prompt = payload["text"]
        translated_prompt = None
        if not _COAST_SUNSET.fullmatch(source_prompt.strip() if isinstance(source_prompt, str) else ""):
            translated_prompt = await translate_turkish_prompt(
                source_prompt, cancelled=cancelled
            )
        if cancelled.is_set():
            raise RuntimeError("LOCAL_IMAGE_CANCELLED")
        prompt = translated_prompt if translated_prompt is not None else source_prompt
        graph = build_workflow(
            prompt,
            payload["aspect_ratio"],
            payload["style"],
            self.checkpoint,
            int(hashlib.sha256(rid.encode()).hexdigest()[:12], 16),
        )
        prompt_id = None
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15), trust_env=False
        ) as s:
            if cancelled.is_set():
                raise RuntimeError("LOCAL_IMAGE_CANCELLED")
            if not await self.ready():
                raise RuntimeError("COMFYUI_OR_SD15_UNAVAILABLE")
            try:
                if cancelled.is_set():
                    raise RuntimeError("LOCAL_IMAGE_CANCELLED")
                reply = await self._json(
                    s, "POST", "/prompt", {"prompt": graph, "client_id": "golge-" + rid}
                )
                prompt_id = str(uuid.UUID(reply["prompt_id"]))
                deadline = time.monotonic() + 240
                while time.monotonic() < deadline:
                    if cancelled.is_set():
                        raise RuntimeError("LOCAL_IMAGE_OUTPUT_SUPPRESSED")
                    history = (await self._json(s, "GET", "/history/" + prompt_id)).get(
                        prompt_id, {}
                    )
                    if history.get("status", {}).get("status_str") == "error":
                        raise RuntimeError("COMFYUI_GENERATION_FAILED")
                    if history.get("status", {}).get("completed"):
                        images = (
                            history.get("outputs", {}).get("7", {}).get("images", [])
                        )
                        if len(images) != 1:
                            raise RuntimeError("COMFYUI_NO_IMAGE")
                        asset = images[0]
                        name = asset.get("filename", "")
                        if (
                            not re.fullmatch(
                                r"golge-local[A-Za-z0-9_.-]*\.(?:png|webp|jpg|jpeg)",
                                name,
                            )
                            or asset.get("subfolder", "")
                            or asset.get("type") != "output"
                        ):
                            raise RuntimeError("COMFYUI_INVALID_ASSET")
                        async with s.get(
                            self.url + "/view",
                            params={
                                "filename": name,
                                "type": "output",
                                "subfolder": "",
                            },
                            allow_redirects=False,
                        ) as r:
                            raw = await read_limited(r, 8 * 1024 * 1024)
                            if r.status != 200 or len(raw) > 8 * 1024 * 1024:
                                raise RuntimeError("COMFYUI_INVALID_IMAGE")
                            result = {
                                "image_b64": base64.b64encode(raw).decode(),
                                "mime_type": r.content_type,
                            }
                        from ultron.cloud_service.image_studio import validate_image

                        if validate_image(result)[2] != SIZES[payload["aspect_ratio"]]:
                            raise RuntimeError("COMFYUI_UNEXPECTED_SIZE")
                        if cancelled.is_set():
                            raise RuntimeError("LOCAL_IMAGE_OUTPUT_SUPPRESSED")
                        return result | {
                            "request_id": rid,
                            "provider": "comfyui_local",
                            "model": "stable-diffusion-1.5",
                        }
                    await asyncio.sleep(0.4)
                raise RuntimeError("COMFYUI_TIMEOUT_UNKNOWN")
            finally:
                if prompt_id is not None:
                    # Deletes only our pending job. Never /interrupt: that stops other users/jobs.
                    try:
                        await self._json(s, "POST", "/queue", {"delete": [prompt_id]})
                    except Exception:
                        pass


def local_image_ready():
    try:
        return asyncio.run(ComfyUI().ready())
    except Exception:
        return False
