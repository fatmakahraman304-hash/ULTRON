"""Long-running GÖLGE conversation correctness without an LLM or owner data."""
import unittest
from conversation_turns import (
    is_bare_continuation, is_thread_recap_request, _topic_terms,
    load_contextual_thread_turns, ollama_messages, gemini_turns,
)


class FakeThread:
    def __init__(self, rows):
        self.rows=rows
        self.calls=[]

    async def fetch(self, sql, *args):
        self.calls.append((sql,args))
        # Model the scoped DB rows, newest-first descending, without touching
        # another user's conversation even if records were in the source.
        owner, thread, before=args[:3]
        rows=[r for r in self.rows if r["owner"]==owner
              and r["thread"]==thread
              and (before is None or r["id"]<before)]
        if "AND id < $4" in sql:
            rows=[r for r in rows if r["id"] < args[3]]
        if "AND role='user'" in sql:
            rows=[r for r in rows if r["role"]=="user"]
        rows.sort(key=lambda r:r["id"], reverse=True)
        return [dict(r) for r in rows[:args[-1]]]


def build_chat():
    rows=[{"owner":"a","thread":"goal","id":1,"role":"user",
           "content":"GÖLGE, mimarlık planımı geliştir. Önce basit çizim sonra detaylı odalar. Asla dosya silme."},
          {"owner":"a","thread":"goal","id":2,"role":"assistant","content":"Basit taslak hazır."}]
    for n in range(3,125):
        rows.append({"owner":"a","thread":"goal","id":n,
                     "role":"user" if n%2 else "assistant",
                     "content":"devam et" if n%2 else "Yeni bir adım."})
    rows.extend([
        {"owner":"b","thread":"goal","id":500,"role":"user",
         "content":"Diğer hesaptaki gizli bilgi"},
        {"owner":"a","thread":"other","id":501,"role":"user",
         "content":"Başka konuşmadaki sır"},
    ])
    return rows


class PatternTests(unittest.TestCase):
    def test_golge_and_legacy_recap_speech(self):
        for text in ["GÖLGE, sohbetimizi özetle",
                     "Golge sohbeti özetle","ULTRON, sohbeti özetle",
                     "Bu sohbeti özetle"]:
            self.assertTrue(is_thread_recap_request(text),text)
        self.assertFalse(is_thread_recap_request("GÖLGE, önceden neler yapmıştım?"))
        self.assertNotIn("gölge",_topic_terms("GÖLGE Mercedes fiyatını anlat"))
        self.assertIn("mercedes",_topic_terms("GÖLGE Mercedes fiyatını anlat"))

    def test_only_bare_explicit_continue_uses_historical_goal(self):
        for text in ["Devam et","GÖLGE, devam et","Golge kaldığın yerden devam et",
                     "Peki devam et","continue","keep going"]:
            self.assertTrue(is_bare_continuation(text),text)
        for text in ["Devam et ve bilgisayarı kapat","Bu projenin devamı nasıl?",
                     "Konu değiştir","Bana devam etmeyi açıkla","Sil",
                     "GÖLGE, yeni bir fikir öner"]:
            self.assertFalse(is_bare_continuation(text),text)


class GoalContinuityTests(unittest.IsolatedAsyncioTestCase):
    async def test_60_continue_turns_still_preserve_original_goal_for_both_models(self):
        pool=FakeThread(build_chat())
        turns=await load_contextual_thread_turns(
            pool,"a","goal",question="Devam et",
            before_id=125,max_chars=2600,limit=12,
        )
        self.assertEqual(turns[0]["role"],"user")
        self.assertIn("mimarlık planımı",turns[0]["content"])
        self.assertIn("Asla dosya silme",turns[0]["content"])
        self.assertEqual(turns[-1]["role"],"assistant")
        self.assertLessEqual(len(turns),12)
        self.assertLessEqual(sum(len(x["content"]) for x in turns),2600)
        self.assertEqual([x["role"] for x in turns].count("system"),0)
        self.assertNotIn("Diğer hesaptaki gizli",str(turns))
        self.assertNotIn("Başka konuşmadaki sır",str(turns))
        self.assertEqual(len(pool.calls),2)
        for sql,args in pool.calls:
            self.assertIn("user_id=$1 AND conversation_id=$2",sql)
            self.assertEqual(args[:3],("a","goal",125))
            self.assertLessEqual(args[-1],240)
        self.assertIn("mimarlık planımı",str(ollama_messages("safe persona",turns,"devam et")))
        self.assertIn("mimarlık planımı",str(gemini_turns(turns,"devam et")))

    async def test_no_extra_query_when_goal_is_already_in_recent_turns(self):
        rows=build_chat()[-2:]+[
            {"owner":"a","thread":"goal","id":125,"role":"user","content":"GÖLGE, çizimi değiştirme."},
            {"owner":"a","thread":"goal","id":126,"role":"assistant","content":"Tamam"}]
        pool=FakeThread(rows)
        turns=await load_contextual_thread_turns(
            pool,"a","goal",question="devam et",max_chars=800,limit=12)
        self.assertEqual(len(pool.calls),1)
        self.assertIn("çizimi değiştirme",str(turns))

    async def test_old_owner_correction_overrides_original_goal_in_both_models(self):
        rows=build_chat()
        rows.append({"owner":"a","thread":"goal","id":55,"role":"user",
                     "content":"Hayır, düzeltme: planı yalnızca siyah yap, duvarları silme."})
        pool=FakeThread(rows)
        turns=await load_contextual_thread_turns(
            pool,"a","goal",question="GÖLGE, devam et",
            before_id=125,max_chars=2600,limit=12,
        )
        self.assertEqual([t["role"] for t in turns[:2]],["user","user"])
        self.assertIn("mimarlık planımı",turns[0]["content"])
        self.assertIn("siyah yap",turns[1]["content"])
        self.assertLess(turns[0]["content"].find("mimarlık"),len(turns[0]["content"]))
        self.assertLessEqual(sum(len(t["content"]) for t in turns),2600)
        for messages in (ollama_messages("GÖLGE",turns,"devam et"),
                         gemini_turns(turns,"devam et")):
            self.assertIn("mimarlık planımı",str(messages))
            self.assertIn("siyah yap",str(messages))

    async def test_tiny_context_never_exceeds_requested_budget(self):
        rows=build_chat()
        rows.append({"owner":"a","thread":"goal","id":55,"role":"user",
                     "content":"Hayır, yalnızca siyah"})
        pool=FakeThread(rows)
        turns=await load_contextual_thread_turns(
            pool,"a","goal",question="Devam et",before_id=125,
            max_chars=12,limit=12,
        )
        self.assertLessEqual(sum(len(t["content"]) for t in turns),12)

    async def test_topic_switch_blocks_resurrection_of_old_goal(self):
        rows=build_chat()
        rows.append({"owner":"a","thread":"goal","id":60,"role":"user",
                     "content":"Konuyu değiştir"})
        # Force a recent chat history consisting only of continuations.
        pool=FakeThread(rows)
        turns=await load_contextual_thread_turns(pool,"a","goal",question="Devam et",
                     before_id=125,max_chars=2600,limit=12)
        self.assertNotIn("mimarlık planımı",str(turns))
        self.assertTrue(all(t["role"] in ("assistant","user") for t in turns))

    async def test_missing_goal_is_not_invented_and_stays_same_owner(self):
        rows=[{"owner":"b","thread":"goal","id":1,"role":"user",
               "content":"Özel kod: GIZLI"},]
        rows +=[{"owner":"a","thread":"goal","id":i+10,
                  "role":"user" if i%2 else "assistant",
                  "content":"Devam et" if i%2 else "Önceki yanıt"}
                 for i in range(30)]
        pool=FakeThread(rows)
        turns=await load_contextual_thread_turns(pool,"a","goal",question="Devam et",limit=12)
        self.assertNotIn("GIZLI",str(turns))
        self.assertTrue(all(t["role"] in ("assistant","user") for t in turns))

    async def test_no_reuse_of_stale_goal_from_different_thread(self):
        pool=FakeThread(build_chat())
        turns=await load_contextual_thread_turns(pool,"a","new-thread",question="Devam et")
        self.assertEqual(turns,[])
        self.assertEqual(len(pool.calls),1)


if __name__=="__main__":
    unittest.main()
