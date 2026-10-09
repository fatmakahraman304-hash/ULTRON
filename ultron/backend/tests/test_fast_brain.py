"""ULTRON local Fast Brain latency/quality routing contracts.

Uses only installed-model fakes; no Ollama, GPU, paid API or network required.
The native audio/MARK Gemini Live pipeline remains unchanged.
"""
import unittest
from unittest.mock import patch

from app.core.fast_brain import FastBrainPolicy, classify_text, last_user_intent, simple_chitchat
from app.core.model_router import ModelRouter, TaskType
from app.core.brain import Brain


MODELS=["qwen2.5-coder:7b","qwen3:4b","qwen3:8b","llava:7b"]
CONFIG={"llm":{
    "model":"qwen2.5-coder:7b",
    "provider":"ollama",
    "base_url":"http://127.0.0.1:11434",
    "local_multi_model":{"enabled":True,"models":["qwen3:4b","qwen3:8b"]},
    "fast_brain":{
        "enabled":True,"single_pass_all_interactive":True,
        "conversation_models":["qwen3.5:4b","qwen3:4b"],
        "reasoning_models":["qwen3:8b","qwen3:4b"],
        "coding_models":["qwen2.5-coder:7b"],
        "vision_models":["llava:7b"],
        "speech_tokens":192,"tool_tokens":512,"keep_alive":"10m",
    },
}}


class FakeBrain:
    model="qwen2.5-coder:7b"
    def __init__(self, fail=()):
        self.calls=[]
        self.fail=set(fail)
    def chat(self,messages,tools=None,model=None):
        self.calls.append(("chat",model,bool(tools)))
        if model in self.fail:
            raise RuntimeError("Ollama failed")
        return {"message":{"role":"assistant","content":"Merhaba efendim."}}
    def ask(self,prompt,system="",model=None):
        self.calls.append(("ask",model,False))
        if model in self.fail:
            raise RuntimeError("Ollama failed")
        return "Türkçe yanıt"


class TestClassification(unittest.TestCase):
    def test_fast_normal_conversation(self):
        for utterance in ("Merhaba ULTRON", "Nasılsın?", "Bana bir şaka anlat",
                          "Kıbrıs'ta bugün hava nasıl?", "Hızlı cevap ver"):
            self.assertEqual(classify_text(utterance),"FAST",utterance)
    def test_code_deep_vision(self):
        self.assertEqual(classify_text("Python kodu yaz"),"CODING")
        self.assertEqual(classify_text("React API hatası düzelt"),"CODING")
        self.assertEqual(classify_text("Detaylı araştır ve kapsamlı analiz yap"),"GENERAL")
        self.assertEqual(classify_text("Bu ekran görüntüsünü analiz et"),"VISION")
    def test_only_pure_greetings_can_skip_tool_schemas(self):
        for phrase in ('Merhaba', 'Nasılsın?', 'Bana bir şaka anlat', 'Selam!'):
            self.assertTrue(simple_chitchat(phrase),phrase)
        for task in ('Merhaba dosyayı aç', 'Bilgisayarımın durumunu kontrol et', 'Sesi yükselt', 'Nasılsın, tarayıcıyı aç'):
            self.assertFalse(simple_chitchat(task),task)

    def test_history_uses_real_latest_user_not_tool_output(self):
        history=[{"role":"system","content":"SYS"},{"role":"user","content":"Python kodu yaz"},
                 {"role":"assistant","content":"working"},{"role":"tool","content":"ok"}]
        self.assertEqual(last_user_intent(history),"CODING")


class TestInstalledModelPolicy(unittest.TestCase):
    def setUp(self):
        self.policy=FastBrainPolicy(CONFIG["llm"]["fast_brain"])
    def test_model_is_never_invented_or_downloaded(self):
        choice=self.policy.choose(task="FAST",installed=MODELS,primary="qwen2.5-coder:7b")
        self.assertEqual(choice.model,"qwen3:4b")
        self.assertTrue(choice.inventory_checked)
        self.assertEqual(choice.reason,"installed_preference")
        self.assertEqual(self.policy.choose(task="FAST",installed=[],primary="qwen2.5-coder:7b").model,"qwen2.5-coder:7b")
    def test_qwen35_is_opt_in_once_installed(self):
        v=self.policy.choose(task="FAST",installed=MODELS+["qwen3.5:4b"],primary="qwen2.5-coder:7b")
        self.assertEqual(v.model,"qwen3.5:4b")
    def test_specialist_models(self):
        self.assertEqual(self.policy.choose(task="CODING",installed=MODELS,primary="qwen3:4b").model,"qwen2.5-coder:7b")
        self.assertEqual(self.policy.choose(task="VISION",installed=MODELS,primary="qwen3:4b").model,"llava:7b")
        self.assertEqual(self.policy.choose(task="GENERAL",installed=MODELS,primary="qwen3:4b").model,"qwen3:8b")
    def test_disabled_and_invalid_config_are_safe(self):
        self.assertEqual(FastBrainPolicy({}).choose(task="FAST",installed=MODELS,primary="baseline").model,"baseline")
        p=FastBrainPolicy({"enabled":True,"conversation_models":"bad","speech_tokens":"NaN"})
        self.assertIn(p.choose(task="FAST",installed=MODELS,primary="qwen3:4b").model,MODELS)
        self.assertEqual(p.runtime_options("qwen3:4b")["options"]["num_predict"],192)
    def test_prompt_options_are_bounded_and_think_only_where_supported(self):
        p=self.policy.runtime_options("qwen3:4b")
        self.assertIs(p["think"],False)
        self.assertEqual(p["keep_alive"],"10m")
        self.assertEqual(p["options"]["num_ctx"],4096)
        self.assertLessEqual(p["options"]["num_predict"],256)
        with_tools=self.policy.runtime_options("qwen2.5-coder:7b",tools=True)
        self.assertNotIn("think",with_tools)
        self.assertEqual(with_tools["options"]["num_ctx"],8192)
        self.assertEqual(with_tools["options"]["num_predict"],512)


class TestRouterLatency(unittest.TestCase):
    def router(self, brain=None):
        brain=brain or FakeBrain()
        return ModelRouter(brain,CONFIG,get_models=lambda:list(MODELS),sleep=lambda seconds:None)
    def test_chat_one_call_no_racing_or_judge(self):
        brain=FakeBrain()
        r=self.router(brain)
        with patch.object(r,"race_local_and_judge",side_effect=AssertionError("extra model race")):
            answer=r.chat(TaskType.GENERAL,[{"role":"user","content":"Merhaba"}],tools=[{"type":"function"}])
        self.assertEqual(answer["message"]["content"],"Merhaba efendim.")
        self.assertEqual(brain.calls,[("chat","qwen3:4b",True)])
    def test_ask_one_call_with_optional_judge_only_for_manual(self):
        brain=FakeBrain()
        r=self.router(brain)
        with patch.object(r,"race_local_and_judge",side_effect=AssertionError("unexpected race")):
            answer=r.ask(TaskType.GENERAL,"Merhaba ULTRON")
        self.assertEqual(answer,"Türkçe yanıt")
        self.assertEqual(brain.calls,[("ask","qwen3:4b",False)])
        self.assertTrue(r.local_multi_enabled())
    def test_code_chooses_coder_without_parallel_loading(self):
        brain=FakeBrain()
        r=self.router(brain)
        r.chat(TaskType.GENERAL,[{"role":"user","content":"Python kodu yaz"}])
        self.assertEqual(brain.calls,[("chat","qwen2.5-coder:7b",False)])
    def test_coding_fallback_only_when_primary_fails(self):
        brain=FakeBrain(fail={"qwen2.5-coder:7b"})
        r=self.router(brain)
        response=r.chat(TaskType.GENERAL,[{"role":"user","content":"Python kodu yaz"}])
        self.assertEqual(response["message"]["content"],"Merhaba efendim.")
        self.assertEqual(len(brain.calls),2)
        self.assertEqual(brain.calls[0][1],"qwen2.5-coder:7b")
        self.assertEqual(brain.calls[1][1],"qwen3:8b")
    def test_no_automatic_judge_on_plain_answers(self):
        r=self.router()
        with patch.object(r,"race_local_and_judge",side_effect=AssertionError("race called")):
            r.chat(TaskType.GENERAL,[{"role":"user","content":"Selam"}],tools=None)
        self.assertEqual(len(r.brain.calls),1)


class TestOllamaWire(unittest.TestCase):
    def test_brain_uses_fast_options_without_changing_tool_contract(self):
        brain=Brain(CONFIG)
        captured=[]
        def reply(endpoint,payload):
            captured.append(payload)
            return {"model":payload["model"],"message":{"content":"OK","tool_calls":[]}}
        with patch.object(brain,"_post",side_effect=reply):
            res=brain.chat([{"role":"user","content":"Selam"}],
                           tools=[{"type":"function","function":{"name":"status"}}],
                           model="qwen3:4b")
            self.assertEqual(res["message"]["content"],"OK")
            brain.ask("Selam","Türkçe cevap ver",model="qwen2.5-coder:7b")
        self.assertEqual(len(captured),2)
        self.assertIs(captured[0]["think"],False)
        self.assertTrue(captured[0]["tools"])
        self.assertEqual(captured[0]["options"]["num_predict"],512)
        self.assertNotIn("think",captured[1])
        self.assertEqual(captured[1]["options"]["num_predict"],192)


if __name__=="__main__":
    unittest.main()
