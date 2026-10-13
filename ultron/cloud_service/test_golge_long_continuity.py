"""GÖLGE: long-running 'devam et' goal continuity without implicit memory."""
import asyncio
import unittest

from conversation_turns import (
    is_bare_continuation_request,
    select_continuation_turns,
    load_contextual_thread_turns,
)
from conversation_persona import build_system_instruction


def chain(*, corrections=(), n=32):
    rows=[
        {"role":"user","content":"GÖLGE: Önce doğal sohbeti geliştir. Hologramı ve Render'ı değiştirme, gerçek testleri bitir."},
        {"role":"assistant","content":"Sohbet iyileştirme ilk adımı test edildi."},
    ]
    for sentence in corrections:
        rows.append({"role":"user","content":sentence})
        rows.append({"role":"assistant","content":"Talimat düzeltildi, not edildi."})
    for i in range(n):
        rows.append({"role":"user","content":"Devam et"})
        rows.append({"role":"assistant","content":f"{i+1}. aşamada ilerledim."})
    return rows


class GolgeLongContinuation(unittest.TestCase):
    def test_only_bare_go_ahead_triggers_anchoring(self):
        for phrase in ("Devam et", "devam", "GÖLGE devam et!",
                       "Gölge, devam o zaman", "Devam et büyük aşamaya",
                       "Kaldığın yerden devam et", "keep going", "continue"):
            with self.subTest(phrase=phrase):
                self.assertTrue(is_bare_continuation_request(phrase))
        for phrase in ("Devam et ama önce e-postalarımı silme",
                       "Devam et ve Render'a dağıt", "GÖLGE yeni hologram yap",
                       "Yarın 16:00'da hatırlat", "Bir önceki adı unut",
                       "Ne olmuştu?", None, ""):
            with self.subTest(phrase=phrase):
                self.assertFalse(is_bare_continuation_request(phrase))

    def test_recovers_original_owner_goal_after_32_empty_continuations(self):
        result=select_continuation_turns(chain(),max_chars=1600,max_turns=12)
        self.assertIn("Önce doğal sohbeti geliştir",result[0]["content"])
        self.assertIn("Render'ı değiştirme",result[0]["content"])
        self.assertIn("32. aşamada ilerledim",result[-1]["content"])
        self.assertTrue(all(x["role"] in ("user","assistant") for x in result))
        self.assertLessEqual(len(result),12)
        self.assertLessEqual(sum(len(x["content"]) for x in result),1600)

    def test_owner_correction_is_kept_after_initial_goal(self):
        result=select_continuation_turns(chain(
            corrections=["Hayır, gerçek Windows testi yapılmadan yayınlama."]),
            max_chars=2400,max_turns=12)
        self.assertIn("doğal sohbeti geliştir",result[0]["content"])
        self.assertEqual(result[1]["content"],
                         "Hayır, gerçek Windows testi yapılmadan yayınlama.")
        self.assertIn("32. aşamada ilerledim",result[-1]["content"])

    def test_recent_concrete_request_dominates_previous_goal(self):
        rows=chain()
        rows.extend([
            {"role":"user","content":"Şimdi yeni görev: sadece ses kalitesini test et."},
            {"role":"assistant","content":"Ses kalitesini incelemeye başladım."},
            {"role":"user","content":"Devam et"},
            {"role":"assistant","content":"Ses işlemeye devam ediyorum."},
        ])
        result=select_continuation_turns(rows,max_chars=1200,max_turns=12)
        self.assertNotIn("doğal sohbeti geliştir",str(result))
        self.assertIn("sadece ses kalitesini",str(result))

    def test_does_not_recover_abandoned_topic(self):
        rows=chain(n=15)
        rows.append({"role":"user","content":"Konuyu değiştir, bir önceki işi bırak."})
        rows.append({"role":"assistant","content":"Yeni konuya geçildi."})
        rows.extend([
            {"role":"user","content":"Devam et"},
            {"role":"assistant","content":"Yeni konu bekleniyor."}
        ]*12)
        result=select_continuation_turns(rows,max_chars=1800,max_turns=12)
        self.assertNotIn("doğal sohbeti geliştir",str(result))

    def test_not_recover_or_fabricate_when_only_repeated_continuations(self):
        rows=chain()[2:]
        result=select_continuation_turns(rows,max_chars=700,max_turns=8)
        self.assertNotIn("doğal sohbeti geliştir",str(result))
        self.assertLessEqual(len(result),8)

    def test_prior_history_does_not_create_a_fake_tool_completion(self):
        guidance=build_system_instruction(
            user_message="Devam et",has_prior_turns=True,read_only=True,
            max_chars=4800)
        self.assertIn("latest specific USER goal",guidance)
        self.assertIn("Do not claim any work was completed",guidance)
        self.assertIn("READ-ONLY MODE",guidance)
        no_history=build_system_instruction(
            user_message="Devam et",has_prior_turns=False)
        self.assertIn("FOLLOW-UP WITHOUT CONTEXT",no_history)


class ScopedDatabaseContinuation(unittest.IsolatedAsyncioTestCase):
    async def test_same_owner_thread_query_and_caps(self):
        class DB:
            def __init__(self):
                self.calls=[]
            async def fetch(self,sql,*args):
                self.calls.append((sql,args))
                rows=chain(n=34)
                return [dict(id=i+1,**row) for i,row in reversed(list(enumerate(rows)))]
        db=DB()
        out=await load_contextual_thread_turns(
            db,"owner-G","conversation-Q",question="Devam et",
            before_id=888,max_chars=1500,limit=12,lookback=80)
        self.assertTrue(db.calls)
        self.assertEqual(len(db.calls),1)
        sql,args=db.calls[0]
        self.assertIn("user_id=$1 AND conversation_id=$2",sql)
        self.assertIn("id < $3",sql)
        self.assertIn("ORDER BY id DESC LIMIT $4",sql)
        self.assertEqual(args,("owner-G","conversation-Q",888,80))
        self.assertIn("Önce doğal sohbeti geliştir",str(out))
        self.assertLessEqual(len(out),12)
        self.assertLessEqual(sum(len(x["content"]) for x in out),1500)

    async def test_no_global_history_for_other_goals(self):
        class DB:
            def __init__(self):
                self.queries=[]
            async def fetch(self,query,*args):
                self.queries.append((query,args))
                return []
        db=DB()
        result=await load_contextual_thread_turns(
            db,"owner-X","thread-X",question="Devam et",
            before_id=6,limit=10)
        self.assertEqual(result,[])
        self.assertEqual(len(db.queries),1)
        self.assertEqual(db.queries[0][1][:3],("owner-X","thread-X",6))


if __name__=="__main__":
    unittest.main()
