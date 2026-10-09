"""Execute actual release verifier using deterministic GitHub/Render stand-ins.

Integration hits real Postgres in test_dev_requests_postgres.py; this suite
focuses on the hard safety invariant: no GitHub test + live Render proof +
observed desktop version => no 'completed' claim.
"""
from __future__ import annotations
import ast
import asyncio
import json
import os
import re
import time
import types
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

SOURCE=Path(__file__).with_name("development_updates.py")
ID=uuid.UUID("123e4567-e89b-12d3-a456-426614174000")
SHA="a"*40
OLDER="b"*40
MARKER="ULTRON-DEV-"+str(ID)


class FakeDB:
    def __init__(self,target="phone",desktop_sha=""):
        self.row={
            "id":ID,"user_id":"owner","target":target,"prompt":"ULTRON kendini geliştir",
            "status":"awaiting_chatgpt","source_device":"iphone","commit_sha":"",
            "desktop_sha":desktop_sha,"verified_tests":False,"verified_cloud":False,
        }

    async def fetchrow(self, sql, *args):
        if sql.startswith("SELECT"):
            return dict(self.row)
        if "UPDATE dev_requests SET status=" in sql:
            self.row.update(status=args[2],commit_sha=args[3],
                            verified_tests=args[4],verified_cloud=args[5])
            return dict(self.row)
        raise AssertionError(sql)


class FakeRequest(dict):
    def __init__(self,db):
        super().__init__(user_id="owner")
        self.app={"db":db}
        self.match_info={"id":str(ID)}


def build_verifier():
    syntax=ast.parse(SOURCE.read_text(encoding="utf-8"))
    wanted={"verify_request","release_state","_item","handoff_text","_json_dumps","_http_error"}
    pieces=[node for node in syntax.body
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in wanted]
    prog=ast.Module(body=[
        ast.ImportFrom(module="__future__",names=[ast.alias(name="annotations")],level=0),
        *pieces
    ],type_ignores=[])
    ast.fix_missing_locations(prog)
    web=types.SimpleNamespace(json_response=lambda data,**kwargs:{**data,"http_status":kwargs.get("status",200)})
    namespace={
        "web":web,"uuid":uuid,"os":os,"time":time,"re":re,"json":json,
        "quote":quote,
        "REPOSITORY":"fatmakahraman304-hash/ULTRON",
        "BRANCH":"feat/ultron-cloud-shared-memory",
        "_VERIFICATION_CACHE":{},
        "_GITHUB_MOCK":True,
    }
    exec(compile(prog,str(SOURCE),"exec"),namespace)
    return namespace


class ReleaseProofTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ns=build_verifier()
        self.db=FakeDB()
        self.github_commits=[{"sha":SHA,"commit":{"message":"feat: patch "+MARKER}}]
        self.runs=[]
        self.cloud=SHA
        async def github(path):
            if path.startswith("/commits?"):
                return self.github_commits
            if path.startswith("/actions/runs?"):
                return {"workflow_runs":self.runs}
            if path.startswith("/compare/"):
                raise AssertionError("Unexpected compare with same sha")
            raise AssertionError(path)
        self.ns["_github_json"]=github
        self.ns["_is_ancestor"]=lambda *args: asyncio.sleep(0,result=args[0]==args[1])
        self.environment=patch.dict(os.environ,{"RENDER_GIT_COMMIT":SHA})
        self.environment.start()

    async def asyncTearDown(self):
        self.environment.stop()

    async def run_verify(self):
        return await self.ns["verify_request"](FakeRequest(self.db))

    def set_green(self,phone=True):
        names=["ULTRON Scene Build Check"]
        if phone:names.append("Cloud Queue PostgreSQL Integration")
        self.runs=[{"head_sha":SHA,"name":n,"status":"completed","conclusion":"success"} for n in names]

    async def test_missing_commit_marker_must_stay_pending(self):
        self.github_commits=[]
        self.set_green()
        reply=await self.run_verify()
        self.assertEqual(reply["request"]["status"],"awaiting_chatgpt")
        self.assertFalse(reply["request"]["verified_cloud"])

    async def test_ci_not_run_or_failed_is_not_success(self):
        reply=await self.run_verify()
        self.assertEqual(reply["request"]["status"],"tests_pending")
        self.assertFalse(reply["request"]["verified_tests"])
        self.ns["_VERIFICATION_CACHE"].clear()
        self.runs=[{"head_sha":SHA,"name":"ULTRON Scene Build Check",
                    "status":"completed","conclusion":"failure"}]
        reply=await self.run_verify()
        self.assertEqual(reply["request"]["status"],"tests_failed")
        self.assertFalse(reply["request"]["verified_cloud"])

    async def test_only_exact_sha_ci_success_not_older_green(self):
        self.runs=[{"head_sha":OLDER,"name":"ULTRON Scene Build Check",
                    "status":"completed","conclusion":"success"},
                   {"head_sha":OLDER,"name":"Cloud Queue PostgreSQL Integration",
                    "status":"completed","conclusion":"success"}]
        reply=await self.run_verify()
        self.assertEqual(reply["request"]["status"],"tests_pending")

    async def test_render_not_live_or_wrong_sha_never_completes(self):
        self.set_green()
        with patch.dict(os.environ,{"RENDER_GIT_COMMIT":OLDER}):
            reply=await self.run_verify()
            self.assertEqual(reply["request"]["status"],"release_pending")
            self.assertFalse(reply["request"]["verified_cloud"])

    async def test_phone_completes_only_with_green_ci_and_render(self):
        self.set_green()
        reply=await self.run_verify()
        self.assertEqual(reply["request"]["status"],"completed")
        self.assertTrue(reply["request"]["verified_cloud"])
        self.assertTrue(reply["request"]["verified_tests"])

    async def test_both_requires_running_desktop_version_after_ci_render(self):
        self.db=FakeDB(target="both")
        self.set_green()
        reply=await self.run_verify()
        self.assertEqual(reply["request"]["status"],"desktop_pending")
        self.ns["_VERIFICATION_CACHE"].clear()
        self.db.row["desktop_sha"]=SHA
        reply=await self.run_verify()
        self.assertEqual(reply["request"]["status"],"completed")

    async def test_desktop_only_requires_scene_and_running_sha(self):
        self.db=FakeDB(target="desktop")
        self.set_green(phone=False)
        reply=await self.run_verify()
        self.assertEqual(reply["request"]["status"],"desktop_pending")
        self.assertTrue(reply["request"]["verified_tests"])


if __name__=="__main__":
    unittest.main()
