"""Provider contract tests use decoded PNG fixtures, never real AI calls."""

import base64
import io
import os
import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from PIL import Image
import image_studio as studio
import app as cloud


def png():
    f = io.BytesIO()
    Image.new("RGB", (64, 64), "cyan").save(f, format="PNG")
    return f.getvalue()


def result():
    return {"mime_type": "image/png", "image_b64": base64.b64encode(png()).decode()}


class StudioTests(unittest.TestCase):
    def test_policy_requires_all_gates(self):
        env = {
            "GOLGE_IMAGE_ENABLED": "true",
            "GOLGE_IMAGE_BUDGET_APPROVED": "true",
            "GOLGE_IMAGE_DAILY_LIMIT": "2",
            "GOLGE_IMAGE_DAILY_BUDGET_USD": "1",
            "GEMINI_API_KEY": "fixture",
        }
        for missing in env:
            with patch.dict(
                os.environ, {k: v for k, v in env.items() if k != missing}, clear=True
            ):
                self.assertFalse(studio.policy()["available"])
        with patch.dict(os.environ, env, clear=True):
            self.assertTrue(studio.policy()["available"])

    def test_decoder_rejects_fake_png_mismatch_empty_svg(self):
        for raw, mime in [
            (b"png bytes", "image/png"),
            (b"", "image/png"),
            (b"<svg/>", "image/svg+xml"),
            (png(), "image/jpeg"),
        ]:
            with self.assertRaises(Exception):
                studio.validate_image(
                    {"mime_type": mime, "image_b64": base64.b64encode(raw).decode()}
                )
        self.assertEqual(studio.validate_image(result())[2], (64, 64))

    def test_sdk_prompt_options_no_retries_no_thought_image(self):
        client = MagicMock()
        client.models.generate_content.return_value = SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    content=SimpleNamespace(
                        parts=[
                            SimpleNamespace(
                                thought=True,
                                inline_data=SimpleNamespace(
                                    data=b"not final", mime_type="image/png"
                                ),
                            ),
                            SimpleNamespace(
                                thought=False,
                                inline_data=SimpleNamespace(
                                    data=png(), mime_type="image/png"
                                ),
                            ),
                        ]
                    )
                )
            ]
        )
        with patch.object(
            cloud.genai, "Client", return_value=client
        ) as factory, patch.object(cloud, "required_env", return_value="fixture"):
            got = cloud._gemini_generate_image(
                "Mersin sahilinde gün batımı", aspect_ratio="9:16", style="cinematic"
            )
        self.assertEqual(got, result() | {"model": studio.MODEL})
        args = client.models.generate_content.call_args.kwargs
        self.assertIn("Mersin sahilinde gün batımı", args["contents"][0])
        self.assertEqual(args["config"].image_config.aspect_ratio, "9:16")
        self.assertEqual(args["config"].image_config.image_size, "1K")
        self.assertEqual(
            factory.call_args.kwargs["http_options"].retry_options.attempts, 1
        )
        client.close.assert_called_once()

    def test_no_image_is_not_success(self):
        client = MagicMock()
        client.models.generate_content.return_value = SimpleNamespace(candidates=[])
        with patch.object(cloud.genai, "Client", return_value=client), patch.object(
            cloud, "required_env", return_value="fixture"
        ):
            with self.assertRaises(RuntimeError):
                cloud._gemini_generate_image("draw")
        client.close.assert_called_once()

    def test_server_intent_distinguishes_creation(self):
        from conversation_persona import classify_intent, classify_image_request

        for text in [
            "Ferrari fotoğrafı oluştur",
            "Bir ejderha ile savaşan şövalye resmi yap",
            "Uzayda yürüyen bir astronot çiz",
            "Create an image of a red car",
        ]:
            self.assertEqual(classify_intent(text).kind, "image_generate")
        for text in [
            "Ferrari fotoğrafı bul",
            "Ferrari hakkında bilgi ver",
            "Bu fotoğrafı analiz et",
            "Fotoğrafı indir",
            "Bir uygulama oluştur",
        ]:
            self.assertIsNone(classify_image_request(text))
        self.assertEqual(
            classify_image_request("Bu görseli daha sinematik yap"), "image_edit"
        )

    def test_budget_is_bounded_and_invalid_values_close_gate(self):
        env = {
            "GOLGE_IMAGE_ENABLED": "true",
            "GOLGE_IMAGE_BUDGET_APPROVED": "true",
            "GOLGE_IMAGE_DAILY_LIMIT": "20",
            "GEMINI_API_KEY": "fixture",
            "GOLGE_IMAGE_DAILY_BUDGET_USD": "0.50",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(studio.policy()["daily_limit"], 1)
        for amount in ["NaN", "Infinity", "-1", "bad", "0.49"]:
            with patch.dict(
                os.environ, env | {"GOLGE_IMAGE_DAILY_BUDGET_USD": amount}, clear=True
            ):
                self.assertFalse(studio.policy()["available"])
