"""Regression tests for Cloud lease fencing; no accounts/network required."""
import asyncio
import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cloud_client import CloudClient, CloudDeliveryRejected
from cloud_delivery import RemoteLeaseGuard


class FakeClient:
    def __init__(self, outcomes):
        self.outcomes=list(outcomes)
        self.calls=[]

    async def report_task_progress(self, command_id, *, delivery_attempt, stage, message):
        self.calls.append((command_id, delivery_attempt, stage, message))
        if not self.outcomes:
            return {"ok": True}
        outcome=self.outcomes.pop(0)
        if outcome=="hang":
            await asyncio.sleep(1.0)
        elif isinstance(outcome, Exception):
            raise outcome
        return {"ok": True}


class LeaseGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_conflict_stops_worker_and_preserves_claim_identity(self):
        client=FakeClient([CloudDeliveryRejected(409,"stale_delivery_attempt")])
        guard=RemoteLeaseGuard(client,42,3,interval=.01,request_timeout=.04,max_unconfirmed=.15)
        await asyncio.wait_for(guard.run(),.5)
        self.assertTrue(guard.lost.is_set())
        self.assertIn("stale_delivery_attempt",guard.reason)
        self.assertEqual(client.calls,[(42,3,"lease","")])

    async def test_not_found_stops_worker(self):
        client=FakeClient([CloudDeliveryRejected(404,"command_not_found")])
        guard=RemoteLeaseGuard(client,42,2,interval=.01,request_timeout=.04,max_unconfirmed=.15)
        await asyncio.wait_for(guard.run(),.5)
        self.assertTrue(guard.lost.is_set())
        self.assertEqual(len(client.calls),1)

    async def test_transient_failure_does_not_immediately_abort(self):
        client=FakeClient([RuntimeError("temporary network error"),True,CloudDeliveryRejected(409,"stale")])
        notes=[]
        guard=RemoteLeaseGuard(client,1,1,interval=.01,request_timeout=.08,max_unconfirmed=.2,log=notes.append)
        await asyncio.wait_for(guard.run(),.5)
        self.assertEqual(len(client.calls),3)
        self.assertTrue(guard.lost.is_set())
        self.assertTrue(any("temporary network error" in note for note in notes))

    async def test_unconfirmed_lease_times_out_and_stops(self):
        client=FakeClient(["hang"]*100)
        guard=RemoteLeaseGuard(client,15,8,interval=.01,request_timeout=.03,max_unconfirmed=.09)
        await asyncio.wait_for(guard.run(),.7)
        self.assertTrue(guard.lost.is_set())
        self.assertIn("unconfirmed",guard.reason)
        self.assertGreaterEqual(len(client.calls),2)
        self.assertLess(len(client.calls),10)

    async def test_cancel_propagates_and_does_not_mark_lease_lost(self):
        client=FakeClient([True]*20)
        guard=RemoteLeaseGuard(client,5,7,interval=.01,request_timeout=.03,max_unconfirmed=.12)
        task=asyncio.create_task(guard.run())
        await asyncio.sleep(.04)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(guard.lost.is_set())

    def test_invalid_agent_claims_rejected(self):
        for cid,attempt in [(0,1),(1,0),(-1,2),(2,-1)]:
            with self.subTest(cid=cid,attempt=attempt):
                with self.assertRaises(ValueError):
                    RemoteLeaseGuard(FakeClient([]),cid,attempt)



class CloudHTTPErrorTests(unittest.TestCase):
    def setUp(self):
        self.client=CloudClient()
        self.client.base_url="https://example.invalid"
        self.client.device_token="test-only"
        self.client.timeout_s=1

    def tearDown(self):
        self.client._executor.shutdown(wait=False, cancel_futures=True)

    def simulated_http_error(self,status,path,body):
        url=self.client.base_url+path
        error=urllib.error.HTTPError(url,status,"simulated",{},io.BytesIO(body.encode()))
        with patch("urllib.request.urlopen", side_effect=error):
            return self.client._sync_request("POST",path,{"delivery_attempt":5})

    def test_409_fences_superseded_delivery(self):
        with self.assertRaises(CloudDeliveryRejected) as captured:
            self.simulated_http_error(409,"/api/device-commands/8/progress",json.dumps({"error":"stale_delivery_attempt"}))
        self.assertEqual(captured.exception.status_code,409)
        self.assertIn("stale_delivery_attempt",str(captured.exception))

    def test_404_fences_inactive_delivery(self):
        with self.assertRaises(CloudDeliveryRejected) as captured:
            self.simulated_http_error(404,"/api/device-commands/8/checkpoint",json.dumps({"error":"command_not_found"}))
        self.assertEqual(captured.exception.status_code,404)

    def test_unrelated_404_is_not_a_lease_fence(self):
        with self.assertRaises(RuntimeError) as captured:
            self.simulated_http_error(404,"/health",'{"detail":"missing endpoint"}')
        self.assertNotIsInstance(captured.exception,CloudDeliveryRejected)

    def test_503_is_transient_not_a_stale_attempt(self):
        with self.assertRaises(RuntimeError) as captured:
            self.simulated_http_error(503,"/api/device-commands/8/progress",'{"error":"unavailable"}')
        self.assertNotIsInstance(captured.exception,CloudDeliveryRejected)


if __name__=="__main__":
    unittest.main()
