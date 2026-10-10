"""Real disposable PostgreSQL: targeted personal context with strict tenant bounds."""
import os
import unittest
from pathlib import Path
try:
    import asyncpg
    from app import _memory_context
except ImportError:
    asyncpg=None
DB=os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL","")


@unittest.skipUnless(bool(DB and asyncpg),"requires disposable PostgreSQL")
class PersonalContextPgTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
    self.pool=await asyncpg.create_pool(DB,min_size=1,max_size=3)
    await self.pool.execute(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
    await self.pool.execute("DELETE FROM memories WHERE user_id LIKE 'ci-focus-%'")
    await self.pool.execute("DELETE FROM owner_plans WHERE user_id LIKE 'ci-focus-%'")
 async def asyncTearDown(self):
    await self.pool.execute("DELETE FROM memories WHERE user_id LIKE 'ci-focus-%'")
    await self.pool.execute("DELETE FROM owner_plans WHERE user_id LIKE 'ci-focus-%'")
    await self.pool.close()

 async def test_topic_preference_plans_and_no_cross_account_leaks(self):
    await self.pool.execute(
      "INSERT INTO memories(user_id,category,key,value) VALUES "
      "('ci-focus-a','PROJECT','Mercedes C180','Araç bakım incelemesi'),"
      "('ci-focus-a','PREFERENCE','Yanıt tarzı','Türkçe ve kısa konuş'),"
      "('ci-focus-b','FACT','PRIVATE_OTHER_OWNER','SECRET_DONT_INCLUDE')")
    for i in range(30):
      await self.pool.execute("INSERT INTO memories(user_id,category,key,value) "
            "VALUES('ci-focus-a','FACT',$1,$2)",f"Alakasız {i}",f"Başka konu {i}")
    await self.pool.execute(
      "INSERT INTO owner_plans(user_id,title,scheduled_date,note) "
      "VALUES('ci-focus-a','Gelecek mimarlık sınavı',CURRENT_DATE+1,'never expose this note'),"
      "('ci-focus-b','PRIVATE_OTHER_OWNER_PLAN',CURRENT_DATE+1,'secret')")
    focussed=await _memory_context(self.pool,"ci-focus-a","Mercedes C180")
    self.assertIn("Mercedes C180",focussed)
    self.assertIn("Türkçe ve kısa",focussed)
    self.assertIn("Gelecek mimarlık sınavı",focussed)
    self.assertNotIn("SECRET_DONT_INCLUDE",focussed)
    self.assertNotIn("PRIVATE_OTHER_OWNER",focussed)
    self.assertNotIn("never expose this note",focussed)
    self.assertLessEqual(len(focussed),3400)
    other=await _memory_context(self.pool,"ci-focus-b","Mercedes C180")
    self.assertNotIn("Araç bakım incelemesi",other)
    self.assertNotIn("Gelecek mimarlık sınavı",other)

if __name__=="__main__":
    unittest.main()
