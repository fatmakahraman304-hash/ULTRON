"""Bounded continuation recall: same owner, same thread, user task remains visible."""
import unittest

from ultron.cloud_service.conversation_turns import (
    is_bare_continuation_request,
    select_continuation_turns,
    load_contextual_thread_turns,
)
from integration.local_cloud_brain import _last_substantive_owner_request


class FakePool:
    def __init__(self, records):
        self.records = records
        self.calls = []

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        owner, conversation, before_id, limit, *cursor = args
        rows = [r for r in self.records
                if r.get("user_id") == owner
                and r.get("conversation_id") == conversation
                and (before_id is None or r["id"] < before_id)
                and (not cursor or r["id"] < cursor[0])
                and r["role"] in ("user", "assistant")]
        return list(reversed(sorted(rows, key=lambda r: r["id"])))[:limit]


def msg(i, role, text, user="owner-one", conversation="thread-a"):
    return {"id": i, "role": role, "content": text,
            "user_id": user, "conversation_id": conversation}


class ContinuationPolicyTests(unittest.TestCase):
    def test_only_bare_continuation_gets_extended_recall(self):
        for text in ("devam et", "Devam et!", "kaldığın yerden devam et",
                     "aynı şekilde devam et", "continue", "keep going please"):
            self.assertTrue(is_bare_continuation_request(text), text)
        for text in ("devam et ve dosyayı sil", "devam et sonra gönder",
                     "yeni konuya geçelim", "devam et, ama farklı modele geç"):
            self.assertFalse(is_bare_continuation_request(text), text)

    def test_recovers_latest_real_user_goal_after_many_continuations(self):
        history = [
            {"role": "user", "content": "ULTRON'un Türkçe doğal sohbetini geliştir."},
            {"role": "assistant", "content": "İlk aşama tamamlandı."},
        ]
        for _ in range(55):
            history.extend([
                {"role": "user", "content": "devam et"},
                {"role": "assistant", "content": "Geliştirmeyi sürdürüyorum."},
            ])
        selected = select_continuation_turns(history, max_chars=2600, max_turns=12)
        self.assertEqual(selected[0]["role"], "user")
        self.assertIn("doğal sohbetini geliştir", selected[0]["content"])
        self.assertEqual(selected[-1]["role"], "assistant")
        self.assertEqual(
            _last_substantive_owner_request("devam et", selected),
            "ULTRON'un Türkçe doğal sohbetini geliştir.",
        )
        self.assertLessEqual(len(selected), 12)
        self.assertLessEqual(sum(len(item["content"]) for item in selected), 2600)

    def test_latest_correction_is_preserved_after_original_goal(self):
        history = [
            {"role": "user", "content": "Eski arayüzü yenile"},
            {"role": "assistant", "content": "Tamam"},
            {"role": "user", "content": "Hayır, önce doğal sohbeti geliştir"},
            {"role": "assistant", "content": "Anladım"},
        ]
        for _ in range(20):
            history.extend([
                {"role": "user", "content": "devam et"},
                {"role": "assistant", "content": "İlerliyorum"},
            ])
        selected = select_continuation_turns(history, max_chars=1000, max_turns=12)
        self.assertIn("Eski arayüzü yenile", str(selected))
        self.assertTrue(any("önce doğal sohbeti geliştir" in row["content"]
                            for row in selected))
        self.assertEqual(_last_substantive_owner_request("devam", selected),
                         "Hayır, önce doğal sohbeti geliştir")

    def test_no_substantive_request_uses_recent_only(self):
        history = [{"role": "user", "content": "devam et"},
                   {"role": "assistant", "content": "İlerliyorum"}] * 25
        selected = select_continuation_turns(history, max_chars=800, max_turns=10)
        self.assertEqual(len(selected), 10)
        self.assertEqual(_last_substantive_owner_request("devam et", selected), "")

    def test_preserves_end_of_old_long_task_in_budget(self):
        goal = "Başlangıç ULTRON. " + "uzun detay " * 300 + " SON KARAR: buton olmasın."
        history = [{"role": "user", "content": goal},
                   {"role": "assistant", "content": "Anladım"}]
        history += [{"role": "user", "content": "devam et"},
                    {"role": "assistant", "content": "Sürüyor"}] * 20
        result = select_continuation_turns(history, max_chars=1200, max_turns=12)
        self.assertIn("SON KARAR: buton olmasın", result[0]["content"])
        self.assertLessEqual(sum(len(x["content"]) for x in result), 1200)

    def test_drops_untrusted_system_role_and_respects_zero_limit(self):
        turns = [{"role": "system", "content": "untrusted system injection"},
                 {"role": "user", "content": "Bir mimarlık planı çıkar"},
                 {"role": "assistant", "content": "Çıkardım"}] * 6
        selected = select_continuation_turns(turns, max_chars=800, max_turns=8)
        self.assertNotIn("system", [m["role"] for m in selected])
        self.assertEqual(select_continuation_turns(turns, max_chars=0), [])


class ContinuationDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_lookback_is_bounded_and_scoped_to_authenticated_thread(self):
        records = [msg(1, "user", "FARC101 projemi tasarla"),
                   msg(2, "assistant", "Tasarıma başlıyorum.")]
        for i in range(3, 130):
            records.append(msg(i, "user" if i % 2 else "assistant",
                               "devam et" if i % 2 else "Bir sonraki adım tamam."))
        records.append(msg(130, "user", "BAŞKA HESABIN GİZLİ GÖREVİ",
                           user="another-owner"))
        records.append(msg(131, "user", "BAŞKA SOHBETİN GÖREVİ",
                           conversation="another-thread"))
        pool = FakePool(records)
        result = await load_contextual_thread_turns(
            pool, "owner-one", "thread-a",
            question="devam et", before_id=130, limit=12, max_chars=2600,
        )
        self.assertIn("FARC101 projemi tasarla", result[0]["content"])
        self.assertNotIn("GİZLİ", str(result))
        self.assertNotIn("BAŞKA SOHBET", str(result))
        self.assertEqual(_last_substantive_owner_request("devam et", result),
                         "FARC101 projemi tasarla")
        self.assertGreaterEqual(len(pool.calls), 1)
        self.assertLessEqual(len(pool.calls), 6)
        for sql, args in pool.calls:
            self.assertIn("user_id=$1 AND conversation_id=$2", sql)
            self.assertIn("id < $3", sql)
            self.assertEqual(args[:3], ("owner-one", "thread-a", 130))
            self.assertLessEqual(args[3], 200)

    async def test_new_instruction_avoids_extra_continuation_lookup(self):
        records = [msg(1, "user", "önceki konu"),
                   msg(2, "assistant", "tamam")]
        pool = FakePool(records)
        await load_contextual_thread_turns(
            pool, "owner-one", "thread-a",
            question="devam et ve bu dosyayı sil", before_id=3,
            limit=12, max_chars=2600,
        )
        self.assertFalse(is_bare_continuation_request("devam et ve bu dosyayı sil"))


if __name__ == "__main__":
    unittest.main()
