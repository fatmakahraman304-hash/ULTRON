"""Disposable PostgreSQL isolation and ordered conversation context regression."""
import os,sys,unittest,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
try:
 import asyncpg
 from conversation_turns import load_thread_turns
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

if __name__=="__main__":unittest.main()
