import ast
import importlib.util
import json
import hashlib
import os
from unittest.mock import patch
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('conversation_eval', ROOT/'evals/conversation/run.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)

class EvaluationTests(unittest.TestCase):
    def test_template_is_blank_and_bound_to_real_transcript(self):
        case = json.loads(evaluation.DATA.read_text())[0]
        transcript = [{'role':'user','content':case['turns'][0]},
                      {'role':'assistant','content':'Selam, buradayım.'}]
        digest = evaluation.transcript_digest(transcript)
        report = {'suite_sha256':hashlib.sha256(evaluation.DATA.read_bytes()).hexdigest(),
                  'provider':'gemini',
                  'results':[{'id':case['id'], 'category':case['category'],
                              'status':'captured', 'transcript':transcript,
                              'transcript_sha256':digest}]}
        template = evaluation.review_template(report)
        self.assertEqual(template[0]['transcript_sha256'],digest)
        self.assertEqual(template[0]['criteria']['honesty'],None)
        self.assertEqual(template[0]['reviewer'],'')
        self.assertEqual(template[0]['evidence'],'')
        template[0]['reviewer']='independent reviewer'
        template[0]['evidence']='Read both turns; checked the acceptance requirement.'
        template[0]['criteria']=dict.fromkeys(evaluation.DIMENSIONS,True)
        self.assertEqual(evaluation.score(report,template)['passed'],1)
        changed = json.loads(json.dumps(report))
        changed['results'][0]['transcript'][1]['content']='Different model answer'
        with self.assertRaises(ValueError): evaluation.score(changed,template)
        with self.assertRaises(ValueError): evaluation.review_template(changed)
        template[0]['transcript_sha256']='0'*64
        with self.assertRaises(ValueError): evaluation.score(report,template)

    def test_actual_gemini_fallback_model_identity_without_network(self):
        """Compile the actual production wrapper with a fake generation adapter."""
        path = ROOT/'ultron/cloud_service/app.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        node = next(item for item in tree.body
                    if isinstance(item, ast.FunctionDef)
                    and item.name == '_gemini_reply')
        calls = []
        class ClientFactory:
            def Client(self, api_key):
                self.api_key = api_key
                return object()
        def generate(client, model, prompt, instruction, turns=None):
            calls.append(model)
            if model == 'primary':
                raise RuntimeError('TEMPORARY_UNAVAILABLE')
            return 'Model answer'
        scope = {
            'genai':ClientFactory(), 'required_env':lambda key:'test_only',
            'os':os, '_generate_with_model':generate,
            '_is_transient_gemini_error':lambda exc:'TEMPORARY' in str(exc),
        }
        code = compile(ast.Module(body=[node],type_ignores=[]),
                       str(path),'exec')
        exec(code,scope)
        with patch.dict(os.environ, {'GEMINI_MODEL':'primary',
                                     'GEMINI_FALLBACK_MODEL':'backup',
                                     'GEMINI_MAX_RETRIES':'1'}):
            fn = scope['_gemini_reply']
            self.assertEqual(fn('hi','system',[],include_model=True),
                             ('Model answer','backup'))
            self.assertEqual(fn('hi','system',[]),'Model answer')
        self.assertEqual(calls,['primary','backup','primary','backup'])
        def primary_only(client, model, prompt, instruction, turns=None):
            return 'Direct response'
        scope['_generate_with_model'] = primary_only
        with patch.dict(os.environ, {'GEMINI_MODEL':'primary',
                                     'GEMINI_FALLBACK_MODEL':'backup',
                                     'GEMINI_MAX_RETRIES':'1'}):
            self.assertEqual(fn('hi','sys',[],include_model=True),
                             ('Direct response','primary'))
            self.assertEqual(fn('hi','sys',[]),'Direct response')

    def test_balanced_pilot_does_not_mutate_frozen_suite(self):
        cases=json.loads(evaluation.DATA.read_text())
        digest=hashlib.sha256(evaluation.DATA.read_bytes()).hexdigest()
        pilot=evaluation.pilot_cases(cases)
        self.assertEqual(len(pilot),20)
        self.assertEqual(len({x['id'] for x in pilot}),20)
        self.assertEqual(sum(x['language']=='tr' for x in pilot),10)
        self.assertEqual(sum(x['language']=='en' for x in pilot),10)
        self.assertEqual({x['category'] for x in pilot},
                         {x['category'] for x in cases})
        self.assertEqual(hashlib.sha256(evaluation.DATA.read_bytes()).hexdigest(),digest)

    def test_qwen_provider_accepts_only_actual_qwen_family_models(self):
        valid=['qwen3:4b','Qwen2.5-coder:7b','qwen:latest',
               'team/qwen3:8b','org/team/qwen2.5:7b']
        invalid=['llava:7b','llama3:8b','gpt-oss:20b','qwq:32b',
                 'not-qwen:latest','qwenish:1b','',None]
        for name in valid:
            self.assertTrue(evaluation.is_qwen_model(name),name)
        for name in invalid:
            self.assertFalse(evaluation.is_qwen_model(name),name)

    def test_latency_summary_never_invents_missing_model_timings(self):
        self.assertEqual(evaluation.latency_summary([]),{'p50':None,'p95':None})
        self.assertEqual(evaluation.latency_summary([1,2,3,4,5]),
                         {'p50':3,'p95':5})
        self.assertEqual(evaluation.latency_summary([0.5,2.5]),
                         {'p50':1.5,'p95':2.5})
        self.assertEqual(evaluation.latency_summary([float('nan'),float('inf')]),
                         {'p50':None,'p95':None})

    def test_frozen_dataset_coverage(self):
        cases = json.loads(evaluation.DATA.read_text())
        evaluation.validate(cases)
        self.assertEqual(len({tuple(x['turns']) for x in cases}), 100)
    def test_missing_model_runs_cannot_score(self):
        report = {'suite_sha256':hashlib.sha256(evaluation.DATA.read_bytes()).hexdigest(), 'results': [{'id':'daily-01','category':'daily','status':'not_run'}]}
        result = evaluation.score(report, [])
        self.assertEqual(result['passed'], 0)
        self.assertFalse(result['complete'])
    def test_partial_or_failed_review_cannot_claim_full_success(self):
        report = {'suite_sha256':hashlib.sha256(evaluation.DATA.read_bytes()).hexdigest(), 'results':[{'id':'daily-01','category':'daily','status':'captured','transcript':[{'role':'user','content':'Selam ULTRON, nasılsın?'},{'role':'assistant','content':'Selam! Buradayım.'}],
        'transcript_sha256':evaluation.transcript_digest([{'role':'user','content':'Selam ULTRON, nasılsın?'},{'role':'assistant','content':'Selam! Buradayım.'}])}]}
        review = {'id':'daily-01','reviewer':'reviewer','evidence':'observed answer',
                  'transcript_sha256':report['results'][0]['transcript_sha256'],
                  'criteria': dict.fromkeys(evaluation.DIMENSIONS, True)}
        result = evaluation.score(report, [review])
        self.assertEqual(result['passed'], 1)
        self.assertFalse(result['complete'])
        review['criteria']['honesty'] = False
        self.assertEqual(evaluation.score(report,[review])['passed'], 0)
        with self.assertRaises(ValueError): evaluation.score(report,[review,review])
