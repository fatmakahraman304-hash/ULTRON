"""Opt-in live public CC0 download + real WebGL. No model inference or private data."""
import asyncio
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ultron/cloud_service'))
from scene_assets import search,download
from test_scene_browser import SceneBrowserTests

class PublicAssetSmoke(SceneBrowserTests):
    async def runTest(self):
        items=await asyncio.to_thread(search,'sandalye')
        self.assertTrue(items)
        asset=items[0];binary=await asyncio.to_thread(download,asset['id'])
        await self.page.route('**/api/scene-assets?*',lambda route:route.fulfill(json={'items':items}))
        await self.page.route('**/api/scene-assets/'+asset['id'],lambda route:route.fulfill(body=binary,content_type='model/gltf-binary'))
        await self.engine();await self.command('internetten sandalye modeli bul getir')
        state=await self.state();self.assertTrue(state['parts'])
        self.assertIn(asset['source'],await self.page.locator('#sceneNotice').inner_text())
        await self.command('onu sağa taşı');await self.command('onu yok et')
        self.assertEqual((await self.state())['parts'],[])
        await self.command('geri al');self.assertEqual(len((await self.state())['parts']),len(state['parts']))
        self.assertEqual(self.errors,[])
        await self.page.screenshot(path='/tmp/golge-public-asset.png')
        print('PUBLIC_CC0_ASSET',asset['id'],len(binary),'bytes',len(state['parts']),'parts',asset['source'])

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([PublicAssetSmoke()]))
    sys.exit(not result.wasSuccessful())
