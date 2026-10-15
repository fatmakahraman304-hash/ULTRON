"""Desktop routing boundary with synthetic Qwen/Cloud only."""
import asyncio
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from ultron.backend.scene_design_api import design_request

GOOD={'name':'Table','parts':[{'name':'Top','shape':'box','size':[2,.2,2],'position':[0,0,0],'rotation':[0,0,0]}]}
class DesktopDesignTests(unittest.IsolatedAsyncioTestCase):
    async def test_ready_local_and_offline_cloud_without_tools(self):
        executor=ThreadPoolExecutor(max_workers=1)
        try:
            client=SimpleNamespace(_local_executor=executor,enabled=True,local_chat=AsyncMock(return_value={'reply':json.dumps(GOOD)}),_request=AsyncMock(return_value={'design':GOOD}))
            request=SimpleNamespace(app={'scene_design_client':client},json=AsyncMock(return_value={'description':'table'}))
            with patch('integration.local_cloud_brain.local_chat_ready',return_value=True):
                r=await design_request(request);self.assertEqual(r.status,200)
                client._request.assert_not_called();self.assertEqual(client.local_chat.call_args.args[2],[])
            with patch('integration.local_cloud_brain.local_chat_ready',return_value=False):
                r=await design_request(request);self.assertEqual(r.status,200)
                client._request.assert_awaited_once()
        finally:executor.shutdown()
    async def test_invalid_local_result_does_not_silently_fallback(self):
        executor=ThreadPoolExecutor(max_workers=1)
        try:
            client=SimpleNamespace(_local_executor=executor,enabled=True,local_chat=AsyncMock(return_value={'reply':'code goes here'}),_request=AsyncMock())
            request=SimpleNamespace(app={'scene_design_client':client},json=AsyncMock(return_value={'description':'table'}))
            with patch('integration.local_cloud_brain.local_chat_ready',return_value=True):
                self.assertEqual((await design_request(request)).status,502)
                client._request.assert_not_called()
        finally:executor.shutdown()
if __name__=='__main__':unittest.main(verbosity=2)
