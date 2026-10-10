"""No paid provider and no automatic model pull in paired-iPhone Ollama brain."""
import unittest
from unittest.mock import patch

from integration import local_cloud_brain as local


class LocalBrainTests(unittest.TestCase):
    def setUp(self):
        local._MODELS_CACHE=(0.0,[])

    def test_chats_on_installed_free_qwen_model(self):
        calls=[]
        def fake(path,payload=None,timeout=8):
            calls.append((path,payload))
            if path=="/api/tags":
                return {"models":[{"name":"qwen3:4b"},{"name":"qwen2.5-coder:7b"}]}
            return {"message":{"role":"assistant","content":"Merhaba, buradayım efendim."}}
        with patch.object(local,"_get_json",side_effect=fake):
            out=local.local_chat("Merhaba","Kısa Türkçe cevap ver")
        self.assertEqual(out["model"],"qwen3:4b")
        self.assertEqual(out["provider"],"local-ollama")
        self.assertEqual(out["reply"],"Merhaba, buradayım efendim.")
        self.assertEqual(calls[1][1]["model"],"qwen3:4b")
        self.assertNotIn("tools",calls[1][1])
        self.assertIs(calls[1][1]["think"],False)

    def test_code_prefers_original_coder_model(self):
        with patch.object(local,"_get_json",side_effect=[
            {"models":[{"name":"qwen3:4b"},{"name":"qwen2.5-coder:7b"}]},
            {"message":{"content":"def add(a,b): return a+b"}}
        ]) as fetch:
            out=local.local_chat("Python kodu yaz","Sen ULTRON'sun")
        self.assertEqual(out["model"],"qwen2.5-coder:7b")
        self.assertNotIn("think",fetch.call_args_list[-1].args[1])

    def test_optional_qwen35_selected_only_when_installed(self):
        with patch.object(local,"_get_json",side_effect=[
            {"models":[{"name":"qwen3.5:4b"},{"name":"qwen3:4b"}]},
            {"message":{"content":"Hazırım."}}
        ]):
            out=local.local_chat("Selam","")
        self.assertEqual(out["model"],"qwen3.5:4b")

    def test_missing_models_or_empty_answer_fail_closed(self):
        with patch.object(local,"_get_json",return_value={"models":[]}):
            with self.assertRaises(local.LocalBrainUnavailable):
                local.local_chat("Merhaba","")
        with patch.object(local,"_get_json",side_effect=[
            {"models":[{"name":"qwen3:4b"}]},{"message":{"content":""}}
        ]):
            with self.assertRaises(local.LocalBrainUnavailable):
                local.local_chat("Merhaba","")

    def test_readiness_probes_live_ollama_not_positive_cache(self):
        local._MODELS_CACHE=(float('inf'),['qwen3:4b'])
        with patch.object(local,"_get_json",side_effect=local.LocalBrainUnavailable("offline")):
            self.assertFalse(local.local_chat_ready())
        with patch.object(local,"_get_json",return_value={"models":[]}):
            self.assertFalse(local.local_chat_ready())
        with patch.object(local,"_get_json",return_value={"models":[{"name":"qwen3:4b"}]}) as fetch:
            self.assertTrue(local.local_chat_ready())
            self.assertEqual(fetch.call_args.args,('/api/tags',))
            self.assertLessEqual(fetch.call_args.kwargs['timeout'],2)

    def test_only_local_fixed_endpoints_allowed(self):
        with self.assertRaises(ValueError):
            local._get_json("https://api.gemini.com")
        with self.assertRaises(ValueError):
            local._get_json("/api/pull",{"model":"qwen3:4b"})


if __name__=="__main__":
    unittest.main()
