"""Explicit research-intent integration contracts; no external network/model."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verified_research import (
    append_research_sources, build_research_prompt_block,
    extract_research_query, research_for_chat,
)


class _FixtureEngine:
    def __init__(self):
        self.calls = []
        self.closed = False

    def research(self, query, *, max_sources, store):
        self.calls.append((query, max_sources, store))
        return {
            "ok": True, "status": "sources_read", "evidence_level": "source_pages_read",
            "confidence": 0.0, "citations": ["https://example.org/report"],
            "synthesis": {"findings": [{"title": "Report", "url": "https://example.org/report",
                "accessed_at": "2026-10-14T00:00:00Z", "excerpt": "Measured value is 42 kWh.",
                "basis": "source_page_excerpt", "page_read": True}],
                "unread_sources": [{"title": "Fake result", "read_status": "timeout"}]},
        }

    def close(self):
        self.closed = True


class VerifiedResearchIntegrationTests(unittest.TestCase):
    def test_normal_chat_never_starts_search_or_reader(self):
        engine = _FixtureEngine()
        result = asyncio.run(research_for_chat("Selam, nasılsın?", engine_factory=lambda: engine))
        self.assertIsNone(result)
        self.assertEqual(engine.calls, [])
        self.assertFalse(engine.closed)

    def test_research_is_explicit_bounded_and_never_persists_search_text(self):
        engine = _FixtureEngine()
        result = asyncio.run(research_for_chat(
            "GÖLGE, internette pil kapasitesi hakkında kaynakları araştır",
            engine_factory=lambda: engine,
        ))
        self.assertEqual(engine.calls, [("pil kapasitesi hakkında kaynakları", 5, False)])
        self.assertTrue(engine.closed)
        self.assertEqual(result["evidence_level"], "source_pages_read")

    def test_sensitive_query_is_not_sent_to_external_search(self):
        engine = _FixtureEngine()
        result = asyncio.run(research_for_chat(
            "Research this API key sk-proj-12345678901234567890", engine_factory=lambda: engine
        ))
        self.assertEqual(result["status"], "research_blocked_sensitive_input")
        self.assertEqual(engine.calls, [])
        self.assertFalse(engine.closed)

    def test_prompt_serializes_only_read_excerpt_as_untrusted_data(self):
        result = _FixtureEngine().research("battery", max_sources=3, store=False)
        block = build_research_prompt_block(result)
        self.assertIn("untrusted", block.lower())
        self.assertIn("Measured value is 42 kWh.", block)
        self.assertNotIn("Fake result", block)
        self.assertNotIn("timeout", block)
        self.assertIn('"claim_verification":"not_performed"', block)

    def test_final_response_lists_only_real_read_sources_or_reports_no_read(self):
        result = _FixtureEngine().research("battery", max_sources=3, store=False)
        answer = append_research_sources("The value is 42 kWh.", result)
        self.assertIn("https://example.org/report", answer)
        self.assertNotIn("Fake result", answer)
        self.assertIn("Cümle 1: olası eşleşme", answer)
        wrong = append_research_sources("The value is 48 kWh.", result)
        self.assertIn("Cümle 1: kaynak excerpt'iyle eşleşme bulunmadı", wrong)
        failed = append_research_sources("A general answer.", {
            "status": "sources_not_read", "citations": [], "synthesis": {"findings": []}
        })
        self.assertIn("kaynak sayfaları okunamadı", failed.lower())

    def test_cloud_chat_executes_research_only_on_research_route_and_cites_reads(self):
        import app as cloud

        class Pool:
            def __init__(self):
                self.message_id = 0

            async def fetchval(self, sql, *args):
                if "INSERT INTO conversations" in sql:
                    return args[0]
                if "INSERT INTO messages" in sql:
                    self.message_id += 1
                    return self.message_id
                raise AssertionError(sql)

            async def execute(self, sql, *args):
                return "UPDATE 1"

        class Request(dict):
            def __init__(self, message):
                super().__init__(user_id="ci-research-owner", device_id="ci-phone")
                self.app = {"db": Pool()}
                self.query = {}
                self.match_info = {}
                self._message = message

            async def json(self):
                return {"message": self._message}

        evidence = _FixtureEngine().research("battery", max_sources=3, store=False)
        gemini = Mock(return_value="The measured value is 42 kWh.")

        async def research(message):
            return evidence

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-fixture-not-a-real-key"}), \
             patch.object(cloud, "load_contextual_thread_turns", new=AsyncMock(return_value=[])), \
             patch.object(cloud, "_memory_context", new=AsyncMock(return_value="owner memory")), \
             patch.object(cloud, "_gemini_reply", new=gemini), \
             patch.object(cloud, "research_for_chat", new=AsyncMock(side_effect=research)) as run:
            normal = asyncio.run(cloud.chat(Request("Selam, nasılsın?")))
            self.assertEqual(json.loads(normal.text)["reply"], "The measured value is 42 kWh.")
            run.assert_not_awaited()

            research_response = asyncio.run(
                cloud.chat(Request("GÖLGE, araştır: battery capacity"))
            )
            payload = json.loads(research_response.text)
            self.assertEqual(run.await_count, 1)
            self.assertIn("untrusted public web data", gemini.call_args.args[1])
            self.assertIn("Measured value is 42 kWh.", gemini.call_args.args[1])
            self.assertIn("https://example.org/report", payload["reply"])
            self.assertNotIn("Fake result", payload["reply"])

    def test_cloud_chat_cancel_suppresses_late_gemini_reply_without_persisting_it(self):
        import threading
        import app as cloud

        class Pool:
            def __init__(self):
                self.message_id = 0
                self.messages = []
            async def fetchval(self, sql, *args):
                if "INSERT INTO conversations" in sql:
                    return args[0]
                if "INSERT INTO messages" in sql:
                    self.message_id += 1
                    self.messages.append(("assistant" if "'assistant'" in sql else "user", args[2]))
                    return self.message_id
                raise AssertionError(sql)
            async def execute(self, *_args):
                return "UPDATE 1"

        app_state = {"db": Pool()}
        request_id = "81b4f437-f792-43fc-910e-1a58e977a93d"
        request_key = "f" * 64

        class Request(dict):
            def __init__(self, body, user="cancel-owner", device="cancel-phone"):
                super().__init__(user_id=user, device_id=device)
                self.app = app_state
                self.query = {}
                self.match_info = {}
                self._body = body
            async def json(self):
                return self._body

        started, release = threading.Event(), threading.Event()
        def delayed_gemini(*_args):
            started.set()
            release.wait(2)
            return "late answer must not be stored or spoken"

        async def exercise():
            with patch.object(cloud, "load_contextual_thread_turns", new=AsyncMock(return_value=[])), \
                 patch.object(cloud, "_memory_context", new=AsyncMock(return_value="")), \
                 patch.object(cloud, "_gemini_reply", new=delayed_gemini), \
                 patch.object(cloud, "research_for_chat", new=AsyncMock(return_value=None)):
                body = {"message": "hello", "request_id": request_id, "request_key": request_key}
                active = asyncio.create_task(cloud.chat(Request(body)))
                self.assertTrue(await asyncio.to_thread(started.wait, 1))
                cancelled = await cloud.cancel_chat(Request({
                    "request_id": request_id, "request_key": request_key,
                }))
                self.assertEqual(json.loads(cancelled.text)["status"], "output_suppressed")
                self.assertFalse(json.loads(cancelled.text)["provider_stopped"])
                release.set()
                result = json.loads((await active).text)
                self.assertEqual(result["status"], "output_suppressed")
                self.assertFalse(any(role == "assistant" for role, _ in app_state["db"].messages))

        try:
            asyncio.run(exercise())
        finally:
            release.set()

    def test_cancel_after_success_reports_completed_without_relabelling_it(self):
        import app as cloud

        class Pool:
            def __init__(self):
                self.message_id = 0
                self.messages = []
            async def fetchval(self, sql, *args):
                if "INSERT INTO conversations" in sql:
                    return args[0]
                if "INSERT INTO messages" in sql:
                    self.message_id += 1
                    self.messages.append(args[2])
                    return self.message_id
                raise AssertionError(sql)
            async def execute(self, *_args):
                return "UPDATE 1"

        app_state = {"db": Pool()}
        request_id, request_key = "d36cb343-1e99-4c5d-8f6a-c7079b997c41", "a" * 64
        class Request(dict):
            def __init__(self, body):
                super().__init__(user_id="completed-owner", device_id="phone")
                self.app, self.query, self.match_info = app_state, {}, {}
                self._body = body
            async def json(self):
                return self._body

        async def exercise():
            with patch.object(cloud, "load_contextual_thread_turns", new=AsyncMock(return_value=[])), \
                 patch.object(cloud, "_memory_context", new=AsyncMock(return_value="")), \
                 patch.object(cloud, "_gemini_reply", Mock(return_value="done")), \
                 patch.object(cloud, "research_for_chat", new=AsyncMock(return_value=None)):
                response = await cloud.chat(Request({
                    "message": "hello", "request_id": request_id,
                    "request_key": request_key,
                }))
                self.assertEqual(json.loads(response.text)["reply"], "done")
                stopped = await cloud.cancel_chat(Request({
                    "request_id": request_id, "request_key": request_key,
                }))
                self.assertEqual(json.loads(stopped.text)["status"], "already_completed")
                self.assertFalse(json.loads(stopped.text)["provider_stopped"])
                self.assertEqual(app_state["db"].messages, ["hello", "done"])

        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
