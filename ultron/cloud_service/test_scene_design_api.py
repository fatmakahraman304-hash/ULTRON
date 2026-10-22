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
        from scene_assets import register
        register(app)
        self.client=TestClient(TestServer(app));await self.client.start_server()
    async def asyncTearDown(self):
        await self.client.close();self.env.stop()
    async def test_auth_and_no_generation_on_invalid_input(self):
        with patch.object(cloud,'_gemini_reply') as generate:
            r=await self.client.post('/api/scene-design',json={'description':'sihirli tilki'})
            self.assertEqual(r.status,401)
            r=await self.client.post('/api/scene-design',json={'description':'x'*241},headers={'Authorization':'Bearer scene_test_only'})
            self.assertEqual(r.status,400);generate.assert_not_called()
    async def test_data_only_result_and_safe_failure_without_database(self):
        headers={'Authorization':'Bearer scene_test_only'}
        with patch.object(cloud,'_gemini_reply',return_value=json.dumps(GOOD)) as generate:
            r=await self.client.post('/api/scene-design',json={'description':'sihirli tilki'},headers=headers)
            self.assertEqual(r.status,200);self.assertEqual((await r.json())['design'],GOOD)
            self.assertEqual(generate.call_args.args[2],[])
        with patch.object(cloud,'_gemini_reply',return_value='{"code":"alert(1)"}'):
            r=await self.client.post('/api/scene-design',json={'description':'sihirli tilki'},headers=headers)
            self.assertEqual(r.status,502);self.assertNotIn('alert',await r.text())

    async def test_asset_endpoints_keep_auth_boundary(self):
        with patch('scene_assets.search') as search,patch('scene_assets.download') as download:
            for path in ['/api/scene-assets?query=chair','/api/scene-assets/chair']:
                self.assertEqual((await self.client.get(path)).status,401)
            search.assert_not_called();download.assert_not_called()
        with patch('scene_assets.search',return_value=[]):
            r=await self.client.get('/api/scene-assets?query=chair',headers={'Authorization':'Bearer scene_test_only'})
            self.assertEqual(r.status,200);self.assertEqual((await r.json())['items'],[])


class LibraryApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_known_shape_is_built_without_a_model_call(self):
        env=patch.dict(os.environ,{'ULTRON_DEVICE_TOKEN':'scene_test_only'});env.start()
        app=web.Application(middlewares=[cloud.auth_middleware]);app.router.add_post('/api/scene-design',cloud.scene_design)
        app.router.add_post('/api/scene-library',cloud.scene_library)
        client=TestClient(TestServer(app));await client.start_server()
        try:
            h={'Authorization':'Bearer scene_test_only'}
            r=await client.post('/api/scene-library',json={'description':'kalp'},headers=h);self.assertEqual(len((await r.json())['design']['parts']),3)
            r=await client.post('/api/scene-library',json={'description':'sihirli tilki'},headers=h);self.assertEqual((r.status,(await r.json())['design']),(200,None))
            r=await client.post('/api/scene-library',json={'description':'x'*241},headers=h);self.assertEqual(r.status,400)
            self.assertEqual((await client.post('/api/scene-library',json={'description':'kalp'})).status,401)
            with patch.object(cloud,'_gemini_reply') as generate:
                r=await client.post('/api/scene-design',json={'description':'8 köşeli yıldız'},headers={'Authorization':'Bearer scene_test_only'})
                body=await r.json()
                self.assertEqual((r.status,body['source']),(200,'library'))
                self.assertEqual(len(body['design']['parts']),9)
                generate.assert_not_called()
        finally:
            await client.close();env.stop()
