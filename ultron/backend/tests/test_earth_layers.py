"""No network: public layer configuration never publishes credentials."""
import importlib.util
import os
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('world_api',Path(__file__).resolve().parents[2]/'cloud_service'/'world_api.py')
world=importlib.util.module_from_spec(spec)
spec.loader.exec_module(world)

class EarthLayerTests(unittest.TestCase):
 def test_unconfigured_satellite_is_unavailable_and_map_is_not_satellite(self):
  with patch.dict(os.environ,{},clear=True):
   data=world.earth_layers_config()
  self.assertTrue(data['MAP']['available'])
  self.assertIn('openstreetmap',data['MAP']['url'])
  self.assertFalse(data['SATELLITE']['available'])
  self.assertFalse(data['TERRAIN']['available'])

 def test_unapproved_private_and_credential_urls_are_never_published(self):
  for url in ['http://tiles.example/{z}/{x}/{y}.png','https://127.0.0.1/{z}/{x}/{y}.png','https://localhost/{z}/{x}/{y}.png','https://user:password@tiles.example/{z}/{x}/{y}.png','https://tiles.example/{z}/{x}/{y}.png?token=SECRET','https://tiles.example/tiles.png']:
   with patch.dict(os.environ,{'GOLGE_SATELLITE_LICENSE_APPROVED':'1','GOLGE_SATELLITE_TILE_URL':url,'GOLGE_SATELLITE_ATTRIBUTION':'Owner'},clear=True):
    self.assertFalse(world.earth_layers_config()['SATELLITE']['available'],url)

 def test_approved_public_template_requires_attribution_and_explicit_license(self):
  env={'GOLGE_SATELLITE_TILE_URL':'https://imagery.example/{z}/{x}/{y}.jpg','GOLGE_SATELLITE_ATTRIBUTION':'Licensed imagery owner'}
  with patch.dict(os.environ,env,clear=True):self.assertFalse(world.earth_layers_config()['SATELLITE']['available'])
  with patch.dict(os.environ,{**env,'GOLGE_SATELLITE_LICENSE_APPROVED':'1'},clear=True):self.assertTrue(world.earth_layers_config()['SATELLITE']['available'])


class GeocodingTests(unittest.IsolatedAsyncioTestCase):
 async def test_country_alias_uses_real_geocoder_and_filters_wrong_localities(self):
  features=[{'properties':{'name':'Cyprus','type':'district'},'geometry':{'coordinates':[.06,51.5]}},
            {'properties':{'name':'Κύπρος - Kıbrıs','type':'country'},'geometry':{'coordinates':[33.1451,34.9823]}}]
  reader=AsyncMock(return_value={'features':features})
  with patch.object(world,'_upstream',reader):response=await world.search(SimpleNamespace(query={'q':'Kıbrıs'}))
  import json
  data=json.loads(response.body)
  self.assertEqual(len(data['results']),1)
  self.assertEqual(data['results'][0]['lat'],34.9823)
  self.assertIn('Cyprus',reader.call_args.args[0])
  self.assertEqual(data['source'],'Photon/OSM')

 async def test_invalid_and_duplicate_provider_coordinates_are_removed(self):
  features=[{'properties':{'name':'Nicosia','type':'city'},'geometry':{'coordinates':coords}} for coords in ([33.361,35.185],[33.362,35.186],[0,950],[float('nan'),0])]
  with patch.object(world,'_upstream',AsyncMock(return_value={'features':features})):
   response=await world.search(SimpleNamespace(query={'q':'Lefkoşa'}))
  import json
  self.assertEqual(len(json.loads(response.body)['results']),1)

if __name__=='__main__':unittest.main()
