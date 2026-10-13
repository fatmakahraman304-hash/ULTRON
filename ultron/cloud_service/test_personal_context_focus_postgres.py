"""Real disposable PostgreSQL: targeted personal context with strict tenant bounds."""
import os
import unittest
from pathlib import Path
try:
    import asyncpg
    from personal_context_focus import load_focused_owner_context
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
      "('ci-focus-b','FACT','PRIVATE_OTHER_OWNER Mercedes C180','SECRET_DONT_INCLUDE')")
    for i in range(130):
      await self.pool.execute("INSERT INTO memories(user_id,category,key,value) "
            "VALUES('ci-focus-a','FACT',$1,$2)",f"Alakasız {i}",f"Başka konu {i}")
    await self.pool.execute(
      "INSERT INTO owner_plans(user_id,title,scheduled_date,note) "
      "VALUES('ci-focus-a','Gelecek mimarlık sınavı',CURRENT_DATE+1,'never expose this note'),"
      "('ci-focus-b','PRIVATE_OTHER_OWNER_PLAN',CURRENT_DATE+1,'secret')")
    focussed=await load_focused_owner_context(self.pool,"ci-focus-a","Mercedes C180")
    self.assertIn("Mercedes C180",focussed)
    self.assertIn("Türkçe ve kısa",focussed)
    self.assertIn("Gelecek mimarlık sınavı",focussed)
    self.assertNotIn("SECRET_DONT_INCLUDE",focussed)
    self.assertNotIn("PRIVATE_OTHER_OWNER",focussed)
    self.assertNotIn("never expose this note",focussed)
    self.assertLessEqual(len(focussed),3400)
    other=await load_focused_owner_context(self.pool,"ci-focus-b","Mercedes C180")
    self.assertNotIn("Araç bakım incelemesi",other)
    self.assertNotIn("Gelecek mimarlık sınavı",other)

 async def test_future_not_hidden_by_overdue_backlog_and_past_request(self):
    # Real PostgreSQL ORDER BY/LIMIT is essential: pure Python sorting cannot
    # rescue future plans that an older SQL LIMIT already discarded.
    await self.pool.execute(
       "INSERT INTO owner_plans(user_id,title,scheduled_date,note) "
       "SELECT 'ci-focus-time', 'OLD-STALLED-' || n, CURRENT_DATE - n, "
       "'do not expose private note' FROM generate_series(1,20) AS items(n)")
    await self.pool.execute(
       "INSERT INTO owner_plans(user_id,title,scheduled_date,note) VALUES "
       "('ci-focus-time','FUTURE-ARCHITECTURE-EXAM',CURRENT_DATE+2,'private'),"
       "('ci-focus-time','FUTURE-DESIGN-REVIEW',CURRENT_DATE+3,'private')")
    upcoming = await load_focused_owner_context(self.pool, "ci-focus-time",
                                                 "Merhaba")
    self.assertIn("FUTURE-ARCHITECTURE-EXAM", upcoming)
    self.assertIn("FUTURE-DESIGN-REVIEW", upcoming)
    self.assertNotIn("OLD-STALLED-", upcoming)
    self.assertIn("future date", upcoming)
    self.assertNotIn("do not expose private note", upcoming)
    historical = await load_focused_owner_context(
        self.pool, "ci-focus-time", "Geçmiş planlarımı göster")
    self.assertIn("OLD-STALLED-1", historical)
    self.assertIn("past date, not upcoming", historical)
    self.assertNotIn("FUTURE-ARCHITECTURE-EXAM", historical)

if __name__=="__main__":
    unittest.main()
