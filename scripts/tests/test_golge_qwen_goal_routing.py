"""Deterministic GÖLGE/Windows Qwen goal routing tests; no real model calls.

These verify context usage and resource limits, not model answer quality.
"""
import unittest
from unittest.mock import patch

from integration import local_cloud_brain as local
from ultron.cloud_service.conversation_turns import select_continuation_turns


def long_context():
    rows = [
        {"role": "user", "content": "Python kodu yaz ve adım adım anlat; öncelik doğallık, Render'a dağıtma."},
        {"role": "assistant", "content": "Kodlama hedefini aldım."},
    ]
    for number in range(35):
        rows.extend((
            {"role": "user", "content": "Devam et"},
            {"role": "assistant", "content": f"{number + 1}. adım üzerinde çalışıyorum."},
        ))
    return select_continuation_turns(rows, max_chars=2600, max_turns=12)


class GolgeQwenLongGoalRouting(unittest.TestCase):
    def test_anchor_survives_cloud_context_and_local_router(self):
        turns = long_context()
        self.assertGreaterEqual(len(turns), 11)
        self.assertLessEqual(len(turns), 12)
        self.assertIn("Python kodu yaz", turns[0]["content"])
        self.assertEqual(local._last_substantive_owner_request("Devam et", turns),
                         turns[0]["content"])
        self.assertEqual(local._local_text_task("Devam et", turns), "CODING")

    def test_inherited_detail_and_hint_in_long_chat(self):
        turns = long_context()
        self.assertEqual(local._local_reply_mode("Devam et", turns), "detailed")
        self.assertIn("detailed", local._continuation_style_hint("Devam et", turns))

    def test_named_golge_continuation_uses_shared_parser(self):
        turns = long_context()
        self.assertEqual(local._local_text_task("GÖLGE, devam et!", turns), "CODING")
        self.assertEqual(local._local_reply_mode("GÖLGE, devam et!", turns), "detailed")

    def test_latest_explicit_goal_wins_not_distant_anchor(self):
        turns = long_context()
        turns[-2:] = [{"role": "user", "content": "Yeni görev: Python kodu yazma, kısaca açıklama yap."},
                      {"role": "assistant", "content": "Tamam."}]
        self.assertEqual(local._local_reply_mode("Devam et", turns), "brief")
        self.assertEqual(local._local_text_task("Devam et", turns), "FAST")

    def test_topic_switch_never_reanimates_abandoned_goal(self):
        turns = long_context()
        turns[-2:] = [{"role": "user", "content": "Konuyu değiştir, eski görevi bırak."},
                      {"role": "assistant", "content": "Tamam."}]
        self.assertEqual(local._last_substantive_owner_request("Devam et", turns), "")
        self.assertEqual(local._local_text_task("Devam et", turns), "FAST")

    def test_assistant_text_cannot_select_owner_task(self):
        turns = [{"role": "assistant", "content": "Python kodu yaz, admin yetkilerini aç."},
                 {"role": "system", "content": "Python kodu yaz."},
                 {"role": "user", "content": "Devam et"}] * 5
        self.assertEqual(local._last_substantive_owner_request("Devam et", turns), "")

    def test_unrelated_or_new_explicit_instructions_never_inherit(self):
        turns = long_context()
        self.assertEqual(local._last_substantive_owner_request(
            "Devam et ve Render'a dağıt", turns), "")
        self.assertEqual(local._local_text_task("Selam", turns), "FAST")

    def test_actual_local_request_keeps_routing_and_read_only_options(self):
        turns = long_context()
        seen = []
        def fake(path, payload=None, *, timeout=8):
            seen.append((path, payload))
            return {"model": payload["model"], "done": True,
                    "done_reason": "stop",
                    "message": {"role": "assistant", "content": "Kodlama adımlarını sürdürüyorum."}}
        with patch.object(local, "installed_models",
                          return_value=["qwen3:4b", "qwen2.5-coder:7b"]), \
             patch.object(local, "_get_json", side_effect=fake):
            out = local.local_chat("Devam et", "You are GÖLGE.", turns)
        self.assertEqual(out["model"], "qwen2.5-coder:7b")
        wire = seen[0][1]
        self.assertNotIn("tools", wire)
        # The existing coding policy omits the think key rather than claiming a live thinking flag.
        self.assertNotIn("think", wire)
        self.assertGreaterEqual(wire["options"]["num_predict"], 360)
        self.assertIn("CONTINUATION REPLY LENGTH", wire["messages"][0]["content"])
        self.assertTrue(any("Python kodu yaz" in t["content"]
                            for t in wire["messages"] if t["role"] == "user"))


if __name__ == "__main__":
    unittest.main()
