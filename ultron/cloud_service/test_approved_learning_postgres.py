"""Disposable PostgreSQL checks that proposed facts cannot learn without owner consent."""
import json
import os
import unittest
from pathlib import Path
try:
    import asyncpg
    from aiohttp import web
    from approved_learning import suggest_learning,list_learning_proposals,decide_learning,delete_learning_proposal
except ImportError:
    asyncpg=None
    web=None

DB=os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL","")


class Request(dict):
    def __init__(self,pool,owner="ci-learn-alpha",body=None,method="GET",proposal_id="",
                 auth="web",site="same-origin",content_type="application/json"):
        super().__init__(user_id=owner,auth_kind=auth)
        self.app={"db":pool}
        self.method=method
        self.match_info={"id":str(proposal_id)}
        self.headers={"Sec-Fetch-Site":site}
        self.content_type=content_type
        self.body=body if body is not None else {}
    async def json(self):
        return self.body


@unittest.skipUnless(bool(DB and asyncpg and web),"requires disposable PostgreSQL")
class ApprovedLearningPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool=await asyncpg.create_pool(DB,min_size=1,max_size=3)
        await self.pool.execute(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        await self.pool.execute("DELETE FROM learning_proposals WHERE user_id LIKE 'ci-learn-%'")
        await self.pool.execute("DELETE FROM memories WHERE user_id LIKE 'ci-learn-%'")
    async def asyncTearDown(self):
        await self.pool.execute("DELETE FROM learning_proposals WHERE user_id LIKE 'ci-learn-%'")
        await self.pool.execute("DELETE FROM memories WHERE user_id LIKE 'ci-learn-%'")
        await self.pool.close()

    async def add(self,owner="ci-learn-alpha",key="Communication"):
        resp=await suggest_learning(Request(self.pool,owner=owner,method="POST",body={
            "category":"PREFERENCE","key":key,"value":"Türkçe ve kısa konuş"}))
        self.assertEqual(resp.status,201)
        self.assertFalse(json.loads(resp.text)["memory_saved"])
        return json.loads(resp.text)["proposal"]["id"]

    async def test_proposal_never_saves_memory_until_explicit_approval(self):
        id=await self.add()
        self.assertEqual(await self.pool.fetchval(
            "SELECT COUNT(*) FROM memories WHERE user_id='ci-learn-alpha'"),0)
        proposals=json.loads((await list_learning_proposals(Request(self.pool))).text)
        self.assertFalse(proposals["auto_learning_enabled"])
        self.assertEqual(proposals["proposals"][0]["status"],"pending")
        self.assertEqual(len(json.loads((await list_learning_proposals(
            Request(self.pool,owner="ci-learn-beta"))).text)["proposals"]),0)
        with self.assertRaises(web.HTTPNotFound):
            await decide_learning(Request(self.pool,owner="ci-learn-beta",method="POST",
                proposal_id=id,body={"approve":True}))
        approved=await decide_learning(Request(self.pool,method="POST",
            proposal_id=id,body={"approve":True}))
        self.assertTrue(json.loads(approved.text)["memory_saved"])
        row=await self.pool.fetchrow(
            "SELECT category,key,value,updated_by_device FROM memories "
            "WHERE user_id='ci-learn-alpha' AND key='Communication'")
        self.assertEqual(row["value"],"Türkçe ve kısa konuş")
        self.assertEqual(row["updated_by_device"],"owner-approved-learning")
        again=await decide_learning(Request(self.pool,method="POST",
            proposal_id=id,body={"approve":True}))
        self.assertEqual(again.status,409)
        self.assertEqual(await self.pool.fetchval(
            "SELECT COUNT(*) FROM memories WHERE user_id='ci-learn-alpha'"),1)

    async def test_rejection_does_not_learn_and_delete_is_user_scoped(self):
        id=await self.add(key="Do not remember")
        rejected=await decide_learning(Request(self.pool,method="POST",
            proposal_id=id,body={"approve":False}))
        self.assertEqual(json.loads(rejected.text)["proposal"]["status"],"rejected")
        self.assertEqual(await self.pool.fetchval(
            "SELECT COUNT(*) FROM memories WHERE user_id='ci-learn-alpha'"),0)
        with self.assertRaises(web.HTTPNotFound):
            await delete_learning_proposal(Request(self.pool,owner="ci-learn-beta",
                method="DELETE",proposal_id=id))
        removed=await delete_learning_proposal(Request(self.pool,method="DELETE",proposal_id=id))
        self.assertTrue(json.loads(removed.text)["deleted"])

    async def test_approval_cannot_overwrite_existing_memory(self):
        await self.pool.execute(
            "INSERT INTO memories(user_id,category,key,value) "
            "VALUES('ci-learn-alpha','FACT','existing','Do not change')")
        id=await self.add(key="existing")
        conflict=await decide_learning(Request(self.pool,method="POST",
            proposal_id=id,body={"approve":True}))
        self.assertEqual(conflict.status,409)
        self.assertEqual(await self.pool.fetchval(
            "SELECT value FROM memories WHERE user_id='ci-learn-alpha' AND key='existing'"),"Do not change")
        self.assertEqual(await self.pool.fetchval(
            "SELECT status FROM learning_proposals WHERE id=$1",id),"pending")

    async def test_cross_site_and_token_rejected_no_writes(self):
        for req in [
            Request(self.pool,auth="device",method="POST",
                body={"category":"FACT","key":"key","value":"value"}),
            Request(self.pool,site="cross-site",method="POST",
                body={"category":"FACT","key":"key","value":"value"}),
        ]:
            with self.assertRaises(web.HTTPForbidden):
                await suggest_learning(req)
        with self.assertRaises(web.HTTPUnsupportedMediaType):
            await suggest_learning(Request(self.pool,content_type="text/plain",method="POST",
                body={"category":"FACT","key":"key","value":"value"}))
        self.assertEqual(await self.pool.fetchval(
            "SELECT COUNT(*) FROM learning_proposals WHERE user_id='ci-learn-alpha'"),0)

if __name__=="__main__":
    unittest.main()
