"""Disposable PostgreSQL integration for owner-scoped ULTRON dev requests.

No real user password, GitHub token or Render account is required.
"""
import asyncio
import ast
import json
import os
import re
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace

try:
    import asyncpg
except ImportError:
    asyncpg = None

DB=os.getenv("ULTRON_QUEUE_TEST_DATABASE_URL", "")
SOURCE=Path(__file__).with_name("development_updates.py")
SCHEMA=Path(__file__).with_name("schema.sql")


def handlers():
    tree=ast.parse(SOURCE.read_text(encoding="utf-8"))
    allowed={"handoff_text","_item","_json_dumps","_http_error",
             "insert_development_request","create_request","list_requests",
             "report_desktop_version"}
    functions=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))
               and node.name in allowed]
    module=ast.Module(body=[ast.ImportFrom(module="__future__",
                        names=[ast.alias(name="annotations")],level=0),*functions],type_ignores=[])
    ast.fix_missing_locations(module)
    def response(item,status=200,**_kwargs):
        return {"status_code":status,**item}
    web=SimpleNamespace(json_response=response)
    ctx={
        "web":web,"uuid":uuid,"re":re,"json":json,
        "REPOSITORY":"fatmakahraman304-hash/ULTRON",
        "BRANCH":"feat/ultron-cloud-shared-memory",
        "TARGETS":frozenset(("phone","desktop","both")),
    }
    exec(compile(module,str(SOURCE),"exec"),ctx)
    return ctx


class FakeRequest(dict):
    def __init__(self,db,body=None,owner="ci-owner",auth_kind="web",ident=None):
        super().__init__(user_id=owner,auth_kind=auth_kind,device_id="test-device")
        self.app={"db":db}
        self.body=body if body is not None else {}
        self.match_info={"id":str(ident or uuid.uuid4())}

    async def json(self):
        return self.body


@unittest.skipUnless(DB and asyncpg, "requires disposable PostgreSQL database")
class DevRequestPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool=await asyncpg.create_pool(DB,min_size=1,max_size=3)
        async with self.pool.acquire() as conn:
            await conn.execute(SCHEMA.read_text(encoding="utf-8"))
            await conn.execute("DELETE FROM dev_requests WHERE user_id LIKE 'ci-%'")
        self.h=handlers()

    async def asyncTearDown(self):
        await self.pool.close()

    async def test_owner_scoped_request_and_no_client_supplied_success(self):
        req=FakeRequest(self.pool,{
            "prompt":"ULTRON uygulamasına yeni güvenilir sesli komut ekle",
            "target":"both","status":"completed","verified_cloud":True,
        })
        created=await self.h["create_request"](req)
        self.assertEqual(created["status_code"],201)
        item=created["request"]
        self.assertEqual(item["status"],"awaiting_chatgpt")
        self.assertFalse(item["verified_cloud"])
        self.assertFalse(item["verified_tests"])
        self.assertIn("ULTRON-DEV-"+str(item["id"]),item["handoff"])
        own=await self.h["list_requests"](FakeRequest(self.pool))
        self.assertTrue(any(x["id"]==item["id"] for x in own["requests"]))
        others=await self.h["list_requests"](FakeRequest(self.pool,owner="ci-other"))
        self.assertFalse(any(x["id"]==item["id"] for x in others["requests"]))

    async def test_request_length_scope_and_rate_limit(self):
        for body in (
            {"prompt":"short"},
            {"prompt":"A"*2001},
            {"prompt":"ultron geliştir","target":"elsewhere"},
        ):
            result=await self.h["create_request"](FakeRequest(self.pool,body))
            self.assertEqual(result["status_code"],400,result)
        for i in range(12):
            result=await self.h["create_request"](
                FakeRequest(self.pool,{"prompt":"ULTRON, kendini geliştir: özellik "+str(i)})
            )
            self.assertEqual(result["status_code"],201)
        thirteenth=await self.h["create_request"](
            FakeRequest(self.pool,{"prompt":"ULTRON, yeni özellik ekle ve test et"})
        )
        self.assertEqual(thirteenth["status_code"],429)

    async def test_phone_cannot_spoof_windows_installation(self):
        request_created=await self.h["create_request"](
            FakeRequest(self.pool,{"prompt":"ULTRON, Windows güncelleme kontrolü ekle","target":"desktop"})
        )
        item=request_created["request"]
        iphone=FakeRequest(self.pool,
                           {"commit_sha":"a"*40},
                           owner="ci-owner",
                           auth_kind="web",ident=item["id"])
        rejected=await self.h["report_desktop_version"](iphone)
        self.assertEqual(rejected["status_code"],403)
        self.assertEqual(rejected["error"],"desktop_token_required")
        row=await self.pool.fetchrow("SELECT desktop_sha,status FROM dev_requests WHERE id=$1",item["id"])
        self.assertEqual(row["desktop_sha"],"")
        self.assertEqual(row["status"],"awaiting_chatgpt")


if __name__=="__main__":
    unittest.main()
