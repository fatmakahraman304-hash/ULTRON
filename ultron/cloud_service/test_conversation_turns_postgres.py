"""Disposable PostgreSQL isolation and ordered conversation context regression."""
import os,sys,unittest,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
try:
 import asyncpg
 from conversation_turns import load_thread_turns, load_contextual_thread_turns, is_thread_recap_request
except ImportError:
 asyncpg=None
DB=os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL","")


@unittest.skipUnless(bool(DB and asyncpg),"requires disposable PostgreSQL")
class ConversationTurnsPgTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.pool=await asyncpg.create_pool(DB,min_size=1,max_size=3)
  await self.pool.execute(HERE.joinpath("schema.sql").read_text(encoding="utf-8"))
  await self.pool.execute("DELETE FROM messages WHERE user_id LIKE 'ci-dialogue-%'")
  await self.pool.execute("DELETE FROM conversations WHERE user_id LIKE 'ci-dialogue-%'")
  self.c1,self.c2,self.c3=uuid.uuid4(),uuid.uuid4(),uuid.uuid4()
  for ident,owner in [(self.c1,"ci-dialogue-a"),(self.c2,"ci-dialogue-a"),(self.c3,"ci-dialogue-b")]:
   await self.pool.execute("INSERT INTO conversations(id,user_id,title) VALUES($1,$2,'test')",ident,owner)
  async def add(cid,owner,role,text):
   return await self.pool.fetchval("INSERT INTO messages(conversation_id,user_id,role,content) "
      "VALUES($1,$2,$3,$4) RETURNING id",cid,owner,role,text)
  self.add=add
 async def asyncTearDown(self):
  await self.pool.execute("DELETE FROM messages WHERE user_id LIKE 'ci-dialogue-%'")
  await self.pool.execute("DELETE FROM conversations WHERE user_id LIKE 'ci-dialogue-%'")
  await self.pool.close()
 async def test_context_not_leak_other_conversation_or_user_or_current_message(self):
  await self.add(self.c1,"ci-dialogue-a","user","Arabayı konuşalım")
  await self.add(self.c1,"ci-dialogue-a","assistant","Tamam")
  await self.add(self.c2,"ci-dialogue-a","user","SECRET_FROM_OTHER_THREAD")
  await self.add(self.c3,"ci-dialogue-b","user","SECRET_FROM_OTHER_USER")
  current_id=await self.add(self.c1,"ci-dialogue-a","user","Peki fiyatı?")
  turns=await load_thread_turns(self.pool,"ci-dialogue-a",self.c1,before_id=current_id)
  self.assertEqual([x["content"] for x in turns],["Arabayı konuşalım","Tamam"])
  self.assertNotIn("Peki fiyatı?",str(turns))
  self.assertNotIn("SECRET_FROM_OTHER",str(turns))
  self.assertEqual(await load_thread_turns(self.pool,"ci-dialogue-b",self.c1),[])
  self.assertEqual(await load_thread_turns(self.pool,"ci-dialogue-a",self.c3),[])


 async def test_explicit_topic_recalls_older_in_thread_without_leaking_other_messages(self):
  await self.add(self.c1,"ci-dialogue-a","user","Mercedes C180 2009 modelinin bakımını konuşalım")
  await self.add(self.c1,"ci-dialogue-a","assistant","Mercedes C180 bakımını araştırabiliriz")
  await self.add(self.c2,"ci-dialogue-a","user","PRIVATE OTHER THREAD MERCEDES C180")
  await self.add(self.c3,"ci-dialogue-b","user","PRIVATE OTHER USER MERCEDES C180")
  for i in range(24):
   await self.add(self.c1,"ci-dialogue-a","user" if i%2==0 else "assistant",
      f"Genel günlük sohbet {i} hakkında konuşuyoruz")
  current=await self.add(self.c1,"ci-dialogue-a","user","Mercedes C180 için ne demiştik?")
  turns=await load_contextual_thread_turns(
    self.pool,"ci-dialogue-a",self.c1,question="Mercedes C180 için ne demiştik?",
    before_id=current,max_chars=3000,limit=14,
  )
  text=" ".join(t["content"] for t in turns)
  self.assertIn("Mercedes C180 2009",text)
  self.assertNotIn("PRIVATE",text)
  self.assertNotIn("ne demiştik?",text)
  self.assertLessEqual(sum(len(t["content"]) for t in turns),3000)
  self.assertEqual(await load_contextual_thread_turns(self.pool,"ci-dialogue-b",
      self.c1,question="Mercedes C180"),[])
  self.assertEqual(await load_contextual_thread_turns(self.pool,"ci-dialogue-a",
      self.c3,question="Mercedes C180"),[])

 async def test_on_demand_recap_samples_start_middle_end_without_other_users(self):
  await self.add(self.c1,"ci-dialogue-a","user","BAŞLANGIÇ: Mimarlık maketi")
  await self.add(self.c1,"ci-dialogue-a","assistant","Maket fikri üzerine konuştuk")
  for i in range(26):
   await self.add(self.c1,"ci-dialogue-a","user" if i%2==0 else "assistant",
                  f"ORTA-KONU {i}: renkler ve malzemeler")
  await self.add(self.c2,"ci-dialogue-a","user","OTHER_THREAD_PRIVATE_SECRET")
  await self.add(self.c3,"ci-dialogue-b","user","OTHER_USER_PRIVATE_SECRET")
  await self.add(self.c1,"ci-dialogue-a","user","SON: ULTRON sesli komut")
  await self.add(self.c1,"ci-dialogue-a","assistant","Mikrofonu geliştireceğiz")
  current=await self.add(self.c1,"ci-dialogue-a","user","Bu sohbeti özetle")
  turns=await load_contextual_thread_turns(self.pool,"ci-dialogue-a",self.c1,
          question="Bu sohbeti özetle",before_id=current,max_chars=2800,limit=14)
  material=" | ".join(x["content"] for x in turns)
  self.assertIn("BAŞLANGIÇ:",material)
  self.assertIn("ORTA-KONU 13",material)
  self.assertIn("SON:",material)
  self.assertNotIn("OTHER_",material)
  self.assertNotIn("Bu sohbeti özetle",material)
  self.assertLessEqual(sum(len(x["content"]) for x in turns),2800)
  self.assertEqual(await load_contextual_thread_turns(
      self.pool,"ci-dialogue-b",self.c1,question="Bu sohbeti özetle"),[])
  self.assertEqual(await load_contextual_thread_turns(
      self.pool,"ci-dialogue-a",self.c3,question="Bu sohbeti özetle"),[])

 async def test_first_topic_beyond_80_messages_is_owner_scoped_and_deduplicated(self):
  await self.add(self.c1,"ci-dialogue-a","user","2009 Mercedes C180 başlangıç")
  await self.add(self.c1,"ci-dialogue-a","assistant","Motor versiyonunu doğrula")
  await self.add(self.c2,"ci-dialogue-a","user","OTHER_THREAD_SECRET")
  await self.add(self.c3,"ci-dialogue-b","user","OTHER_OWNER_SECRET")
  for i in range(100):
   await self.add(self.c1,"ci-dialogue-a","user" if i%2==0 else "assistant",f"Mimarlık aşama {i}")
  current=await self.add(self.c1,"ci-dialogue-a","user","İlk söylediğine geri dön.")
  turns=await load_contextual_thread_turns(self.pool,"ci-dialogue-a",self.c1,
      question="İlk söylediğine geri dön.",before_id=current,max_chars=2600,limit=12)
  self.assertIn("2009 Mercedes C180",str(turns))
  self.assertIn("aşama 99",str(turns))
  self.assertNotIn("SECRET",str(turns))
  self.assertNotIn("geri dön",str(turns))
  self.assertLessEqual(len(turns),12)
  self.assertEqual(await load_contextual_thread_turns(self.pool,"ci-dialogue-b",self.c1,
      question="İlk söylediğine geri dön."),[])
  other=await load_contextual_thread_turns(self.pool,"ci-dialogue-a",self.c2,
      question="İlk söylediğine geri dön.")
  self.assertEqual(len(other),1)

 async def test_recap_after_120_messages_preserves_true_middle_and_isolation(self):
  await self.add(self.c1,"ci-dialogue-a","user","TRUE_START: Mercedes C180")
  await self.add(self.c1,"ci-dialogue-a","assistant","İlk yanıt")
  await self.add(self.c2,"ci-dialogue-a","user","OTHER_THREAD_SECRET")
  await self.add(self.c3,"ci-dialogue-b","user","OTHER_OWNER_SECRET")
  for i in range(124):
   text = "TRUE_MIDDLE: Mimarlık maketi" if i == 61 else f"Later topic {i}"
   await self.add(self.c1,"ci-dialogue-a",
                  "user" if i%2==0 else "assistant", text)
  await self.add(self.c1,"ci-dialogue-a","user","TRUE_END: ULTRON ses")
  await self.add(self.c1,"ci-dialogue-a","assistant","Mikrofon konuşması")
  current = await self.add(self.c1,"ci-dialogue-a","user","Bu sohbeti özetle")
  turns = await load_contextual_thread_turns(
      self.pool,"ci-dialogue-a",self.c1,question="Bu sohbeti özetle",
      before_id=current,max_chars=2800,limit=14)
  combined = " ".join(t["content"] for t in turns)
  self.assertIn("TRUE_START:", combined)
  self.assertIn("TRUE_MIDDLE:", combined)
  self.assertIn("TRUE_END:", combined)
  self.assertNotIn("OTHER_", combined)
  self.assertLessEqual(len(turns),14)
  self.assertLessEqual(sum(len(t["content"]) for t in turns),2800)


 async def test_explicit_named_topic_beyond_last_80_preserves_exchange_and_tenant(self):
  await self.add(self.c1,"ci-dialogue-a","user","Mercedes C180 2009 bakım konuşması")
  await self.add(self.c1,"ci-dialogue-a","assistant","Motor masrafını doğrulayalım")
  await self.add(self.c2,"ci-dialogue-a","user","OTHER_THREAD_MERCEDES_C180")
  await self.add(self.c3,"ci-dialogue-b","user","OTHER_OWNER_MERCEDES_C180")
  for i in range(124):
   await self.add(self.c1,"ci-dialogue-a",
                  "user" if i%2==0 else "assistant",f"Günlük genel konu {i}")
  current=await self.add(self.c1,"ci-dialogue-a","user",
                         "Mercedes C180 hakkında ne demiştik?")
  turns=await load_contextual_thread_turns(
      self.pool,"ci-dialogue-a",self.c1,
      question="Mercedes C180 hakkında ne demiştik?",
      before_id=current,max_chars=2800,limit=14)
  combined=" ".join(t["content"] for t in turns)
  self.assertIn("Mercedes C180 2009",combined)
  self.assertIn("Motor masrafını",combined)
  self.assertIn("genel konu 123",combined)
  self.assertNotIn("OTHER_",combined)
  self.assertLessEqual(len(turns),14)
  self.assertLessEqual(sum(len(t["content"]) for t in turns),2800)


 async def test_old_answer_survives_incidental_recent_topic_and_owner_isolation(self):
  await self.add(self.c1,"ci-dialogue-a","user","Mercedes C180 2009 orijinal fren masrafı")
  await self.add(self.c1,"ci-dialogue-a","assistant","Ön fren disklerini kontrol edelim")
  await self.add(self.c2,"ci-dialogue-a","user","OTHER_THREAD Mercedes C180 special")
  await self.add(self.c3,"ci-dialogue-b","user","OTHER_OWNER Mercedes C180 special")
  for i in range(124):
   text=("Mercedes C180 sadece örnek, eski fren yanıtı yok" if i==40
         else f"İlgisiz güncel sohbet {i}")
   await self.add(self.c1,"ci-dialogue-a",
                  "user" if i%2==0 else "assistant",text)
  current=await self.add(self.c1,"ci-dialogue-a","user",
                         "Mercedes C180 hakkında ne demiştik?")
  turns=await load_contextual_thread_turns(
      self.pool,"ci-dialogue-a",self.c1,
      question="Mercedes C180 hakkında ne demiştik?",
      before_id=current,max_chars=3000,limit=14)
  text=" ".join(x["content"] for x in turns)
  self.assertIn("orijinal fren masrafı",text)
  self.assertIn("Ön fren disklerini",text)
  self.assertIn("güncel sohbet 123",text)
  self.assertNotIn("OTHER_THREAD",text)
  self.assertNotIn("OTHER_OWNER",text)
  self.assertLessEqual(len(turns),14)
  self.assertLessEqual(sum(len(x["content"]) for x in turns),3000)


 async def test_long_historical_answer_conclusion_survives_deep_recall(self):
  question=("Mercedes C180 2009 fren sistemi sorusu. "
            + "teknik ayrıntı " * 90
            + " SON SORU: Balata mı disk mi?")
  answer=("İlk teknik değerlendirme. " + "uzun açıklama " * 100
          + " SON KARAR: Ön disk ve balata kontrolü.")
  await self.add(self.c1,"ci-dialogue-a","user",question)
  await self.add(self.c1,"ci-dialogue-a","assistant",answer)
  for i in range(110):
   await self.add(self.c1,"ci-dialogue-a",
                  "user" if i%2==0 else "assistant", f"Güncel konu {i}")
  await self.add(self.c2,"ci-dialogue-a","user",
                 "OTHER_THREAD SON KARAR: gizli")
  await self.add(self.c3,"ci-dialogue-b","assistant",
                 "OTHER_OWNER SON KARAR: gizli")
  current=await self.add(self.c1,"ci-dialogue-a","user",
                         "Mercedes C180 hakkında ne demiştik?")
  turns=await load_contextual_thread_turns(
      self.pool,"ci-dialogue-a",self.c1,
      question="Mercedes C180 hakkında ne demiştik?",
      before_id=current,max_chars=3000,limit=14)
  material=" ".join(row["content"] for row in turns)
  self.assertIn("SON SORU",material)
  self.assertIn("SON KARAR: Ön disk",material)
  self.assertIn("Güncel konu 109",material)
  self.assertNotIn("OTHER_THREAD",material)
  self.assertNotIn("OTHER_OWNER",material)
  self.assertLessEqual(len(turns),14)
  self.assertLessEqual(sum(len(row["content"]) for row in turns),3000)


 async def test_earliest_decision_survives_more_than_24_old_keyword_hits(self):
  await self.add(self.c1,"ci-dialogue-a","user",
                 "Mercedes C180 2009 ORIGINAL_PLAN inspect front discs")
  await self.add(self.c1,"ci-dialogue-a","assistant",
                 "Original conclusion: start with front brake inspection")
  await self.add(self.c2,"ci-dialogue-a","user",
                 "OTHER_THREAD Mercedes C180 original fake")
  await self.add(self.c3,"ci-dialogue-b","user",
                 "OTHER_OWNER Mercedes C180 original fake")
  for i in range(42):
   await self.add(self.c1,"ci-dialogue-a",
                  "user" if i%2==0 else "assistant",
                  f"Mercedes C180 repeated old reference {i}")
  for i in range(105):
   await self.add(self.c1,"ci-dialogue-a",
                  "user" if i%2==0 else "assistant",
                  f"Unrelated latest conversation {i}")
  current=await self.add(self.c1,"ci-dialogue-a","user",
                         "Mercedes C180 hakkında ne demiştik?")
  found=await load_contextual_thread_turns(
      self.pool,"ci-dialogue-a",self.c1,
      question="Mercedes C180 hakkında ne demiştik?",
      before_id=current,max_chars=3500,limit=14)
  material=" ".join(t["content"] for t in found)
  self.assertIn("ORIGINAL_PLAN",material)
  self.assertIn("Original conclusion",material)
  self.assertIn("conversation 104",material)
  self.assertNotIn("OTHER_THREAD",material)
  self.assertNotIn("OTHER_OWNER",material)
  self.assertLessEqual(len(found),14)
  self.assertLessEqual(sum(len(t["content"]) for t in found),3500)


if __name__=="__main__":unittest.main()
