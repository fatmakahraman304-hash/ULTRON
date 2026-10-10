"""Disposable PostgreSQL contracts for owner-only, explicit note lifecycle."""
import json, os, unittest, uuid
from pathlib import Path
try:
 import asyncpg
 from aiohttp import web
 from conversation_notes import draft_note,list_notes,create_note,edit_note,delete_note
except ImportError:
 asyncpg=None
 web=None
DB=os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL","")


class Request(dict):
 def __init__(self,pool,owner="ci-note-a",method="GET",body=None,conv=None,
              nid="",auth="web",site="same-origin",content_type="application/json"):
  super().__init__(user_id=owner,auth_kind=auth)
  self.app={"db":pool};self.method=method
  self.match_info={"id":str(nid)}
  self.query={"conversation_id":str(conv)} if conv else {}
  self.headers={"Sec-Fetch-Site":site}
  self.content_type=content_type
  self.body=body or {}
 async def json(self):return self.body


@unittest.skipUnless(bool(DB and asyncpg and web),"requires disposable PostgreSQL")
class NotePostgresTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.pool=await asyncpg.create_pool(DB,min_size=1,max_size=4)
  await self.pool.execute(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
  await self.pool.execute("DELETE FROM conversation_notes WHERE user_id LIKE 'ci-note-%'")
  await self.pool.execute("DELETE FROM messages WHERE user_id LIKE 'ci-note-%'")
  await self.pool.execute("DELETE FROM conversations WHERE user_id LIKE 'ci-note-%'")
  self.ca,self.cb,self.cc=uuid.uuid4(),uuid.uuid4(),uuid.uuid4()
  for conv,owner in [(self.ca,"ci-note-a"),(self.cb,"ci-note-a"),(self.cc,"ci-note-b")]:
   await self.pool.execute("INSERT INTO conversations(id,user_id,title) VALUES($1,$2,'note test')",conv,owner)
 async def asyncTearDown(self):
  await self.pool.execute("DELETE FROM conversation_notes WHERE user_id LIKE 'ci-note-%'")
  await self.pool.execute("DELETE FROM messages WHERE user_id LIKE 'ci-note-%'")
  await self.pool.execute("DELETE FROM conversations WHERE user_id LIKE 'ci-note-%'")
  await self.pool.close()

 async def test_preview_never_writes_edit_delete_user_scoped(self):
  for i,text in enumerate(("2009 Mercedes C180 konuşuyoruz",
        "Şifrem: abc-secret",
        "Mimarlık için maket tasarımı")):
   await self.pool.execute("INSERT INTO messages(conversation_id,user_id,role,content) "
     "VALUES($1,$2,'user',$3)",self.ca,"ci-note-a",text)
  await self.pool.execute("INSERT INTO messages(conversation_id,user_id,role,content) "
     "VALUES($1,$2,'user','OTHER_THREAD_PRIVATE')",self.cb,"ci-note-a")
  await self.pool.execute("INSERT INTO messages(conversation_id,user_id,role,content) "
     "VALUES($1,$2,'user','OTHER_OWNER_PRIVATE')",self.cc,"ci-note-b")
  preview=await draft_note(Request(self.pool,conv=self.ca))
  data=json.loads(preview.text)
  self.assertFalse(data["saved"])
  self.assertIn("Mercedes",data["draft"]["body"])
  self.assertIn("Mimarlık",data["draft"]["body"])
  self.assertNotIn("abc-secret",data["draft"]["body"])
  self.assertNotIn("OTHER_",data["draft"]["body"])
  self.assertEqual(await self.pool.fetchval("SELECT count(*) FROM conversation_notes "
       "WHERE user_id='ci-note-a'"),0)
  body={"conversation_id":str(self.ca),"title":"Benim notum","body":"Düzenleyip kaydettim"}
  saved=await create_note(Request(self.pool,method="POST",body=body))
  self.assertEqual(saved.status,201)
  nid=json.loads(saved.text)["note_id"]
  self.assertFalse(json.loads(saved.text)["memory_saved"])
  shown=json.loads((await list_notes(Request(self.pool,conv=self.ca))).text)["notes"]
  self.assertEqual(len(shown),1)
  self.assertEqual(shown[0]["body"],"Düzenleyip kaydettim")
  self.assertEqual(json.loads((await list_notes(Request(self.pool,conv=self.cb))).text)["notes"],[])
  with self.assertRaises(web.HTTPNotFound):
   await edit_note(Request(self.pool,owner="ci-note-b",method="PUT",nid=nid,
         body={"title":"Hırsız","body":"başka kayıt"}))
  with self.assertRaises(web.HTTPNotFound):
   await delete_note(Request(self.pool,owner="ci-note-b",method="DELETE",nid=nid))
  edited=await edit_note(Request(self.pool,method="PUT",nid=nid,
        body={"title":"Düzeltilmiş not","body":"Yeniden okudum"}))
  self.assertTrue(json.loads(edited.text)["saved"])
  self.assertEqual(json.loads((await list_notes(Request(self.pool,conv=self.ca))).text)
                   ["notes"][0]["title"],"Düzeltilmiş not")
  removed=await delete_note(Request(self.pool,method="DELETE",nid=nid))
  self.assertTrue(json.loads(removed.text)["deleted"])
  self.assertEqual(json.loads((await list_notes(Request(self.pool,conv=self.ca))).text)["notes"],[])
  self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM memories "
                  "WHERE user_id LIKE 'ci-note-%'"),0)

 async def test_denies_cross_owner_drafts_and_automatic_writes(self):
  with self.assertRaises(web.HTTPNotFound):
   await draft_note(Request(self.pool,owner="ci-note-b",conv=self.ca))
  with self.assertRaises(web.HTTPNotFound):
   await list_notes(Request(self.pool,owner="ci-note-b",conv=self.ca))
  with self.assertRaises(web.HTTPNotFound):
   await create_note(Request(self.pool,method="POST",
       body={"conversation_id":str(self.cc),"title":"Not","body":"Gizli"}))
  with self.assertRaises(web.HTTPForbidden):
   await create_note(Request(self.pool,auth="device",method="POST",
       body={"conversation_id":str(self.ca),"title":"Not","body":"Gizli"}))
  with self.assertRaises(web.HTTPForbidden):
   await create_note(Request(self.pool,site="cross-site",method="POST",
       body={"conversation_id":str(self.ca),"title":"Not","body":"Gizli"}))
  with self.assertRaises(web.HTTPUnsupportedMediaType):
   await create_note(Request(self.pool,method="POST",content_type="text/plain",
       body={"conversation_id":str(self.ca),"title":"Not","body":"Gizli"}))
  invalid=await create_note(Request(self.pool,method="POST",body={
        "conversation_id":str(self.ca),"title":"x"*200,"body":"y"}))
  self.assertEqual(invalid.status,400)
  self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM conversation_notes "
                    "WHERE user_id LIKE 'ci-note-%'"),0)

if __name__=="__main__":unittest.main()
