"""Disposable Postgres regression tests: learning OFF by default and owner scoped."""
import json
import os
import unittest
from pathlib import Path
try:
    import asyncpg
    from aiohttp import web
    from auto_learning import get_auto_learning,set_auto_learning,learn_from_owner_message
except ImportError:
    asyncpg=None
    web=None
DB=os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL","")


class Request(dict):
    def __init__(self,pool,owner="ci-auto-alpha",body=None,method="GET",auth="web",
                 site="same-origin",content_type="application/json"):
        super().__init__(user_id=owner,auth_kind=auth)
        self.app={"db":pool}
        self.method=method
        self.headers={"Sec-Fetch-Site":site}
        self.content_type=content_type
        self.body=body if body is not None else {}
    async def json(self):
        return self.body


@unittest.skipUnless(bool(DB and asyncpg and web),"requires disposable PostgreSQL")
class AutoLearningPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool=await asyncpg.create_pool(DB,min_size=1,max_size=3)
        await self.pool.execute(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        await self.pool.execute("DELETE FROM owner_auto_learning WHERE user_id LIKE 'ci-auto-%'")
        await self.pool.execute("DELETE FROM memories WHERE user_id LIKE 'ci-auto-%'")
    async def asyncTearDown(self):
        await self.pool.execute("DELETE FROM memories WHERE user_id LIKE 'ci-auto-%'")
        await self.pool.execute("DELETE FROM owner_auto_learning WHERE user_id LIKE 'ci-auto-%'")
        await self.pool.close()

    async def test_default_off_owner_enable_text_learns_disable_stops(self):
        self.assertFalse(json.loads((await get_auto_learning(Request(self.pool))).text)["enabled"])
        self.assertFalse(await learn_from_owner_message(self.pool,"ci-auto-alpha",
                     "Hedefim: İngilizce öğrenmek"))
        resp=await set_auto_learning(Request(self.pool,method="PUT",body={"enabled":True}))
        self.assertTrue(json.loads(resp.text)["enabled"])
        self.assertFalse(json.loads((await get_auto_learning(Request(self.pool,
                   owner="ci-auto-beta"))).text)["enabled"])
        self.assertFalse(await learn_from_owner_message(self.pool,"ci-auto-beta",
                     "Hedefim: İngilizce öğrenmek"))
        accepted=await learn_from_owner_message(self.pool,"ci-auto-alpha",
                                                "Hedefim: İngilizce öğrenmek")
        self.assertTrue(accepted)
        self.assertFalse(await learn_from_owner_message(self.pool,"ci-auto-alpha",
                     "Hedefim: İngilizce öğrenmek"))
        rows=await self.pool.fetch("SELECT category,key,value,updated_by_device "
                     "FROM memories WHERE user_id='ci-auto-alpha'")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["category"],"GOAL")
        self.assertEqual(rows[0]["updated_by_device"],"opt-in-auto-learning")
        self.assertFalse(await learn_from_owner_message(self.pool,"ci-auto-alpha",
                                                "Tercihim: parola bu bilgi gizli"))
        await set_auto_learning(Request(self.pool,method="PUT",body={"enabled":False}))
        self.assertFalse(await learn_from_owner_message(self.pool,"ci-auto-alpha",
                                                "Projem: yeni iş projesi"))
        self.assertEqual(await self.pool.fetchval(
                     "SELECT COUNT(*) FROM memories WHERE user_id='ci-auto-alpha'"),1)

    async def test_same_origin_cookie_write_and_existing_memory_not_overwritten(self):
        for r in [
            Request(self.pool,method="PUT",body={"enabled":True},auth="device"),
            Request(self.pool,method="PUT",body={"enabled":True},site="cross-site"),
        ]:
            with self.assertRaises(web.HTTPForbidden):
                await set_auto_learning(r)
        with self.assertRaises(web.HTTPUnsupportedMediaType):
            await set_auto_learning(Request(self.pool,method="PUT",body={"enabled":True},content_type="text/plain"))
        bad=await set_auto_learning(Request(self.pool,method="PUT",body={"enabled":"yes"}))
        self.assertEqual(bad.status,400)
        await set_auto_learning(Request(self.pool,method="PUT",body={"enabled":True}))
        from auto_learning import extract_owner_statement
        cat,key,value=extract_owner_statement("Tercihim: Türkçe ve kısa cevap")
        await self.pool.execute("INSERT INTO memories(user_id,category,key,value) VALUES($1,$2,$3,$4)",
                                "ci-auto-alpha","FACT",key,"OLD")
        result=await learn_from_owner_message(self.pool,"ci-auto-alpha","Tercihim: Türkçe ve kısa cevap")
        self.assertFalse(result)
        self.assertEqual(await self.pool.fetchval(
                        "SELECT value FROM memories WHERE user_id=$1 AND key=$2","ci-auto-alpha",key),"OLD")

if __name__=="__main__":
    unittest.main()
