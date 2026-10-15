"""Regression tests for the zero-extra-call shared conversational router."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from conversation_persona import (
    build_system_instruction, classify_intent, dialogue_guidance,
)
from conversation_turns import (
    is_explicit_turn_correction, load_contextual_thread_turns,
)
from ultron.backend.app.core.fast_brain import FastBrainPolicy, classify_text


class ConversationIntentRouterTests(unittest.TestCase):
    def test_route_priority_and_elliptical_turns(self):
        cases = [
            ("Selam, nasılsın?", "chat"),
            ("GÖLGE, devam et", "continuation"),
            ("Peki, onun yakıt tüketimi?", "continuation"),
            ("Actually, I meant the 2009 model", "correction"),
            ("Bir şey daha: aslında 2009 modelini kastetmiştim", "correction"),
            ("Önceki projeye dön", "topic_return"),
            ("Let's go back to the previous project", "topic_return"),
            ("Az önce ne demiştim?", "history_recall"),
            ("What did I just say?", "history_recall"),
            ("Hafızanda benim tercihlerimden ne var?", "memory_recall"),
            ("What do you remember about my preferences?", "memory_recall"),
            ("Kaynakları kontrol ederek güncel araştırma yap", "research"),
            ("Research the latest changes and cite sources", "research"),
            ("Bu Python hatasını düzelt ve testleri çalıştır", "computer_task"),
            ("Run the tests and fix the failing code", "computer_task"),
            ("Sahnede mavi bir küre oluştur ve döndür", "scene_visual"),
            ("Create a 3D robot arm in the scene", "scene_visual"),
        ]
        for message, expected in cases:
            with self.subTest(message=message):
                self.assertEqual(classify_intent(message).kind, expected)

    def test_current_correction_wins_over_old_topic_recall(self):
        decision = classify_intent(
            "Aslında önceki projeye değil, 2009 Mercedes'e dön demek istedim"
        )
        self.assertEqual(decision.kind, "correction")
        self.assertTrue(decision.requires_context)
        self.assertTrue(is_explicit_turn_correction(
            "Bir şey daha: kastettiğim dizel modeldi"
        ))

    def test_tool_intents_never_claim_unverified_completion(self):
        for message, route in (
            ("Güncel kaynaklarla araştır", "RESEARCH ROUTE"),
            ("Python kodunu değiştir", "COMPUTER TASK ROUTE"),
            ("3D sahneye bir motor ekle", "SCENE ROUTE"),
        ):
            with self.subTest(message=message):
                decision = classify_intent(message)
                self.assertTrue(decision.requires_tool)
                guidance = dialogue_guidance(message, has_prior_turns=True)
                self.assertIn(route, guidance)
                self.assertIn("do not claim", guidance.lower())
                system = build_system_instruction(
                    user_message=message, read_only=True, max_chars=4500,
                    has_prior_turns=True,
                )
                self.assertIn(route, system)
                self.assertIn("READ-ONLY MODE", system)

    def test_history_and_memory_routes_are_separate_and_scoped(self):
        history = classify_intent("Önceki mesajım neydi?")
        memory = classify_intent("Benim hakkımda neleri hatırlıyorsun?")
        self.assertEqual(history.kind, "history_recall")
        self.assertEqual(memory.kind, "memory_recall")
        self.assertTrue(history.requires_context)
        self.assertTrue(memory.requires_context)
        self.assertIn("same conversation", dialogue_guidance(
            "Önceki mesajım neydi?", has_prior_turns=True).lower())

    def test_research_uses_reasoning_route_without_affecting_fast_chat(self):
        self.assertEqual(classify_text("Selam, nasılsın?"), "FAST")
        self.assertEqual(classify_text("Kaynaklarla kapsamlı araştır"), "RESEARCH")
        self.assertEqual(classify_text("Research how to implement a Python parser"), "RESEARCH")
        self.assertEqual(classify_text("Run the tests"), "CODING")
        policy = FastBrainPolicy({"enabled": True,
                                  "research_models": ["qwen3:8b"]})
        choice = policy.choose(task=classify_text("Araştır ve kaynakları karşılaştır"),
                               installed=["qwen3:4b", "qwen3:8b"],
                               primary="qwen3:4b")
        self.assertEqual((choice.task, choice.model), ("RESEARCH", "qwen3:8b"))

    def test_previous_topic_return_loads_older_same_thread_evidence(self):
        class DB:
            def __init__(self):
                self.calls = []
                self.rows = [
                    {"id": 1, "role": "user", "content": "2009 Mercedes C180 projesine dönelim"},
                    {"id": 2, "role": "assistant", "content": "C180 motor seçenekleri"},
                    {"id": 3, "role": "user", "content": "Konuyu değiştirelim, Qwen modelini inceleyelim"},
                    {"id": 4, "role": "assistant", "content": "Qwen3:8B seçenekleri"},
                    {"id": 5, "role": "user", "content": "Önceki projeye dön"},
                ]

            async def fetch(self, sql, *args):
                self.calls.append((sql, args))
                if "ORDER BY id ASC LIMIT" in sql:
                    return self.rows[:args[-1]]
                return list(reversed(self.rows[:-1]))[:args[-1]]

        import asyncio
        async def run():
            db = DB()
            turns = await load_contextual_thread_turns(
                db, "owner-a", "thread-a", question="Önceki projeye dön",
                before_id=5, max_chars=1400, limit=8,
            )
            combined = " ".join(row["content"] for row in turns)
            self.assertIn("Mercedes C180", combined)
            self.assertIn("Qwen3", combined)
            self.assertTrue(db.calls)
            self.assertTrue(all(args[:3] == ("owner-a", "thread-a", 5)
                                for _, args in db.calls))
        asyncio.run(run())

    def test_previous_topic_pages_past_recent_window_to_find_its_anchor(self):
        class DB:
            def __init__(self):
                self.calls = []
                self.rows = [
                    {"id": 1, "role": "user", "content": "2009 Mercedes C180 projesi"},
                    {"id": 2, "role": "assistant", "content": "C180 seçenekleri"},
                    {"id": 3, "role": "user", "content": "Konuyu değiştirelim, Qwen'i konuşalım"},
                ] + [
                    {"id": i, "role": "assistant" if i % 2 else "user",
                     "content": f"Güncel Qwen bağlamı {i}"}
                    for i in range(4, 100)
                ]

            async def fetch(self, sql, *args):
                self.calls.append((sql, args))
                if len(args) == 5:
                    return [row for row in reversed(self.rows)
                            if row["id"] < args[4]][:args[3]]
                return list(reversed(self.rows[-args[3]:]))

        import asyncio
        async def run():
            db = DB()
            turns = await load_contextual_thread_turns(
                db, "owner-a", "thread-a", question="Önceki projeye dön",
                before_id=200, max_chars=1800, limit=8,
            )
            combined = " ".join(row["content"] for row in turns)
            self.assertIn("Mercedes C180", combined)
            self.assertIn("Qwen bağlamı 98", combined)
            self.assertGreaterEqual(len(db.calls), 2)
            self.assertTrue(all(args[:3] == ("owner-a", "thread-a", 200)
                                for _, args in db.calls))
        asyncio.run(run())

    def test_frozen_bilingual_intent_suite_and_model_limits(self):
        from evals.conversation.intent_eval import DATA, evaluate, validate
        import json
        cases = json.loads(DATA.read_text(encoding="utf-8"))
        validate(cases)
        report = evaluate(cases)
        self.assertEqual(report["deterministic_router"]["score"], "100/100")
        self.assertEqual(report["language_counts"], {"tr": 50, "en": 50})
        self.assertEqual(report["model_quality"], "NOT_RUN")
        self.assertEqual(report["first_token_latency_ms"], "NOT_RUN")
        self.assertEqual(report["total_model_latency_ms"], "NOT_RUN")
        self.assertEqual(report["extra_model_calls_for_routing"], 0)
        changed = [dict(row) for row in cases]
        changed[0]["message"] = "Changed criterion"
        with self.assertRaises(ValueError):
            validate(changed)


if __name__ == "__main__":
    unittest.main()
