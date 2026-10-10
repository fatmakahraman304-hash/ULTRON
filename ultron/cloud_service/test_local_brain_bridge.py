"""Safety contracts for default-free ULTRON local text chat from iPhone."""
import unittest
from pathlib import Path

ROOT=Path(__file__).parent
CLOUD=(ROOT/"local_brain_bridge.py").read_text(encoding="utf-8")
APP=(ROOT/"app.py").read_text(encoding="utf-8")
MARK=(ROOT.parent.parent/"mark_app.py").read_text(encoding="utf-8")
DESKTOP=(ROOT.parent.parent/"integration"/"local_cloud_brain.py").read_text(encoding="utf-8")
PWA=(ROOT/"static"/"index.html").read_text(encoding="utf-8")
SCHEMA=(ROOT/"schema.sql").read_text(encoding="utf-8")


class LocalFirstBridgeTests(unittest.TestCase):
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
    def test_owner_does_not_receive_dangerous_remote_tools(self):
        self.assertIn('"mode":"local_brain"',CLOUD)
        self.assertIn('if payload.get("mode") == "local_brain":',MARK)
        self.assertIn('from integration.local_cloud_brain import local_chat',MARK)
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
        self.assertIn("await api('/api/device-presence')",PWA)
        self.assertIn("window.ULTRONAutoBrain.select(response.devices)",PWA)
        self.assertIn("const preferred=await refreshAutoBrain(true)",PWA)
        self.assertIn("await localBrainAnswer(text)",PWA)
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
        self.assertIn("if not reply:",CLOUD)
        self.assertIn("status=202",CLOUD)


if __name__=="__main__":
    unittest.main()
