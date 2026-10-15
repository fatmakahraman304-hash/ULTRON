import copy
import json
import unittest
from scene_design import validate, description

GOOD={'name':'Masa','parts':[{'name':'Tabla','shape':'box','size':[3,.2,2],'position':[0,1,0],'rotation':[0,0,0]}]}
class DesignTests(unittest.TestCase):
    def test_valid_json_and_fence(self):
        self.assertEqual(validate(json.dumps(GOOD)),GOOD)
        self.assertEqual(validate('```json\n'+json.dumps(GOOD)+'\n```'),GOOD)
    def test_reject_untrusted_geometry(self):
        for change in [{'shape':'script'},{'size':[float('inf'),1,1]},{'size':[0,1,1]},{'position':[True,0,0]},{'rotation':[0,0,9]},{'url':'http://localhost/'}]:
            bad=copy.deepcopy(GOOD);bad['parts'][0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):validate(bad)
    def test_budget_and_extra_keys(self):
        for bad in [None,{},'x'*24001,{**GOOD,'code':'print(1)'},{**GOOD,'parts':GOOD['parts']*25}]:
            with self.assertRaises(ValueError):validate(bad)
    def test_description(self):
        self.assertEqual(description({'description':' masa '}),'masa')
        for bad in [None,{}, {'description':4},{'description':'x'*241}]:
            with self.assertRaises(ValueError):description(bad)
