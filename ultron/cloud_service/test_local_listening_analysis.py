"""Offline safety contracts for the local-Qwen listening queue and Ollama."""
from __future__ import annotations

import unittest
from unittest.mock import patch
from pathlib import Path

from listening_analysis import MAX_STAGE_CHARS
from local_listening_bridge import _parse_submission, _checksum
from listening_analysis import ListeningPayloadError
from integration import local_cloud_brain as worker

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class LocalQueueContractTests(unittest.TestCase):
    def test_only_expected_owner_request_with_uuid(self):
        stage, prompt, cap, digest = None, None, None, None
        key = "e98ee043-4144-4a4b-93ea-8b99d6db643f"
        ident, stage, prompt, cap, digest = _parse_submission({
            "request_id": key, "stage": "map",
            "text": "Önemli konuşma notları",
            "part": 1, "total": 2,
        })
        self.assertEqual(str(ident), key)
        self.assertEqual(stage, "map")
        self.assertIn("konuşma notları", prompt)
        self.assertEqual(digest, _checksum(stage, prompt))
        self.assertLessEqual(len(prompt), 14000)

    def test_invalid_submissions_rejected_before_queue(self):
        good = {"request_id": "a4bb98f8-2f21-4914-87c9-a7a43e7304bc",
                "stage": "map", "text": "söz", "part": 1, "total": 2}
        for body in (
            {}, {"stage": "map"}, {**good, "request_id": "not-a-uuid"},
            {**good, "text": "x" * (MAX_STAGE_CHARS + 1)},
            {**good, "part": 99},
            {**good, "stage": "execute"},
        ):
            with self.subTest(body=str(body)[:35]):
                with self.assertRaises(ListeningPayloadError):
                    _parse_submission(body)

    def test_cloud_queue_requires_new_worker_readiness_and_strict_owner(self):
        source = (HERE / "local_listening_bridge.py").read_text(encoding="utf-8")
        self.assertIn("state->>'listening_analysis_ready'='true'", source)
        self.assertIn("state->>'local_chat_ready'='true'", source)
        self.assertIn("last_seen > NOW() - INTERVAL '15 seconds'", source)
        self.assertIn("user_id=$1 AND target='desktop'", source)
        self.assertIn("payload->>'request_id'=$2", source)
        self.assertIn("pg_advisory_xact_lock", source)
        self.assertIn("payload=payload-'text'-'system'", source)
        self.assertIn("_validated_local_reply(result)", source)
        self.assertNotIn("learn_from_owner_message", source)
        self.assertNotIn("INSERT INTO messages", source)
        self.assertNotIn("INSERT INTO memories", source)
        self.assertNotIn("INSERT INTO events", source)

    def test_old_worker_cannot_interpret_transcript_as_agent_task(self):
        desktop = (ROOT / "mark_app.py").read_text(encoding="utf-8")
        new_mode = desktop.index('if payload.get("mode") == "local_listening_analysis":')
        normal_agent = desktop.index('if payload.get("mode") == "local_brain":')
        self.assertLess(new_mode, normal_agent)
        self.assertIn('"listening_analysis_ready": ready', desktop)
        self.assertIn("local_listening_analysis", desktop)
        app = (HERE / "app.py").read_text(encoding="utf8")
        self.assertIn("register_local_listening_routes(app)", app)


class FakeOllamaConfigTests(unittest.TestCase):
    def test_full_analysis_prompt_is_sent_to_installed_local_qwen_without_tools(self):
        full = "baş " + ("uzun metin " * 860) + " SON KARAR BUTON OLMASIN"
        calls = []
        def fake(path, body=None, timeout=8):
            calls.append((path, body, timeout))
            return {"model": "qwen3:4b", "done": True,
                    "done_reason": "stop",
                    "message": {"content": "Karar: buton yok."}}
        with patch.object(worker, "installed_models", return_value=["llava:7b", "qwen3:4b"]):
            with patch.object(worker, "_get_json", side_effect=fake):
                reply = worker.local_listening_analysis(full, "Read-only analysis; do not run tools.")
        self.assertEqual(reply["model"], "qwen3:4b")
        self.assertEqual(reply["provider"], "local-ollama")
        self.assertEqual(len(calls), 1)
        path, payload, _ = calls[0]
        self.assertEqual(path, "/api/chat")
        self.assertEqual(payload["messages"][-1]["content"], full)
        self.assertTrue(payload["stream"] is False)
        self.assertEqual(payload["think"], False)
        self.assertNotIn("tools", payload)
        self.assertIn("SON KARAR", payload["messages"][-1]["content"])

    def test_local_worker_rejects_foreign_model_and_incomplete_analysis(self):
        for returned in (
            {"model": "llava:7b", "done": True,
             "message": {"content": "wrong model"}},
            {"model": "qwen3:4b", "done": False,
             "message": {"content": "half"}},
            {"model": "qwen3:4b", "done": True,
             "done_reason": "length",
             "message": {"content": "cut short"}},
        ):
            with self.subTest(reply=returned):
                with patch.object(worker, "installed_models", return_value=["qwen3:4b"]):
                    with patch.object(worker, "_get_json", return_value=returned):
                        with self.assertRaises(worker.LocalBrainUnavailable):
                            worker.local_listening_analysis("söz", "Trusted system rules.")

    def test_rejects_missing_qwen_without_using_visual_or_cloud_models(self):
        with patch.object(worker, "installed_models", return_value=["llava:7b"]):
            with self.assertRaises(worker.LocalBrainUnavailable):
                worker.local_listening_analysis("söz", "Trusted system rules.")


if __name__ == "__main__":
    unittest.main()
