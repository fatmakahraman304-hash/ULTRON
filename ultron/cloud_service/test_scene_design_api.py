"""Actual authenticated HTTP boundary, synthetic generation only."""
import json
import os
import unittest
from unittest.mock import patch
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import app as cloud
from test_scene_design import GOOD

class DesignApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env=patch.dict(os.environ,{'ULTRON_DEVICE_TOKEN':'scene_test_only'})
        self.env.start()
        app=web.Application(middlewares=[cloud.auth_middleware])
        app.router.add_post('/api/scene-design',cloud.scene_design)
        self.client=TestClient(TestServer(app));await self.client.start_server()
    async def asyncTearDown(self):
        await self.client.close();self.env.stop()
    async def test_auth_and_no_generation_on_invalid_input(self):
        with patch.object(cloud,'_gemini_reply') as generate:
            r=await self.client.post('/api/scene-design',json={'description':'masa'})
            self.assertEqual(r.status,401)
            r=await self.client.post('/api/scene-design',json={'description':'x'*241},headers={'Authorization':'Bearer scene_test_only'})
            self.assertEqual(r.status,400);generate.assert_not_called()
    async def test_data_only_result_and_safe_failure_without_database(self):
        headers={'Authorization':'Bearer scene_test_only'}
        with patch.object(cloud,'_gemini_reply',return_value=json.dumps(GOOD)) as generate:
            r=await self.client.post('/api/scene-design',json={'description':'masa'},headers=headers)
            self.assertEqual(r.status,200);self.assertEqual((await r.json())['design'],GOOD)
            self.assertEqual(generate.call_args.args[2],[])
        with patch.object(cloud,'_gemini_reply',return_value='{"code":"alert(1)"}'):
            r=await self.client.post('/api/scene-design',json={'description':'masa'},headers=headers)
            self.assertEqual(r.status,502);self.assertNotIn('alert',await r.text())
