"""Exercise the actual Cloud queue handlers without needing Render/Postgres.

The handlers are extracted from app.py via AST to avoid importing optional
Google/asyncpg integrations. The fake DB models the SQL's guarded state
transitions, and explicit SQL assertions protect the concurrency contract.
This is an isolated regression test, NOT a live Postgres end-to-end test.
"""
from __future__ import annotations

import ast
import asyncio
import json
import re
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().with_name("app.py")


class FakeHTTPError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(kwargs.get("text") or (args[0] if args else ""))


class HTTPBadRequest(FakeHTTPError):
    pass


class HTTPForbidden(FakeHTTPError):
    pass


class HTTPNotFound(FakeHTTPError):
    pass


class HTTPConflict(FakeHTTPError):
    pass


def load_handlers():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    handlers = {
        node.name: node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name in {"complete_device_command", "claim_device_commands", "append_device_command_progress", "save_device_command_checkpoint"}
    }
    if len(handlers) != 4:
        raise AssertionError("Cloud command handlers not found")
    module = ast.Module(body=[
        ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
        *handlers.values(),
    ], type_ignores=[])
    ast.fix_missing_locations(module)
    web = SimpleNamespace(
        Request=object, Response=object,
        HTTPBadRequest=HTTPBadRequest, HTTPForbidden=HTTPForbidden,
        HTTPNotFound=HTTPNotFound, HTTPConflict=HTTPConflict,
        json_response=lambda body, **kwargs: body,
    )
    ns = {"web": web, "json": json, "time": time, "_json_dumps": json.dumps}
    exec(compile(module, str(SOURCE), "exec"), ns)
    return ns


class FakeRequest(dict):
    def __init__(self, db, body, kind="device", command_id="1"):
        super().__init__(user_id="owner", auth_kind=kind)
        self.app = {"db": db}
        self.match_info = {"id": command_id}
        self.body = dict(body)
        if kind == "device" and "delivery_attempt" not in self.body:
            self.body["delivery_attempt"] = 1

    async def json(self):
        return self.body


class FakeDB:
    def __init__(self, status="delivered", retry_count=0, max_retries=2):
        self.status = status
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.command = "agent_task"
        self.delivery_attempt = 1
        self.result = {"message": "initial"}
        self.queries = []

    async def fetchrow(self, sql, *args):
        self.queries.append((sql, args))
        if sql.lstrip().startswith("SELECT"):
            return {"status": self.status, "command": self.command,
                    "delivery_attempt": self.delivery_attempt,
                    "retry_count": self.retry_count, "max_retries": self.max_retries}
        # Enforce the same atomic CAS preconditions as the real UPDATE SQL.
        if self.status != "delivered" or (self.command == "agent_task" and self.delivery_attempt != args[-1]):
            return None
        if "SET status='queued'" in sql:
            if self.retry_count >= self.max_retries:
                return None
            self.status = "queued"
            self.retry_count += 1
            self.result = json.loads(args[0])
        else:
            self.status = args[0]
            self.result = json.loads(args[1])
        return {"id": 1, "target": "desktop", "command": "agent_task",
                "status": self.status, "result": self.result,
                "retry_count": self.retry_count, "max_retries": self.max_retries}


class ProgressDB:
    """Execute real progress/checkpoint handlers against fenced in-memory state."""
    def __init__(self, attempt=2):
        self.delivery_attempt = attempt
        self.status = "delivered"
        self.command = "agent_task"
        self.progress = []
        self.checkpoint = {}
        self.renew_count = 0
        self.queries = []

    async def fetchrow(self, sql, *args):
        self.queries.append((sql,args))
        if self.status != "delivered" or self.command != "agent_task":
            return None
        if args[-1] != self.delivery_attempt:
            return None
        if "SET delivered_at=NOW()" in sql:
            self.renew_count += 1
            return {"id":1, "status":self.status,"delivered_at":None}
        if "SET checkpoint=" in sql:
            self.checkpoint = json.loads(args[0])
            return {"id":1,"status":self.status,"checkpoint":self.checkpoint,"progress":list(self.progress)}
        if "SET progress =" in sql:
            self.progress.extend(json.loads(args[0]))
            return {"id":1,"status":self.status,"progress":list(self.progress)}
        raise AssertionError("Unexpected SQL from Cloud queue handler")


class FakeTransaction:
    def __init__(self, lock):
        self.lock = lock

    async def __aenter__(self):
        await self.lock.acquire()
        return self

    async def __aexit__(self, *_args):
        self.lock.release()


class ClaimDB:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.command_status = {1: "queued", 2: "queued"}
        self.attempts = {1: 0, 2: 0}
        self.advisory_calls = 0
        self.sql = []

    def acquire(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def transaction(self):
        return FakeTransaction(self.lock)

    async def execute(self, sql, *_args):
        self.sql.append(sql)
        if "pg_advisory_xact_lock" in sql:
            self.advisory_calls += 1

    async def fetch(self, sql, *_args):
        self.sql.append(sql)
        if "NOT EXISTS" not in sql or "FOR UPDATE SKIP LOCKED" not in sql:
            raise AssertionError("claim SQL must preserve lane/row protection")
        if any(status == "delivered" for status in self.command_status.values()):
            return []
        for command_id, status in self.command_status.items():
            if status == "queued":
                self.command_status[command_id] = "delivered"
                self.attempts[command_id] += 1
                return [{"id": command_id, "target": "desktop", "command": "agent_task",
                         "payload": {"text": "safe test"}, "source_device": "test",
                         "progress": [], "checkpoint": {}, "retry_count": 0,
                         "max_retries": 2, "delivery_attempt": self.attempts[command_id],
                         "created_at": None}]
        return []


class CloudQueueContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.handlers = load_handlers()

    async def test_completed_command_cannot_be_overwritten(self):
        db = FakeDB()
        req = FakeRequest(db, {"status": "completed", "result": {"message": "done"}})
        first = await self.handlers["complete_device_command"](req)
        self.assertEqual(first["command"]["status"], "completed")
        self.assertEqual(db.result["message"], "done")
        with self.assertRaises(HTTPConflict):
            await self.handlers["complete_device_command"](FakeRequest(
                db, {"status": "failed", "result": {"message": "stale reply"}}))
        self.assertEqual(db.status, "completed")
        self.assertEqual(db.result["message"], "done")

    async def test_inactive_commands_cannot_be_completed(self):
        for state in ["queued", "cancelled", "expired", "failed", "completed"]:
            with self.subTest(status=state):
                db = FakeDB(status=state)
                with self.assertRaises(HTTPConflict):
                    await self.handlers["complete_device_command"](FakeRequest(
                        db, {"status": "completed", "result": {}}))
                self.assertEqual(db.status, state)

    async def test_retry_only_when_delivered_and_within_limit(self):
        db = FakeDB(max_retries=1)
        body = {"status": "failed", "result": {"retryable": True, "message": "temporary", "retry_after_seconds": 15}}
        result = await self.handlers["complete_device_command"](FakeRequest(db, body))
        self.assertEqual(result["command"]["status"], "queued")
        self.assertEqual(db.retry_count, 1)
        with self.assertRaises(HTTPConflict):
            await self.handlers["complete_device_command"](FakeRequest(db, body))
        db.status = "delivered"
        db.delivery_attempt += 1
        result = await self.handlers["complete_device_command"](FakeRequest(db, dict(body, delivery_attempt=2)))
        self.assertEqual(result["command"]["status"], "failed")
        self.assertEqual(db.retry_count, 1)

    async def test_claims_serialize_one_agent_task(self):
        db = ClaimDB()
        first, second = await asyncio.gather(*[
            self.handlers["claim_device_commands"](FakeRequest(db, {"target": "desktop"}))
            for _ in range(2)
        ])
        self.assertEqual(len(first["commands"]) + len(second["commands"]), 1)
        self.assertEqual(sum(state == "delivered" for state in db.command_status.values()), 1)
        self.assertEqual(db.advisory_calls, 2)
        self.assertEqual(sum(db.attempts.values()), 1)
        claimed = first["commands"] or second["commands"]
        self.assertEqual(claimed[0]["delivery_attempt"], 1)

    async def test_claim_direction_guard(self):
        db = ClaimDB()
        with self.assertRaises(HTTPForbidden):
            await self.handlers["claim_device_commands"](FakeRequest(db, {"target": "phone"}, "device"))
        self.assertEqual(db.advisory_calls, 0)


    async def test_old_worker_cannot_complete_after_reclaim(self):
        db = FakeDB(status="delivered", retry_count=1, max_retries=2)
        db.delivery_attempt = 2
        with self.assertRaises(HTTPConflict):
            await self.handlers["complete_device_command"](FakeRequest(db, {
                "delivery_attempt": 1, "status": "completed",
                "result": {"message": "old worker result"}
            }))
        self.assertEqual(db.status, "delivered")
        current = await self.handlers["complete_device_command"](FakeRequest(db, {
            "delivery_attempt": 2, "status": "completed",
            "result": {"message": "new worker result"}
        }))
        self.assertEqual(current["command"]["status"], "completed")
        self.assertEqual(db.result["message"], "new worker result")

    async def test_missing_delivery_attempt_is_rejected_for_agent_tasks(self):
        db = FakeDB()
        with self.assertRaises(HTTPConflict):
            await self.handlers["complete_device_command"](FakeRequest(db, {
                "status": "completed", "delivery_attempt": None,
                "result": {"message": "missing lease proof"}
            }))
        self.assertEqual(db.status, "delivered")

    async def test_old_worker_cannot_win_racing_completion(self):
        db = FakeDB()
        db.delivery_attempt = 3
        requests = [
            FakeRequest(db, {"delivery_attempt": 2, "status": "completed", "result": {"message": "stale"}}),
            FakeRequest(db, {"delivery_attempt": 3, "status": "completed", "result": {"message": "current"}}),
        ]
        result = await asyncio.gather(
            *(self.handlers["complete_device_command"](r) for r in requests), return_exceptions=True
        )
        self.assertEqual(sum(not isinstance(v, Exception) for v in result), 1)
        self.assertTrue(any(isinstance(v, HTTPConflict) for v in result))
        self.assertEqual(db.result["message"], "current")

    def test_progress_checkpoint_and_lease_sql_use_fencing(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        for name in ("append_device_command_progress", "save_device_command_checkpoint"):
            fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == name)
            sql = "\n".join(node.value for node in ast.walk(fn)
                            if isinstance(node, ast.Constant) and isinstance(node.value, str))
            self.assertIn("delivery_attempt", sql)
            self.assertIn("status='delivered'", sql)
            self.assertIn("command='agent_task'", sql)
        schema = SOURCE.with_name("schema.sql").read_text(encoding="utf-8")
        self.assertIn("ADD COLUMN IF NOT EXISTS delivery_attempt", schema)

    async def test_nonagent_control_retains_legacy_completion(self):
        db = FakeDB()
        db.command = "wake"
        out = await self.handlers["complete_device_command"](FakeRequest(db, {
            "status": "completed", "delivery_attempt": None,
            "result": {"message": "awake"}
        }))
        self.assertEqual(out["command"]["status"], "completed")


    async def test_lease_and_progress_are_fenced_after_reclaim(self):
        db = ProgressDB(attempt=2)
        for stage in ("lease", "executing"):
            with self.assertRaises(HTTPNotFound):
                await self.handlers["append_device_command_progress"](FakeRequest(
                    db, {"delivery_attempt":1,"stage":stage,"message":"stale"}
                ))
        self.assertEqual(db.renew_count,0)
        self.assertEqual(db.progress,[])
        lease = await self.handlers["append_device_command_progress"](FakeRequest(
            db, {"delivery_attempt":2,"stage":"lease"}
        ))
        self.assertEqual(lease["command"]["status"],"delivered")
        self.assertEqual(db.renew_count,1)
        response = await self.handlers["append_device_command_progress"](FakeRequest(
            db, {"delivery_attempt":2,"stage":"executing","message":"safe","percent":50}
        ))
        self.assertEqual(response["command"]["progress"][-1]["message"],"safe")

    async def test_checkpoint_stale_worker_cannot_overwrite_current(self):
        db = ProgressDB(attempt=3)
        with self.assertRaises(HTTPNotFound):
            await self.handlers["save_device_command_checkpoint"](FakeRequest(
                db, {"delivery_attempt":2,"step_index":40,"note":"stale",
                     "state":{"last_action":"delete"}}
            ))
        self.assertEqual(db.checkpoint,{})
        response = await self.handlers["save_device_command_checkpoint"](FakeRequest(
            db, {"delivery_attempt":3,"step_index":4,"note":"current",
                 "state":{"last_action":"safe"}}
        ))
        self.assertEqual(response["command"]["checkpoint"]["step_index"],4)
        self.assertEqual(db.checkpoint["note"],"current")

    def test_desktop_client_follows_delivery_fencing(self):
        client = SOURCE.parent.parent / "backend" / "cloud_client.py"
        desktop = SOURCE.parent.parent.parent / "mark_app.py"
        client_source = client.read_text(encoding="utf-8")
        desktop_source = desktop.read_text(encoding="utf-8")
        for method in ("report_task_progress","save_task_checkpoint","complete_task"):
            self.assertIn("async def "+method,client_source)
        self.assertGreaterEqual(client_source.count('"delivery_attempt": int(delivery_attempt)'),2)
        self.assertIn("delivery_attempt = int(item.get(\"delivery_attempt\") or 0)",desktop_source)
        self.assertIn("delivery_attempt=delivery_attempt",desktop_source)

    def test_sql_uses_atomic_compare_and_set(self):
        ns = load_handlers()
        # Capture SQL text from the actual handler's AST, not a copied fixture.
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        for name in ("complete_device_command", "claim_device_commands"):
            fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == name)
            sql = "\n".join(node.value for node in ast.walk(fn)
                            if isinstance(node, ast.Constant) and isinstance(node.value, str))
            if name == "complete_device_command":
                self.assertGreaterEqual(len(re.findall(r"AND status='delivered'", sql)), 2)
                self.assertIn("AND retry_count < max_retries", sql)
                self.assertGreaterEqual(sql.count("delivery_attempt=$6"), 2)
            else:
                self.assertIn("pg_advisory_xact_lock", sql)
                self.assertIn("FOR UPDATE SKIP LOCKED", sql)
                self.assertIn("NOT EXISTS", sql)
                self.assertIn("delivery_attempt=delivery_attempt+1", sql)
        self.assertTrue(callable(ns["complete_device_command"]))


if __name__ == "__main__":
    unittest.main()
