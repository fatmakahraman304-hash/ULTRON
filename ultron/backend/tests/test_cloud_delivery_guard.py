"""Regression tests for Cloud lease fencing; no accounts/network required."""
import asyncio
import io
import json
import sys
import time
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


class SyncLeaseClient:
    def __init__(self, outcomes=()):
        self.outcomes = list(outcomes)
        self.calls = []

    def renew_lease_sync(self, command_id, *, delivery_attempt, timeout):
        self.calls.append((command_id, delivery_attempt, timeout))
        if self.outcomes:
            outcome = self.outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
        return {"ok": True}


class LeaseGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_dedicated_lease_renews_even_while_event_loop_blocked(self):
        client = SyncLeaseClient()
        guard = RemoteLeaseGuard(
            client, 161, 2, interval=.015, request_timeout=.08,
            max_unconfirmed=.18,
        )
        task = asyncio.create_task(guard.run())
        await asyncio.sleep(.025)
        # A synchronous GUI/voice stall would prevent an asyncio-only lease.
        time.sleep(.10)
        self.assertGreaterEqual(len(client.calls), 4)
        self.assertFalse(guard.lost.is_set())
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_dedicated_lease_fences_rejected_attempt(self):
        client = SyncLeaseClient([CloudDeliveryRejected(409, "stale_delivery_attempt")])
        guard = RemoteLeaseGuard(client, 161, 1, interval=.01)
        await asyncio.wait_for(guard.run(), .5)
        self.assertTrue(guard.lost.is_set())
        self.assertIn("stale_delivery_attempt", guard.reason)
        self.assertEqual(client.calls[0][:2], (161, 1))

    async def test_dedicated_lease_gives_up_after_network_failure(self):
        client = SyncLeaseClient([RuntimeError("offline")] * 200)
        guard = RemoteLeaseGuard(
            client, 161, 2, interval=.01, request_timeout=.03,
            max_unconfirmed=.07,
        )
        await asyncio.wait_for(guard.run(), .5)
        self.assertTrue(guard.lost.is_set())
        self.assertIn("unconfirmed", guard.reason)


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



class LocalChatIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client=CloudClient()

    async def asyncTearDown(self):
        self.client._executor.shutdown(wait=True, cancel_futures=True)
        self.client._local_executor.shutdown(wait=True, cancel_futures=True)

    async def test_local_inference_survives_default_executor_shutdown(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        executor=ThreadPoolExecutor(max_workers=1)
        asyncio.get_running_loop().set_default_executor(executor)
        executor.shutdown(wait=True)
        with self.assertRaises(RuntimeError):
            await asyncio.to_thread(lambda: None)
        with patch('integration.local_cloud_brain.local_chat', side_effect=lambda *args: threading.current_thread().name):
            name=await self.client.local_chat('Synthetic request','Synthetic system',[])
        self.assertTrue(name.startswith('ultron-qwen'))

    async def test_completion_network_retry_reuses_result_and_fence(self):
        from unittest.mock import AsyncMock
        fn=AsyncMock(side_effect=[urllib.error.URLError('lost response'),{'ok':True,'replayed':True}])
        with patch.object(self.client,'_request',fn), patch('cloud_client.asyncio.sleep',new_callable=AsyncMock):
            result=await self.client.complete_task(12,delivery_attempt=3,ok=True,extra={'provider':'local-ollama','assistant_reply':'synthetic','model':'qwen3:4b'})
        self.assertTrue(result['replayed'])
        self.assertEqual(fn.await_count,2)
        self.assertEqual(fn.await_args_list[0],fn.await_args_list[1])

    async def test_nonlocal_actions_and_fenced_results_are_never_retried(self):
        from unittest.mock import AsyncMock
        for extra,error in [({},urllib.error.URLError('lost')),({'provider':'local-ollama'},CloudDeliveryRejected(409,'stale'))]:
            fn=AsyncMock(side_effect=error)
            with patch.object(self.client,'_request',fn),self.assertRaises(type(error)):
                await self.client.complete_task(12,delivery_attempt=3,ok=True,extra=extra)
            self.assertEqual(fn.await_count,1)


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

    def test_cloud_claim_has_bounded_http_timeout(self):
        client=CloudClient()
        client.base_url="https://example.invalid"
        client.device_token="test-only"
        try:
            # Check the actual sync request forwarded to the HTTP transport;
            # no real network call or secret is needed.
            with patch("urllib.request.urlopen") as urlopen:
                response=urlopen.return_value.__enter__.return_value
                response.read.return_value=b'{"commands":[]}'
                client._sync_request("POST","/api/device-commands/claim",
                                     {"target":"desktop"},timeout=10.0)
                self.assertEqual(urlopen.call_args.kwargs.get("timeout"),10.0)
        finally:
            client._executor.shutdown(wait=False,cancel_futures=True)

    def test_503_is_transient_not_a_stale_attempt(self):
        with self.assertRaises(RuntimeError) as captured:
            self.simulated_http_error(503,"/api/device-commands/8/progress",'{"error":"unavailable"}')
        self.assertNotIsInstance(captured.exception,CloudDeliveryRejected)


if __name__=="__main__":
    unittest.main()
