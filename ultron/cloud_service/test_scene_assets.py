import copy
import json
import struct
import unittest
from unittest.mock import patch
from scene_assets import search, pack_gltf, read_url, download

class AssetsTests(unittest.TestCase):
    def test_search_dynamic_catalog_and_no_unrelated_substitution(self):
        assets={'chair_new':{'type':2,'name':'New Chair','tags':['wood','chair'],'authors':{'Artist':'All'}},'rock':{'type':2,'name':'Rock','tags':['stone']},'carpet':{'type':2,'name':'Carpet','tags':['fabric']}}
        with patch('scene_assets.catalog',return_value=assets):
            result=search('ahşap sandalye modeli')
            self.assertEqual(result[0]['id'],'chair_new');self.assertEqual(result[0]['license'],'CC0-1.0')
            self.assertEqual(search('spaceship'),[])
            self.assertEqual(search('araba'),[])
    def test_allowlist_before_network(self):
        for url in ['http://dl.polyhaven.org/file/ph-assets/Models/a','https://localhost/a','https://dl.polyhaven.org.evil/a','https://user@dl.polyhaven.org/file/ph-assets/Models/a','https://dl.polyhaven.org/not-models/a']:
            with self.assertRaises(ValueError):read_url(url,20)
    def test_embed_buffers_and_drop_external_texture_references(self):
        doc={'asset':{'version':'2.0'},'buffers':[{'uri':'a.bin','byteLength':3},{'uri':'b.bin','byteLength':4}],'bufferViews':[{'buffer':1,'byteOffset':0,'byteLength':4}],'images':[{'uri':'https://evil.invalid/a.png'}],'materials':[{}],'meshes':[{'primitives':[{'material':0,'attributes':{'POSITION':0}}]}]}
        glb=pack_gltf(doc,[b'abc',b'defg']);magic,version,size=struct.unpack('<III',glb[:12])
        self.assertEqual((magic,version,size),(0x46546c67,2,len(glb)))
        length=struct.unpack('<I',glb[12:16])[0];result=json.loads(glb[20:20+length])
        self.assertEqual(result['bufferViews'][0]['byteOffset'],4)
        self.assertNotIn('images',result);self.assertNotIn('uri',result['buffers'][0]);self.assertNotIn('material',result['meshes'][0]['primitives'][0])
    def test_invalid_geometry_boundaries(self):
        for doc,buffers in [({'asset':{'version':'2.0'},'buffers':[{'byteLength':10}]},[b'x']),({'asset':{'version':'2.0'},'buffers':[{'byteLength':1}],'bufferViews':[{'buffer':0,'byteLength':9}]},[b'x']),({'asset':{'version':'2.0'},'skins':[{}]},[])]:
            with self.assertRaises(ValueError):pack_gltf(doc,buffers)
    def test_download_fetches_only_catalogue_declared_buffers(self):
        doc={'asset':{'version':'2.0'},'buffers':[{'uri':'mesh.bin','byteLength':3}]}
        metadata={'gltf':{'1k':{'gltf':{'url':'https://dl.polyhaven.org/file/ph-assets/Models/m.gltf','include':{'mesh.bin':{'size':3,'url':'https://dl.polyhaven.org/file/ph-assets/Models/m.bin'}}}}}}
        with patch('scene_assets.catalog',return_value={'mesh':{'type':2}}),patch('scene_assets.read_url',side_effect=[json.dumps(metadata).encode(),json.dumps(doc).encode(),b'abc']) as read:
            self.assertTrue(download('mesh').startswith(b'glTF'));self.assertEqual(read.call_count,3)
        with patch('scene_assets.catalog',return_value={}):
            with self.assertRaises(ValueError):download('../private')
