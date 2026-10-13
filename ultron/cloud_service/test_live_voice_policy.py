"""Safety and capability contracts for the phone's live voice assistant."""
import ast
import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from live_voice_policy import (
    build_live_voice_instruction,
    explicit_memory_save_requested,
    safe_manual_memory_value,
)

class LiveVoiceMemoryConsentTests(unittest.TestCase):
    def test_clear_turkish_and_english_save_requests_are_accepted(self):
        requests = (
            "Bunu hatırla: kısa yanıtları seviyorum.",
            "Hafızana kaydet: kahvemi sütsüz içerim.",
            "Şunu aklında tut.",
            "Bunu hafızaya ekle.",
            "Bu bilgiyi not et.",
            "Unutma, projem ULTRON.",
            "Aklında bulunsun, kahvemi sütsüz içerim.",
            "Bunu aklında bulundur: kısa cevapları seviyorum.",
            "Bunu hafızana yaz: projem ULTRON.",
            "Bunu notlarına ekle: Türkçe konuşmayı tercih ederim.",
            "Remember this: I prefer concise replies.",
            "Please remember that I prefer Turkish.",
            "Save this to memory.",
            "Keep this in mind: I use Windows.",
            "Could you keep in mind that I use Windows?",
            "Don't forget that I like short answers.",
            "Do not forget this: I use Windows.",
        )
        for text in requests:
            with self.subTest(text=text):
                self.assertTrue(explicit_memory_save_requested(text))

    def test_disclosure_reminder_question_or_refusal_is_not_consent(self):
        non_requests = (
            "Genelde kısa yanıtları tercih ederim.",
            "Ben Ankara'da yaşıyorum.",
            "Yarın saat dokuzda doktora gitmemi hatırlat.",
            "Bunu hatırlama.",
            "Bunu kaydetme.",
            "Bunu hafızana alma.",
            "Bunu aklında bulundurma.",
            "Bunu hafızana yazma.",
            "Bunu aklında tutmalı mıyım?",
            "Don't save this.",
            "Do not remember this.",
            "I remember this.",
            "Bunu kaydetmeli miyim?",
        )
        for text in non_requests:
            with self.subTest(text=text):
                self.assertFalse(explicit_memory_save_requested(text))

    def test_memory_tool_refuses_credentials_even_after_save_request(self):
        for text in (
            "Bunu hatırla: API key sk-proj-" + "x" * 28,
            "Remember this password: correct horse battery staple",
            "Kaydet: Gizli anahtarım budur.",
            "Remember this secret.",
        ):
            with self.subTest(text=text):
                self.assertFalse(safe_manual_memory_value(text))
        self.assertTrue(safe_manual_memory_value("Kısa yanıtları tercih ediyorum."))


class LiveVoiceInstructionTests(unittest.TestCase):
    def test_voice_policy_requires_explicit_memory_consent_and_grounded_tools(self):
        prompt = build_live_voice_instruction("You are GÖLGE.")
        self.assertIn("Only save persistent memory when the owner explicitly asks", prompt)
        self.assertIn("A personal disclosure alone is not consent", prompt)
        self.assertIn("Automatic-learning settings do not authorize this tool", prompt)
        self.assertIn("until its tool confirms it", prompt)
        self.assertIn("send_laptop_task immediately", prompt)
        self.assertIn("user must approve before files change", prompt)
        self.assertNotIn("reveals a stable personal fact worth remembering", prompt)
        self.assertNotIn("any other action/plugin available", prompt)
        self.assertNotIn("smart-home/IoT", prompt)
        self.assertLess(len(prompt), 2600)

    def test_server_enforces_consent_before_memory_write_and_sees_transcript_first(self):
        source = (HERE / "app.py").read_text(encoding="utf-8")
        self.assertIn(
            'if not explicit_memory_save_requested(" ".join(in_parts)):', source
        )
        guard = source.index(
            'if not explicit_memory_save_requested(" ".join(in_parts)):'
        )
        write = source.index('INSERT INTO memories(user_id, category, key, value', guard)
        self.assertLess(guard, write)

        tree = ast.parse(source)
        live_voice = next(node for node in tree.body
                          if isinstance(node, ast.AsyncFunctionDef)
                          and node.name == "live_voice")
        relay = next(node for node in ast.walk(live_voice)
                     if isinstance(node, ast.AsyncFunctionDef)
                     and node.name == "gemini_to_browser")
        lines = source.splitlines()
        start = relay.lineno - 1
        end = relay.end_lineno
        relay_source = "\n".join(lines[start:end])
        self.assertLess(relay_source.index("sc.input_transcription"),
                        relay_source.index('if getattr(response, "tool_call", None):'))


class LiveVoiceToolEnforcementTests(unittest.TestCase):
    def _run_save_tool(self, utterance, value, category="PREFERENCE"):
        source = (HERE / "app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        live_voice = next(node for node in tree.body
                          if isinstance(node, ast.AsyncFunctionDef)
                          and node.name == "live_voice")
        handler = next(node for node in ast.walk(live_voice)
                       if isinstance(node, ast.AsyncFunctionDef)
                       and node.name == "execute_live_tool")

        class FunctionResponse:
            def __init__(self, *, id, name, response):
                self.id, self.name, self.response = id, name, response

        FakeTypes = type("FakeTypes", (), {"FunctionResponse": FunctionResponse})

        class FakePool:
            def __init__(self):
                self.writes = []

            async def fetchrow(self, query, *args):
                self.writes.append((query, args))
                return {"version": 1}

        FakeCall = type("FakeCall", (), {})
        call = FakeCall()
        call.id = "call-1"
        call.name = "save_memory"
        call.args = {"key": "reply_style", "value": value, "category": category}

        pool = FakePool()
        messages = []

        from live_voice_policy import (
            explicit_memory_save_requested as explicit_request,
            safe_manual_memory_value as safe_value,
        )

        async def send_json(payload):
            messages.append(payload)

        namespace = {
            "types": FakeTypes,
            "pool": pool,
            "user_id": "owner-a",
            "device_id": "phone-a",
            "in_parts": [utterance] if utterance else [],
            "send_json": send_json,
            "explicit_memory_save_requested": explicit_request,
            "safe_manual_memory_value": safe_value,
        }
        module = ast.Module(body=[handler], type_ignores=[])
        exec(compile(module, str(HERE / "app.py"), "exec"), namespace)
        result = asyncio.run(namespace["execute_live_tool"](call))
        return result, pool.writes, messages

    def test_model_cannot_save_a_disclosure_without_current_turn_consent(self):
        result, writes, messages = self._run_save_tool(
            "Genelde kısa yanıtları tercih ederim.", "Kısa yanıtlar"
        )
        self.assertFalse(result.response["ok"])
        self.assertEqual(result.response["error"], "owner_explicit_request_required")
        self.assertEqual(writes, [])
        self.assertEqual(messages, [])

    def test_explicit_request_saves_and_credential_content_is_rejected(self):
        result, writes, messages = self._run_save_tool(
            "Bunu hatırla: kısa yanıtları seviyorum.", "Kısa yanıtlar"
        )
        self.assertTrue(result.response["ok"])
        self.assertEqual(len(writes), 1)
        self.assertEqual(messages[0]["type"], "memory_saved")

        normalized, normalized_writes, _ = self._run_save_tool(
            "Bunu hatırla: kısa yanıtları seviyorum.",
            "Kısa yanıtlar", category="NOTE",
        )
        self.assertTrue(normalized.response["ok"])
        self.assertEqual(normalized_writes[0][1][1], "FACT")

        denied, denied_writes, denied_messages = self._run_save_tool(
            "Bunu hatırla: API anahtarım", "API key: sk-proj-" + "x" * 28
        )
        self.assertEqual(denied.response["error"], "credential_not_stored")
        self.assertEqual(denied_writes, [])
        self.assertEqual(denied_messages, [])

    def test_typed_live_turn_is_forwarded_remembered_and_saved_with_consent(self):
        source = (HERE / "app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        live_voice = next(node for node in tree.body
                          if isinstance(node, ast.AsyncFunctionDef)
                          and node.name == "live_voice")
        nested = {
            node.name: node for node in ast.walk(live_voice)
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name in {"execute_live_tool", "browser_to_gemini", "gemini_to_browser"}
        }

        utterance = "Bunu hafızana yaz: kahvemi sütsüz içerim."
        call = SimpleNamespace(
            id="typed-call", name="save_memory",
            args={"key": "coffee", "value": "Kahvemi sütsüz içerim.",
                  "category": "PREFERENCE"},
        )
        server_content = SimpleNamespace(
            interrupted=False,
            input_transcription=None,
            output_transcription=SimpleNamespace(text="Kaydettim."),
            turn_complete=True,
        )
        response = SimpleNamespace(
            data=None, server_content=server_content,
            tool_call=SimpleNamespace(function_calls=[call]),
        )

        class FakeWSMsgType:
            BINARY, TEXT, CLOSE, CLOSED, ERROR = 1, 2, 8, 9, 10

        class FakeSocket:
            def __init__(self):
                self._closed = False
                self.closed_event = asyncio.Event()

            @property
            def closed(self):
                return self._closed

            @closed.setter
            def closed(self, value):
                self._closed = value
                if value:
                    self.closed_event.set()

            def __aiter__(self):
                async def messages():
                    yield SimpleNamespace(
                        type=FakeWSMsgType.TEXT,
                        data=json.dumps({"type": "text", "text": utterance}),
                    )
                    await self.closed_event.wait()
                return messages()

        class FakeSession:
            def __init__(self, ws):
                self.ws = ws
                self.sent_turns = []
                self.tool_responses = []

            async def send_client_content(self, **kwargs):
                self.sent_turns.append(kwargs)

            async def send_tool_response(self, **kwargs):
                self.tool_responses.append(kwargs)

            async def receive(self):
                yield response
                self.ws.closed = True

        class FakePool:
            def __init__(self):
                self.memory_writes = []
                self.history_writes = []

            async def fetchrow(self, query, *args):
                self.memory_writes.append((query, args))
                return {"version": 1}

            async def execute(self, query, *args):
                self.history_writes.append((query, args))

        class FakeTypes:
            class FunctionResponse:
                def __init__(self, *, id, name, response):
                    self.id, self.name, self.response = id, name, response

        ws = FakeSocket()
        session = FakeSession(ws)
        pool = FakePool()
        in_parts = []
        outgoing = []

        async def send_json(payload):
            if not ws.closed:
                async with namespace["send_lock"]:
                    outgoing.append(payload)

        namespace = {
            "asyncio": asyncio,
            "json": json,
            "ws": ws,
            "session": session,
            "pool": pool,
            "types": FakeTypes,
            "web": SimpleNamespace(WSMsgType=FakeWSMsgType),
            "send_lock": None,
            "send_json": send_json,
            "in_parts": in_parts,
            "out_parts": [],
            "user_id": "owner-a",
            "device_id": "phone-a",
            "conv_uuid": "thread-a",
            "explicit_memory_save_requested": explicit_memory_save_requested,
            "safe_manual_memory_value": safe_manual_memory_value,
        }
        module = ast.Module(body=list(nested.values()), type_ignores=[])
        exec(compile(module, str(HERE / "app.py"), "exec"), namespace)

        async def exercise():
            namespace["send_lock"] = asyncio.Lock()
            inbound = asyncio.create_task(namespace["browser_to_gemini"]())
            outbound = asyncio.create_task(namespace["gemini_to_browser"]())
            done, pending = await asyncio.wait(
                {inbound, outbound}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                if task.exception():
                    raise task.exception()

        asyncio.run(exercise())
        self.assertEqual(session.sent_turns[0]["turns"]["parts"][0]["text"], utterance)
        self.assertEqual(len(pool.memory_writes), 1)
        self.assertTrue(any(args[2] == utterance for _, args in pool.history_writes))
        self.assertTrue(any(item.get("type") == "memory_saved" for item in outgoing))


if __name__ == "__main__":
    unittest.main()
