"""Safety contracts for default-free ULTRON local text chat from iPhone."""
import unittest
import asyncio
import hashlib
import json
import uuid
import sys
from pathlib import Path

ROOT=Path(__file__).parent
CLOUD=(ROOT/"local_brain_bridge.py").read_text(encoding="utf-8")
APP=(ROOT/"app.py").read_text(encoding="utf-8")
MARK=(ROOT.parent.parent/"mark_app.py").read_text(encoding="utf-8")
DESKTOP=(ROOT.parent.parent/"integration"/"local_cloud_brain.py").read_text(encoding="utf-8")
PWA=(ROOT/"static"/"index.html").read_text(encoding="utf-8")
SCHEMA=(ROOT/"schema.sql").read_text(encoding="utf-8")
sys.path.insert(0, str(ROOT))
from local_reply_validation import _validated_local_reply
import local_brain_bridge


class _AsyncScope:
    async def __aenter__(self): return self
    async def __aexit__(self, *_args): return False


class _LocalCancelConnection:
    def __init__(self, *, command_status):
        self.command_status = command_status
        self.calls = []
    def transaction(self): return _AsyncScope()
    async def fetchrow(self, sql, *args):
        self.calls.append((sql, args))
        if "FROM local_chat_requests" in sql:
            return {"command_id": 91, "conversation_id": uuid.UUID("56e1b7da-999e-4a77-9d79-102fd6b923c0"),
                    "reply_saved": False, "cancellation_requested": False,
                    "provider_stopped": False, "request_key_hash": hashlib.sha256(
                        b"b" * 64 if self.command_status == "queued" else b"c" * 64
                    ).hexdigest(), "command_status": self.command_status}
        raise AssertionError(sql)
    async def execute(self, sql, *args):
        self.calls.append((sql, args))
        return "UPDATE 1"
    async def fetchval(self, sql, *args):
        self.calls.append((sql, args))
        return "cancelled" if self.command_status in ("queued", "delivered") else None


class _LocalCancelPool:
    def __init__(self, *, command_status):
        self.conn = _LocalCancelConnection(command_status=command_status)
    def acquire(self): return _AsyncScopeWithValue(self.conn)
    async def fetchval(self, *_args): return False


class _AsyncScopeWithValue(_AsyncScope):
    def __init__(self, value): self.value = value
    async def __aenter__(self): return self.value


class LocalFirstBridgeTests(unittest.TestCase):
    def test_local_chat_cancel_scopes_owner_and_never_claims_provider_stopped(self):
        request_id, request_key = str(uuid.uuid4()), "b" * 64
        request = {
            "auth_kind": "web", "user_id": "owner-a",
            "app": {"db": _LocalCancelPool(command_status="queued")},
            "body": {"request_id": request_id, "request_key": request_key},
        }
        class MockRequest(dict):
            app = request["app"]
            async def json(self): return self["body"]

        response = asyncio.run(local_brain_bridge.cancel_local_chat(MockRequest(request)))
        payload = json.loads(response.text)
        self.assertEqual(payload["status"], "cancelled_before_start")
        self.assertTrue(payload["prevented_start"])
        self.assertFalse(payload["provider_stopped"])
        conn = request["app"]["db"].conn
        select_sql, select_args = next(
            call for call in conn.calls if "FROM local_chat_requests" in call[0]
        )
        self.assertIn("WHERE l.user_id=$1 AND l.request_id=$2", select_sql)
        self.assertEqual(select_args[0], "owner-a")
        self.assertEqual(select_args[1], uuid.UUID(request_id))
        self.assertIn("jsonb_build_object", conn.calls[-1][0])

    def test_delivered_local_qwen_reports_cancellation_pending_not_stopped(self):
        request = {
            "auth_kind": "web", "user_id": "owner-b",
            "app": {"db": _LocalCancelPool(command_status="delivered")},
            "body": {"request_id": str(uuid.uuid4()), "request_key": "c" * 64},
        }
        class MockRequest(dict):
            app = request["app"]
            async def json(self): return self["body"]
        payload = json.loads(asyncio.run(local_brain_bridge.cancel_local_chat(MockRequest(request))).text)
        self.assertEqual(payload["status"], "cancellation_requested")
        self.assertFalse(payload["provider_stopped"])

    def test_local_chat_cancel_rejects_non_web_session(self):
        class MockRequest(dict):
            app = {}
            async def json(self): return {}
        with self.assertRaises(Exception) as raised:
            asyncio.run(local_brain_bridge.cancel_local_chat(MockRequest(auth_kind="device")))
        from aiohttp import web
        self.assertIsInstance(raised.exception, web.HTTPForbidden)

    def test_completed_reply_origin_is_factual_and_not_raw_json(self):
        ollama = _validated_local_reply({
            "assistant_reply": "  Tamam, devam ediyorum.  ",
            "model": "qwen3:4b",
            "provider": "local-ollama",
        })
        self.assertEqual(ollama,
                         ("Tamam, devam ediyorum.", "qwen3:4b",
                          "desktop-local-ollama"))
        no_image = _validated_local_reply({
            "assistant_reply": "Görsel ulaşmadı",
            "model": "",
            "provider": "local-no-image",
        })
        self.assertEqual(no_image,
                         ("Görsel ulaşmadı", "", "desktop-local-no-image"))
        # Compatibility with older paired desktop workers that omitted the
        # provider but returned a genuine model message is intentional.
        legacy = _validated_local_reply({
            "assistant_reply": "Merhaba", "model":"qwen3:4b",
        })
        self.assertEqual(legacy[2], "desktop-local-ollama")
        named_qwen = _validated_local_reply({
            "assistant_reply":"İşte yanıt.",
            "model":"team/qwen2.5-coder:7b",
            "provider":"local-ollama",
        })
        self.assertEqual(named_qwen[1], "team/qwen2.5-coder:7b")
        for payload in (
            {}, {"assistant_reply":""},
            {"assistant_reply":{"content":"not text"}},
            {"assistant_reply":["not text"]},
            {"assistant_reply":123},
            {"assistant_reply":"Hello","provider":"totally-other"},
            {"assistant_reply":"Hello","provider":"/tmp/injected-path"},
            {"assistant_reply":"No image","provider":"local-no-image",
             "model":"qwen3:4b"},
            {"assistant_reply":"Hello","model":{"key":"not-model"}},
            {"assistant_reply":"Hello","model":""},
            {"assistant_reply":"Hello","model":"llava:7b"},
            {"assistant_reply":"Hello","model":"llama3:8b",
             "provider":"local-ollama"},
            {"assistant_reply":"Hello","model":"qwenish:7b"},
            {"assistant_reply":"Hello","model":"../../qwenish:8b"},
        ):
            with self.subTest(payload=payload):
                self.assertIsNone(_validated_local_reply(payload))
        self.assertIn("VALUES($1,$2,'assistant',$3,$4)", CLOUD)
        self.assertIn("reply, source", CLOUD)
        self.assertNotIn("'desktop-local-ollama')", CLOUD)

    def test_cloud_filters_legacy_qwen_thoughts_before_memory_save(self):
        raw={'provider':'local-ollama','model':'qwen3:4b',
             'assistant_reply':'Draft internal text\n</think>\n\nZümrüt 529'}
        reply=_validated_local_reply(raw)
        self.assertEqual(reply,('Zümrüt 529','qwen3:4b','desktop-local-ollama'))
        self.assertIsNone(_validated_local_reply({
            'provider':'local-ollama','model':'qwen3:4b',
            'assistant_reply':'<think>\nNo final answer yet'}))
        self.assertEqual(_validated_local_reply({
            'provider':'local-no-image','model':'',
            'assistant_reply':'No image arrived.'})[0],'No image arrived.')

    def test_owner_queue_limit_and_thread_limit_use_one_transaction_lock(self):
        self.assertIn("pg_advisory_xact_lock",CLOUD)
        self.assertIn("local_chat_thread_busy",CLOUD)
        self.assertIn("l.conversation_id=$2",CLOUD)
        self.assertIn("AND c.user_id=$1",CLOUD)
        self.assertIn("AND c.status IN ('queued','delivered')",CLOUD)
        self.assertIn("local_brain_busy",CLOUD)
        self.assertIn("async with conn.transaction()",CLOUD)

    def test_cloud_requires_web_owner_session(self):
        self.assertIn('request.get("auth_kind") != "web"',CLOUD)
        self.assertIn('request["user_id"]',CLOUD)
        self.assertIn("AND c.user_id=$2",CLOUD)
        self.assertIn("WHERE command_id=$1 AND user_id=$2 FOR UPDATE",CLOUD)
        self.assertIn("reply_saved=TRUE",CLOUD)
    def test_free_mode_does_not_silently_call_gemini(self):
        self.assertIn('"/api/local-chat"',CLOUD)
        self.assertIn('"desktop_offline"',CLOUD)
        self.assertIn("local_chat_requests",SCHEMA)
        self.assertNotIn("genai.Client",CLOUD)
        self.assertNotIn("_gemini_reply(",CLOUD)
        self.assertIn("register_local_brain_routes(app,_memory_context,_recent_context)",APP)

    def test_local_qwen_receives_shared_system_prompt_through_bounded_composer(self):
        self.assertIn('base_prompt=os.getenv("ULTRON_SYSTEM_PROMPT")', CLOUD)
        self.assertIn("max_chars=4500", CLOUD)
        self.assertIn("read_only=True", CLOUD)
    def test_owner_does_not_receive_dangerous_remote_tools(self):
        self.assertIn('"mode":"local_brain"',CLOUD)
        self.assertIn('if payload.get("mode") == "local_brain":',MARK)
        self.assertIn('await client.local_chat(',MARK)
        self.assertIn('from integration.local_cloud_brain import local_chat',
                      (ROOT.parent/'backend'/'cloud_client.py').read_text())
        self.assertIn('if lease_guard.lost.is_set():',MARK)
        self.assertNotIn("subprocess",DESKTOP)
        self.assertNotIn("send_laptop_task",DESKTOP)
        self.assertNotIn("api.openai.com",DESKTOP)
        self.assertNotIn("googleapis.com",DESKTOP)
        self.assertIn('_OLLAMA="http://127.0.0.1:11434"',DESKTOP)
        self.assertIn('"/api/tags"',DESKTOP)
        self.assertIn('"stream":', (ROOT.parent/"backend"/"app"/"core"/"fast_brain.py").read_text(encoding="utf-8"))
    def test_mobile_auto_selects_live_local_or_cloud_without_manual_picker(self):
        self.assertIn("let brainMode='gemini';",PWA)
        self.assertIn("async function refreshAutoBrain(force=false)",PWA)
        self.assertIn("await api('/api/device-presence',{timeoutMs:6000})",PWA)
        self.assertIn("window.ULTRONAutoBrain.select(response.devices)",PWA)
        self.assertIn("const preferred=await refreshAutoBrain(true)",PWA)
        self.assertIn("await localBrainAnswer(text,userBubble,chatIdentity,requestController.signal)",PWA)
        self.assertIn("await cloud()",PWA)
        self.assertIn("window.ULTRONAutoBrain.safeToFallback(e)",PWA)
        self.assertIn("localVoiceController?.toggle()",PWA)
        self.assertNotIn('id="brainMode"',PWA)
        self.assertNotIn('ULTRON BEYİN',PWA)
        self.assertNotIn('GEMINI • İSTEĞE BAĞLI',PWA)
        self.assertNotIn("setTimeout(()=>startHandsFreeVoice(),250)",PWA)
    def test_no_auto_download_and_no_optimistic_reply(self):
        self.assertNotIn("ollama pull",DESKTOP)
        self.assertIn("if not answer:",DESKTOP)
        self.assertIn("answer[:12000]",DESKTOP)
        self.assertIn("_validated_local_reply(result)",CLOUD)
        self.assertIn("status=202",CLOUD)


if __name__=="__main__":
    unittest.main()
