"""Request-scoped interruption contracts; these tests do not call real providers."""

import asyncio
import json
import unittest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer


class RequestCancellationRegistryTests(unittest.TestCase):
    def test_cancel_is_bound_to_owner_request_and_secret(self):
        from app.core.request_cancellation import RequestCancellationRegistry

        registry = RequestCancellationRegistry()
        event = asyncio.Event()
        registry.register("owner-a", "11111111-1111-4111-8111-111111111111",
                          "a" * 64, provider="ollama", provider_cancellable=True,
                          cancel_callback=event.set, started=True)

        self.assertEqual(registry.cancel("owner-b", "11111111-1111-4111-8111-111111111111",
                                         "a" * 64)["status"], "not_found")
        self.assertEqual(registry.cancel("owner-a", "11111111-1111-4111-8111-111111111111",
                                         "b" * 64)["status"], "not_found")
        result = registry.cancel("owner-a", "11111111-1111-4111-8111-111111111111",
                                 "a" * 64)
        self.assertEqual(result["status"], "cancellation_requested")
        self.assertTrue(event.is_set())
        self.assertEqual(registry.cancel("owner-a", "11111111-1111-4111-8111-111111111111",
                                         "a" * 64)["status"], "cancellation_requested")

    def test_unsupported_provider_reports_suppression_not_stopped(self):
        from app.core.request_cancellation import RequestCancellationRegistry

        registry = RequestCancellationRegistry()
        registry.register("owner-a", "22222222-2222-4222-8222-222222222222",
                          "c" * 64, provider="gemini", provider_cancellable=False,
                          started=True)
        result = registry.cancel("owner-a", "22222222-2222-4222-8222-222222222222",
                                 "c" * 64)
        self.assertEqual(result["status"], "output_suppressed")
        self.assertFalse(result["provider_stopped"])

    def test_transport_completion_is_only_reported_when_close_was_confirmed(self):
        from app.core.request_cancellation import RequestCancellationRegistry
        registry = RequestCancellationRegistry()
        request_id, request_key = "21212121-2121-4212-8212-212121212121", "1" * 64
        record = registry.register("owner", request_id, request_key,
                                   provider="ollama-stream", provider_cancellable=True,
                                   started=True)
        registry.cancel("owner", request_id, request_key)
        registry.finish(record, "provider_cancelled", provider_stopped=False)
        self.assertEqual(registry.describe("owner", request_id, request_key)["status"],
                         "output_suppressed")
        self.assertFalse(registry.describe("owner", request_id, request_key)["provider_stopped"])

    def test_stale_cancel_cannot_touch_a_new_request(self):
        from app.core.request_cancellation import RequestCancellationRegistry

        registry = RequestCancellationRegistry()
        old, new = asyncio.Event(), asyncio.Event()
        registry.register("same-device", "33333333-3333-4333-8333-333333333333",
                          "d" * 64, provider="ollama", provider_cancellable=True,
                          cancel_callback=old.set, started=True)
        registry.register("same-device", "44444444-4444-4444-8444-444444444444",
                          "e" * 64, provider="ollama", provider_cancellable=True,
                          cancel_callback=new.set, started=True)
        registry.cancel("same-device", "33333333-3333-4333-8333-333333333333", "d" * 64)
        self.assertTrue(old.is_set())
        self.assertFalse(new.is_set())

    def test_immediate_cancel_is_remembered_until_invoke_registers(self):
        from app.core.request_cancellation import RequestCancellationRegistry

        registry = RequestCancellationRegistry()
        request_id = "55555555-5555-4555-8555-555555555555"
        request_key = "5" * 64
        self.assertEqual(registry.cancel("owner", request_id, request_key)["status"],
                         "cancellation_requested")
        record = registry.register("owner", request_id, request_key,
                                   provider="ollama-stream", provider_cancellable=True)
        self.assertTrue(record.cancel_event.is_set())


class OllamaStreamingCancellationTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_before_provider_start_does_not_claim_it_was_stopped(self):
        from app.core.brain import Brain
        from app.core.request_cancellation import ProviderRequestCancelled
        calls = []
        async def ollama(_request):
            calls.append(True)
            raise AssertionError("provider should not be contacted")
        app = web.Application()
        app.router.add_post("/api/chat", ollama)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            brain = Brain({"llm":{"base_url":str(client.make_url("/")).rstrip("/")}})
            cancel = asyncio.Event(); cancel.set()
            with self.assertRaises(ProviderRequestCancelled) as raised:
                await brain.ask_cancellable("hello", model="qwen-test", cancel_event=cancel)
            self.assertFalse(raised.exception.provider_stopped)
            self.assertEqual(calls, [])
        finally:
            await client.close()

    async def test_cancel_closes_fake_ollama_stream_and_discards_partial_answer(self):
        from app.core.brain import Brain
        from app.core.request_cancellation import ProviderRequestCancelled

        disconnected = asyncio.Event()

        async def ollama(request):
            response = web.StreamResponse(headers={"Content-Type": "application/x-ndjson"})
            await response.prepare(request)
            await response.write((json.dumps({"message": {"content": "partial"}}) + "\n").encode())
            try:
                while True:
                    await asyncio.sleep(0.02)
                    await response.write(b'{"message":{"content":"next"}}\n')
            except (ConnectionResetError, RuntimeError, asyncio.CancelledError):
                disconnected.set()
                return response
            return response

        app = web.Application()
        app.router.add_post("/api/chat", ollama)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            brain = Brain({"llm": {"base_url": str(client.make_url("/" )).rstrip("/"),
                                   "timeout_seconds": 15}})
            cancel_event = asyncio.Event()
            task = asyncio.create_task(brain.ask_cancellable(
                "hello", model="qwen-test", cancel_event=cancel_event))
            await asyncio.sleep(0.05)
            cancel_event.set()
            with self.assertRaises(ProviderRequestCancelled):
                await asyncio.wait_for(task, 1)
            await asyncio.wait_for(disconnected.wait(), 1)
            self.assertTrue(disconnected.is_set())
        finally:
            await client.close()


class MergedInvokeCancellationTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _identity(number):
        return {
            "request_id": f"{number:08x}-1111-4111-8111-111111111111",
            "request_key": f"{number:064x}",
        }

    async def test_cloud_late_result_is_suppressed_and_new_request_can_finish(self):
        import threading
        from types import SimpleNamespace
        import merged_api

        started = asyncio.Event()
        release_old = threading.Event()

        class FakeCloud:
            enabled = True
            def __init__(self):
                self.cancelled = []
            async def chat(self, text, **_identity):
                if text == "old request":
                    started.set()
                    await asyncio.to_thread(release_old.wait, 2)
                    return {"reply": "late old response"}
                return {"reply": "new response"}
            async def cancel_chat(self, request_id, request_key):
                self.cancelled.append((request_id, request_key))
                return {"status": "output_suppressed", "provider_stopped": False}

        cloud = FakeCloud()
        # Avoid environment secrets: each request still carries a random key.
        from unittest.mock import patch
        patcher = patch.object(merged_api, "CloudClient", return_value=cloud)
        patcher.start()
        self.addCleanup(patcher.stop)
        hub = SimpleNamespace(
            bridge=SimpleNamespace(runtime=SimpleNamespace(settings={}), available=True),
            agent=SimpleNamespace(state="IDLE"),
            memory=SimpleNamespace(add_session=lambda *_args: None),
        )
        activities = []
        async def broadcast(_event): pass
        async def on_activity(*args): activities.append(args)
        hub.broadcast = broadcast
        hub.on_activity = on_activity
        app = web.Application()
        merged_api.install(app, hub)
        client = TestClient(TestServer(app))
        await client.start_server()
        old = self._identity(1)
        new = self._identity(2)
        try:
            old_reply = asyncio.create_task(client.post("/api/merged/invoke", json={
                "text": "old request", "mode": "general", **old,
            }))
            await asyncio.wait_for(started.wait(), 1)
            stopped = await client.post("/api/merged/cancel", json=old)
            stop_payload = await stopped.json()
            self.assertEqual(stop_payload["status"], "output_suppressed")
            self.assertFalse(stop_payload["provider_stopped"])

            current_reply = await client.post("/api/merged/invoke", json={
                "text": "new request", "mode": "general", **new,
            })
            current_payload = await current_reply.json()
            self.assertEqual(current_payload["text"], "new response")
            self.assertEqual(current_payload["request_id"], new["request_id"])

            old_response = await asyncio.wait_for(old_reply, 1)
            self.assertEqual(len(activities), 1)
            self.assertNotIn("fallback", str(activities).lower())
            old_payload = await old_response.json()
            self.assertEqual(old_payload["status"], "output_suppressed")
            self.assertNotIn("late old response", str(old_payload))
            self.assertEqual(cloud.cancelled, [(old["request_id"], old["request_key"])])
        finally:
            release_old.set()
            await client.close()

    async def test_agent_task_continues_when_chat_output_is_interrupted(self):
        from types import SimpleNamespace
        import merged_api
        from unittest.mock import patch

        entered, release = asyncio.Event(), asyncio.Event()

        class FakeCloud:
            enabled = False

        class Agent:
            state = "RUNNING"
            message = "task running"
            completed = False
            async def run(self, _text, approved=False):
                assert approved is False
                entered.set()
                await release.wait()
                self.completed = True
                self.state = "DONE"
                self.message = "verified task result"
                return {"ok": True}

        agent = Agent()
        with patch.object(merged_api, "CloudClient", return_value=FakeCloud()):
            hub = SimpleNamespace(
                bridge=SimpleNamespace(runtime=SimpleNamespace(settings={}), available=True),
                agent=agent, pending_task=None,
            )
            async def broadcast(_event): pass
            async def on_activity(*_args): pass
            hub.broadcast = broadcast
            hub.on_activity = on_activity
            app = web.Application()
            merged_api.install(app, hub)
            client = TestClient(TestServer(app))
            await client.start_server()
            identity = self._identity(3)
            try:
                invoke = asyncio.create_task(client.post("/api/merged/invoke", json={
                    "text": "Run the tests", "mode": "agent", **identity,
                }))
                await asyncio.wait_for(entered.wait(), 1)
                cancelled = await client.post("/api/merged/cancel", json=identity)
                payload = await cancelled.json()
                self.assertEqual(payload["status"], "output_suppressed")
                self.assertTrue(payload["operation_continues"])
                self.assertFalse(agent.completed)
                release.set()
                result = await asyncio.wait_for(invoke, 1)
                result_payload = await result.json()
                self.assertTrue(agent.completed)
                self.assertEqual(result_payload["status"], "output_suppressed")
                self.assertFalse(result_payload["completed"] if "completed" in result_payload else False)
            finally:
                release.set()
                await client.close()


class VoiceRuntimeInterruptionTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _identity(number):
        return {
            "request_id": f"{number:08x}-1111-4111-8111-111111111111",
            "request_key": f"{number:064x}",
        }

    async def test_interrupt_stops_active_tts_and_discards_queued_partial_chunks(self):
        from app.multimodal.voice_runtime import VoiceRuntime
        import array

        tts_started = asyncio.Event()
        stopped = []
        played = []

        async def mic():
            for _ in range(4):
                yield array.array("h", [7000] * 480).tobytes()
        async def stt(_pcm):
            yield {"kind": "final", "text": "hello", "confidence": .9, "language": "en"}
        async def brain(_text):
            yield "partial answer"
            await asyncio.Event().wait()
        async def speak(chunks):
            tts_started.set()
            await asyncio.Event().wait()
            played.extend(chunks)

        runtime = VoiceRuntime(mic_frames=mic, stt_stream=stt, brain_stream=brain,
                               tts_speak_chunks=speak,
                               tts_interrupt=lambda: stopped.append(True))
        turn = asyncio.create_task(runtime.run_turn())
        await asyncio.wait_for(tts_started.wait(), 1)
        event = runtime.interrupt()
        result = await asyncio.wait_for(turn, 1)
        self.assertIn(event["type"], {"voice.cancelled", "voice.interrupted"})
        self.assertEqual(result["status"], "interrupted")
        self.assertIsNone(result["text"])
        self.assertEqual(result["chunks"], [])
        self.assertEqual(result["spoken_chunks"], 0)
        self.assertEqual(stopped, [True])
        self.assertEqual(played, [])

    async def test_local_qwen_stream_cancel_is_confirmed_and_new_request_is_independent(self):
        from types import SimpleNamespace
        import merged_api
        from app.core.request_cancellation import ProviderRequestCancelled
        from unittest.mock import patch

        old_started = asyncio.Event()

        class FakeBrain:
            model = "qwen3:4b"
            async def ask_cancellable(self, prompt, system="", model=None, *, cancel_event):
                if prompt == "old local request":
                    old_started.set()
                    await cancel_event.wait()
                    raise ProviderRequestCancelled("fake stream closed", provider_stopped=True)
                return "new local answer"

        class FakeCloud:
            enabled = False

        with patch.object(merged_api, "CloudClient", return_value=FakeCloud()):
            hub = SimpleNamespace(
                bridge=SimpleNamespace(runtime=SimpleNamespace(
                    settings={"llm": {}}, brain=FakeBrain()), available=True),
                agent=SimpleNamespace(state="IDLE"), ai_status={},
            )
            async def check_ollama(): return {"status": {"models": ["qwen3:4b"]}}
            async def broadcast(_event): pass
            hub.check_ollama = check_ollama
            hub.broadcast = broadcast
            app = web.Application()
            merged_api.install(app, hub)
            client = TestClient(TestServer(app))
            await client.start_server()
            old = self._identity(4)
            new = self._identity(5)
            try:
                old_reply = asyncio.create_task(client.post("/api/merged/invoke", json={
                    "text": "old local request", "mode": "coding", **old,
                }))
                await asyncio.wait_for(old_started.wait(), 1)
                stopped = await client.post("/api/merged/cancel", json=old)
                stop_payload = await stopped.json()
                self.assertEqual(stop_payload["status"], "cancelled")
                self.assertTrue(stop_payload["provider_stopped"])

                current = await client.post("/api/merged/invoke", json={
                    "text": "new local request", "mode": "coding", **new,
                })
                current_payload = await current.json()
                self.assertEqual(current_payload["text"], "new local answer")
                old_payload = await (await old_reply).json()
                self.assertEqual(old_payload["status"], "cancelled")
                self.assertNotIn("partial", str(old_payload))
            finally:
                await client.close()


if __name__ == "__main__":
    unittest.main()
