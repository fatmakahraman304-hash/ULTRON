"""Offline contract tests for a single safe backup Qwen chat attempt.

Does not contact Render, Ollama, Gemini, the queue or the local computer.
"""
import json
import unittest
from unittest.mock import patch

from integration import local_cloud_brain as worker


class Settings:
    def read_text(self, encoding="utf-8"):
        return json.dumps({"llm": {
            "model": "qwen3:8b",
            "fast_brain": {"enabled": True, "speech_tokens": 192},
        }})


def completion(model, content, done_reason="stop"):
    return {"model": model, "done": True,
            "done_reason": done_reason,
            "message": {"content": content}}


class LocalQwenRecoveryTests(unittest.TestCase):
    prompt = "Detaylı analiz yap"

    def run_chat(self, installed, fake_api):
        with patch.object(worker, "_SETTINGS", Settings()):
            with patch.object(worker, "installed_models", return_value=installed):
                with patch.object(worker, "_get_json", side_effect=fake_api):
                    return worker.local_chat(self.prompt, "You are ULTRON.", turns=[])

    def test_incomplete_thinking_recovers_using_installed_backup(self):
        calls = []
        def fake(path, payload, timeout):
            calls.append((path, payload))
            if len(calls) == 1:
                return completion("qwen3:8b", "<think>\nNot finished")
            return completion("qwen3:4b", "Tamam, analiz burada.")
        reply = self.run_chat(["qwen3:8b", "qwen3:4b"], fake)
        self.assertEqual(reply["model"], "qwen3:4b")
        self.assertEqual(reply["provider"], "local-ollama")
        self.assertEqual(reply["reply"], "Tamam, analiz burada.")
        self.assertEqual(len(calls), 2)
        self.assertEqual([p["model"] for _, p in calls], ["qwen3:8b", "qwen3:4b"])
        self.assertEqual(calls[0][1]["messages"], calls[1][1]["messages"])
        self.assertNotIn("tools", calls[1][1])
        self.assertLessEqual(calls[1][1]["options"]["num_predict"], 512)

    def test_valid_primary_does_not_run_any_backup(self):
        calls = []
        def fake(path, payload, timeout):
            calls.append(payload["model"])
            return completion("qwen3:8b", "Birinci model çalışıyor.")
        reply = self.run_chat(["qwen3:8b", "qwen3:4b"], fake)
        self.assertEqual(reply["model"], "qwen3:8b")
        self.assertEqual(calls, ["qwen3:8b"])

    def test_visual_model_is_never_used_as_backup(self):
        calls = []
        def fake(path, payload, timeout):
            calls.append(payload["model"])
            return completion("qwen3:8b", "<think>\nUnfinished")
        with self.assertRaises(worker.LocalBrainUnavailable):
            self.run_chat(["qwen3:8b", "llava:7b"], fake)
        self.assertEqual(calls, ["qwen3:8b"])

    def test_backup_wrong_model_identity_is_rejected(self):
        calls = []
        def fake(path, payload, timeout):
            calls.append(payload["model"])
            if len(calls) == 1:
                return completion("qwen3:8b", "<think>\nUnfinished")
            return completion("not-installed:7b", "Forged answer")
        with self.assertRaisesRegex(worker.LocalBrainUnavailable, "beklenmeyen model"):
            self.run_chat(["qwen3:8b", "qwen3:4b"], fake)
        self.assertEqual(calls, ["qwen3:8b", "qwen3:4b"])

    def test_backup_length_cutoff_is_not_published(self):
        calls = []
        def fake(path, payload, timeout):
            calls.append(payload["model"])
            if len(calls) == 1:
                return completion("qwen3:8b", "<think>\nUnfinished")
            return completion("qwen3:4b", "Partial", done_reason="length")
        with self.assertRaises(worker.LocalBrainUnavailable):
            self.run_chat(["qwen3:8b", "qwen3:4b"], fake)
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
